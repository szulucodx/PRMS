"""
PRMS - Messaging helpers
Email works directly via SMTP. SMS and WhatsApp use Twilio-compatible REST API settings.
"""

import base64
import json
import os
import ssl
from email.message import EmailMessage
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from core.database import get_connection


def normalize_phone_number(phone_number):
    if not phone_number:
        return ""

    cleaned = phone_number.strip()
    digits = "".join(ch for ch in cleaned if ch.isdigit())
    if not digits:
        return ""

    if cleaned.startswith("+"):
        return "+" + digits
    if digits.startswith("260"):
        return "+" + digits
    if digits.startswith("0") and len(digits) == 10:
        return "+260" + digits[1:]
    if len(digits) == 9:
        return "+260" + digits
    return "+" + digits


def _safe_text(value):
    return str(value or "").encode("latin-1", "replace").decode("latin-1")


def _pdf_escape(text):
    return _safe_text(text).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def write_pdf_lines(filepath, title, lines, width=70):
    page_width = 595.28
    page_height = 841.89
    margin = 40
    font_size = 10
    leading = 14
    lines_per_page = max(1, int((page_height - (2 * margin)) // leading))
    all_lines = [title.center(width), ""] + list(lines)
    pages = [all_lines[index:index + lines_per_page] for index in range(0, len(all_lines), lines_per_page)] or [[]]

    objects = []

    def reserve_object():
        objects.append("")
        return len(objects)

    catalog_id = reserve_object()
    pages_id = reserve_object()
    font_id = reserve_object()
    page_ids = []
    content_ids = []

    for page_lines in pages:
        content_lines = [
            "BT",
            f"/F1 {font_size} Tf",
            f"1 0 0 1 {margin} {page_height - margin - font_size} Tm",
            f"{leading} TL",
        ]
        for index, line in enumerate(page_lines):
            content_lines.append(f"({_pdf_escape(line)}) Tj")
            if index != len(page_lines) - 1:
                content_lines.append("T*")
        content_lines.append("ET")
        content_stream = "\n".join(content_lines).encode("latin-1", "replace")

        content_id = reserve_object()
        page_id = reserve_object()
        content_ids.append((content_id, content_stream))
        page_ids.append(page_id)

    objects[font_id - 1] = "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"
    objects[pages_id - 1] = "<< /Type /Pages /Count {count} /Kids {kids} >>".format(
        count=len(page_ids),
        kids="[" + " ".join(f"{page_id} 0 R" for page_id in page_ids) + "]",
    )
    objects[catalog_id - 1] = f"<< /Type /Catalog /Pages {pages_id} 0 R >>"

    for (content_id, content_stream), page_id in zip(content_ids, page_ids):
        objects[content_id - 1] = (
            f"<< /Length {len(content_stream)} >>\n"
            f"stream\n{content_stream.decode('latin-1')}\nendstream"
        )
        objects[page_id - 1] = (
            f"<< /Type /Page /Parent {pages_id} 0 R /MediaBox [0 0 {page_width} {page_height}] "
            f"/Resources << /Font << /F1 {font_id} 0 R >> >> /Contents {content_id} 0 R >>"
        )

    pdf = bytearray()
    pdf.extend(b"%PDF-1.4\n")
    offsets = []
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{index} 0 obj\n".encode("ascii"))
        pdf.extend(obj.encode("latin-1", "replace"))
        pdf.extend(b"\nendobj\n")

    xref_offset = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    pdf.extend(
        (
            "trailer\n"
            f"<< /Size {len(objects) + 1} /Root {catalog_id} 0 R >>\n"
            "startxref\n"
            f"{xref_offset}\n"
            "%%EOF"
        ).encode("ascii")
    )

    with open(filepath, "wb") as handle:
        handle.write(pdf)


def export_delivery_history_pdf(filepath, rows):
    lines = [
        f"Total records: {len(rows)}",
        "",
        f"{'DATE/TIME':<19} {'PUPIL':<24} {'METHOD':<10} {'STATUS':<8} RECIPIENT",
        "-" * 88,
    ]
    for row in rows:
        pupil = "—"
        if row.get("first_name") or row.get("last_name"):
            pupil = f"{row.get('first_name', '')} {row.get('last_name', '')}".strip()
        recipient = row.get("recipient") or "—"
        lines.append(
            f"{(row.get('created_at') or '—')[:19]:<19} {pupil[:24]:<24} {str(row.get('delivery_method') or '—')[:10]:<10} "
            f"{str(row.get('status') or '—')[:8]:<8} {recipient}"
        )
        detail = row.get("detail") or "—"
        if detail:
            lines.append(f"    {detail}")
    write_pdf_lines(filepath, "PRMS DELIVERY HISTORY", lines, width=88)


def build_report_summary(context):
    pupil = context["pupil"]
    return (
        f"PRMS results for {pupil['first_name']} {pupil['last_name']} "
        f"(Adm. {pupil['admission_no']}) for Term {context['term']} / {context['year']}: "
        f"Average {context['average']:.1f}, Grade {context['grade']} ({context['remark']})."
    )


def log_report_delivery(pupil_id, report_type, delivery_method, recipient, status, detail):
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO report_delivery (pupil_id, report_type, delivery_method, recipient, status, detail)
            VALUES (?,?,?,?,?,?)
            """,
            (pupil_id, report_type, delivery_method, recipient, status, detail),
        )
        conn.commit()
    finally:
        conn.close()


def get_report_delivery_history(limit=200, pupil_search=None, delivery_method=None, status=None):
    conn = get_connection()
    try:
        where = []
        params = []

        if pupil_search:
            where.append("(p.first_name LIKE ? OR p.last_name LIKE ? OR p.admission_no LIKE ?)")
            search = f"%{pupil_search.strip()}%"
            params.extend([search, search, search])

        if delivery_method and delivery_method != "All":
            where.append("d.delivery_method = ?")
            params.append(delivery_method)

        if status and status != "All":
            where.append("d.status = ?")
            params.append(status)

        where_sql = f"WHERE {' AND '.join(where)}" if where else ""
        rows = conn.execute(
            """
            SELECT
                d.id,
                d.created_at,
                d.report_type,
                d.delivery_method,
                d.recipient,
                d.status,
                d.detail,
                p.admission_no,
                p.first_name,
                p.last_name,
                p.parent_name,
                p.parent_phone,
                p.parent_email
            FROM report_delivery d
            LEFT JOIN pupil p ON p.id = d.pupil_id
            {where_sql}
            ORDER BY d.id DESC
            LIMIT ?
            """.format(where_sql=where_sql),
            (*params, limit),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def send_email_with_attachment(to_email, subject, body, attachment_path, settings):
    host = settings.get("EMAIL_SMTP_HOST", "").strip()
    port = int(settings.get("EMAIL_SMTP_PORT", "587") or 587)
    username = settings.get("EMAIL_SMTP_USER", "").strip()
    password = settings.get("EMAIL_SMTP_PASSWORD", "").strip()
    sender = settings.get("EMAIL_FROM", username).strip() or username

    if not host or not username or not password:
        return False, "Email settings are incomplete. Set EMAIL_SMTP_HOST, EMAIL_SMTP_USER, and EMAIL_SMTP_PASSWORD."

    message = EmailMessage()
    message["From"] = sender
    message["To"] = to_email
    message["Subject"] = subject
    message.set_content(body)

    with open(attachment_path, "rb") as handle:
        pdf_data = handle.read()
    message.add_attachment(pdf_data, maintype="application", subtype="pdf", filename=os.path.basename(attachment_path))

    try:
        if port == 465:
            import smtplib

            with smtplib.SMTP_SSL(host, port, context=ssl.create_default_context()) as client:
                client.login(username, password)
                client.send_message(message)
        else:
            import smtplib

            with smtplib.SMTP(host, port) as client:
                client.ehlo()
                if settings.get("EMAIL_USE_STARTTLS", "1") != "0":
                    client.starttls(context=ssl.create_default_context())
                    client.ehlo()
                client.login(username, password)
                client.send_message(message)
        return True, f"Email sent to {to_email}."
    except Exception as exc:
        return False, str(exc)


def _send_twilio_message(to_number, body, settings, whatsapp=False):
    account_sid = settings.get("TWILIO_ACCOUNT_SID", "").strip()
    auth_token = settings.get("TWILIO_AUTH_TOKEN", "").strip()
    from_number = settings.get("TWILIO_FROM_WHATSAPP" if whatsapp else "TWILIO_FROM_SMS", "").strip()

    if whatsapp:
        if not to_number.startswith("whatsapp:"):
            to_number = f"whatsapp:{to_number}"
        if from_number and not from_number.startswith("whatsapp:"):
            from_number = f"whatsapp:{from_number}"

    if not account_sid or not auth_token or not from_number:
        channel = "WhatsApp" if whatsapp else "SMS"
        return False, f"{channel} settings are incomplete. Set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, and the relevant sender number."

    url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"
    payload = urlencode({"To": to_number, "From": from_number, "Body": body}).encode("utf-8")
    credentials = base64.b64encode(f"{account_sid}:{auth_token}".encode("utf-8")).decode("ascii")
    request = Request(url, data=payload)
    request.add_header("Authorization", f"Basic {credentials}")
    request.add_header("Content-Type", "application/x-www-form-urlencoded")

    try:
        with urlopen(request, timeout=30) as response:
            response_body = response.read().decode("utf-8", "replace")
            data = json.loads(response_body)
            return True, f"Message sent successfully. SID: {data.get('sid', 'unknown')}"
    except Exception as exc:
        return False, str(exc)


def send_sms(to_number, body, settings):
    return _send_twilio_message(normalize_phone_number(to_number), body, settings, whatsapp=False)


def send_whatsapp(to_number, body, settings):
    return _send_twilio_message(normalize_phone_number(to_number), body, settings, whatsapp=True)
