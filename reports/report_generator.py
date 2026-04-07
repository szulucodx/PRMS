"""
PRMS - Report Card Generator
Generates plain text and PDF report cards and class results sheets.
"""

import os
from core.database import get_connection, get_grade
from core.marks_controller import get_pupil_marks, get_class_report_data
from core.class_controller import get_class_label

REPORTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "reports_output")
os.makedirs(REPORTS_DIR, exist_ok=True)


def _safe_text(value):
    return str(value or "").encode("latin-1", "replace").decode("latin-1")


def _pdf_escape(text):
    return _safe_text(text).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _write_text_report(filepath, lines):
    with open(filepath, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))


def _write_pdf_report(filepath, lines):
    page_width = 595.28
    page_height = 841.89
    margin = 40
    font_size = 10
    leading = 14
    lines_per_page = max(1, int((page_height - (2 * margin)) // leading))
    pages = [lines[index:index + lines_per_page] for index in range(0, len(lines), lines_per_page)] or [[]]

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


def get_report_card_context(pupil_id, term, year):
    conn = get_connection()
    pupil = conn.execute(
        "SELECT p.*, c.grade, c.section FROM pupil p LEFT JOIN class c ON p.class_id=c.id WHERE p.id=?",
        (pupil_id,),
    ).fetchone()
    conn.close()

    if not pupil:
        return None

    marks = get_pupil_marks(pupil_id, term, year)
    if not marks:
        return None

    total = sum(m["total"] for m in marks)
    average = total / len(marks)
    grade, remark = get_grade(average)

    return {
        "pupil": dict(pupil),
        "marks": marks,
        "total": total,
        "average": average,
        "grade": grade,
        "remark": remark,
        "term": term,
        "year": year,
    }


def _report_card_lines(context):
    pupil = context["pupil"]
    marks = context["marks"]
    total = context["total"]
    average = context["average"]
    grade = context["grade"]
    remark = context["remark"]
    term = context["term"]
    year = context["year"]

    lines = []
    width = 62

    def bar():
        lines.append("=" * width)

    bar()
    lines.append("PUPIL RESULTS MANAGEMENT SYSTEM (PRMS)".center(width))
    lines.append("ZAMBIAN SCHOOL - ACADEMIC REPORT CARD".center(width))
    bar()
    lines.append("")
    lines.append(f"  Name        : {pupil['first_name']} {pupil['last_name']}")
    lines.append(f"  Admission # : {pupil['admission_no']}")
    lines.append(f"  Class       : Grade {pupil['grade']}{pupil['section']}")
    lines.append(f"  Term        : {term}    Year : {year}")
    lines.append(f"  Gender      : {pupil['gender']}")
    lines.append("")
    bar()
    lines.append(f"  {'SUBJECT':<28} {'CA(40)':<8} {'EXAM(60)':<10} {'TOTAL':<7} {'GRADE':<6} REMARK")
    bar()

    for mark in marks:
        grade_code, grade_remark = get_grade(mark["total"])
        lines.append(
            f"  {mark['subject_name']:<28} {mark['ca_score']:<8.1f} {mark['exam_score']:<10.1f} "
            f"{mark['total']:<7.1f} {grade_code:<6} {grade_remark}"
        )

    bar()
    lines.append(f"  {'TOTAL MARKS':<28} {'':8} {'':10} {total:<7.1f}")
    lines.append(f"  {'AVERAGE':<28} {'':8} {'':10} {average:<7.1f} {grade:<6} {remark}")
    bar()
    lines.append("")
    lines.append("  CLASS TEACHER'S REMARKS : _______________________________________")
    lines.append("")
    lines.append("  HEAD TEACHER'S REMARKS  : _______________________________________")
    lines.append("")
    lines.append("  HEAD TEACHER SIGNATURE  : ________________  DATE: _______________")
    lines.append("")
    lines.append("  PARENT/GUARDIAN SIGN    : ________________  DATE: _______________")
    lines.append("")
    bar()
    lines.append("  NOTE: CA = Continuous Assessment (40%) | EXAM = End-of-Term (60%)".center(width))
    bar()
    return lines


def generate_report_card_text(pupil_id, term, year):
    """Generates a report card as .txt and .pdf files. Returns (filepath, message)."""
    conn = get_connection()
    pupil_row = conn.execute(
        "SELECT id FROM pupil WHERE id=?",
        (pupil_id,),
    ).fetchone()
    conn.close()

    if not pupil_row:
        return None, "Pupil not found."

    context = get_report_card_context(pupil_id, term, year)
    if not context:
        return None, "No marks found for this term/year."

    pupil = context["pupil"]
    lines = _report_card_lines(context)

    name_slug = f"{pupil['last_name']}_{pupil['first_name']}".replace(" ", "_")
    txt_filename = f"ReportCard_{name_slug}_T{term}_{year}.txt"
    pdf_filename = f"ReportCard_{name_slug}_T{term}_{year}.pdf"
    txt_path = os.path.join(REPORTS_DIR, txt_filename)
    pdf_path = os.path.join(REPORTS_DIR, pdf_filename)

    _write_text_report(txt_path, lines)
    _write_pdf_report(pdf_path, lines)

    return pdf_path, f"Report card saved: {pdf_filename}"


def generate_class_results_text(class_id, term, year):
    """Generates a class results sheet as .txt and .pdf files."""
    data = get_class_report_data(class_id, term, year)
    label = get_class_label(class_id)

    if not data:
        return None, "No data found."

    lines = []
    width = 70

    def bar():
        lines.append("=" * width)

    bar()
    lines.append("PUPIL RESULTS MANAGEMENT SYSTEM (PRMS)".center(width))
    lines.append(f"CLASS RESULTS SHEET - {label} | TERM {term} | {year}".center(width))
    bar()
    lines.append(f"  {'POS':<5}{'ADMISSION':<12}{'NAME':<28}{'AVG':<7}{'GRADE':<7}REMARK")
    bar()
    for row in data:
        lines.append(
            f"  {row['position']:<5}{row['admission_no']:<12}{row['name']:<28}"
            f"{row['average']:<7.1f}{row['grade']:<7}{row['remark']}"
        )
    bar()
    lines.append(f"  Total pupils: {len(data)}")
    bar()

    filename_base = f"ClassResults_{label.replace(' ','_')}_T{term}_{year}"
    txt_path = os.path.join(REPORTS_DIR, f"{filename_base}.txt")
    pdf_path = os.path.join(REPORTS_DIR, f"{filename_base}.pdf")

    _write_text_report(txt_path, lines)
    _write_pdf_report(pdf_path, lines)

    return pdf_path, f"Class results saved: {filename_base}.pdf"