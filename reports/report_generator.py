"""
PRMS - Report Card Generator
Generates professional PDF report cards using only stdlib + basic formatting
"""

import os
import sqlite3
from core.database import get_connection, get_grade
from core.marks_controller import get_pupil_marks, get_class_report_data
from core.class_controller import get_class_label

REPORTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "reports_output")
os.makedirs(REPORTS_DIR, exist_ok=True)


def generate_report_card_text(pupil_id, term, year):
    """
    Generates a plain-text report card and saves as .txt file.
    Returns (filepath, message).
    """
    conn = get_connection()
    pupil = conn.execute(
        "SELECT p.*, c.grade, c.section FROM pupil p LEFT JOIN class c ON p.class_id=c.id WHERE p.id=?",
        (pupil_id,)
    ).fetchone()
    conn.close()

    if not pupil:
        return None, "Pupil not found."

    marks = get_pupil_marks(pupil_id, term, year)
    if not marks:
        return None, "No marks found for this term/year."

    total = sum(m['total'] for m in marks)
    avg   = total / len(marks)
    grade, remark = get_grade(avg)

    lines = []
    W = 62
    def bar():  lines.append("=" * W)
    def line(t=""):  lines.append(t)

    bar()
    lines.append("PUPIL RESULTS MANAGEMENT SYSTEM (PRMS)".center(W))
    lines.append("ZAMBIAN SCHOOL — ACADEMIC REPORT CARD".center(W))
    bar()
    line()
    lines.append(f"  Name        : {pupil['first_name']} {pupil['last_name']}")
    lines.append(f"  Admission # : {pupil['admission_no']}")
    lines.append(f"  Class       : Grade {pupil['grade']}{pupil['section']}")
    lines.append(f"  Term        : {term}    Year : {year}")
    lines.append(f"  Gender      : {pupil['gender']}")
    line()
    bar()
    lines.append(f"  {'SUBJECT':<28} {'CA(40)':<8} {'EXAM(60)':<10} {'TOTAL':<7} {'GRADE':<6} REMARK")
    bar()

    for m in marks:
        g, rem = get_grade(m['total'])
        lines.append(
            f"  {m['subject_name']:<28} {m['ca_score']:<8.1f} {m['exam_score']:<10.1f} "
            f"{m['total']:<7.1f} {g:<6} {rem}"
        )

    bar()
    lines.append(f"  {'TOTAL MARKS':<28} {'':8} {'':10} {total:<7.1f}")
    lines.append(f"  {'AVERAGE':<28} {'':8} {'':10} {avg:<7.1f} {grade:<6} {remark}")
    bar()
    line()
    lines.append("  CLASS TEACHER'S REMARKS : _______________________________________")
    line()
    lines.append("  HEAD TEACHER'S REMARKS  : _______________________________________")
    line()
    lines.append("  HEAD TEACHER SIGNATURE  : ________________  DATE: _______________")
    line()
    lines.append("  PARENT/GUARDIAN SIGN    : ________________  DATE: _______________")
    line()
    bar()
    lines.append("  NOTE: CA = Continuous Assessment (40%) | EXAM = End-of-Term (60%)".center(W))
    bar()

    name_slug = f"{pupil['last_name']}_{pupil['first_name']}".replace(" ", "_")
    filename  = f"ReportCard_{name_slug}_T{term}_{year}.txt"
    filepath  = os.path.join(REPORTS_DIR, filename)

    with open(filepath, "w") as f:
        f.write("\n".join(lines))

    return filepath, f"Report card saved: {filename}"


def generate_class_results_text(class_id, term, year):
    """Generates a class results sheet."""
    data  = get_class_report_data(class_id, term, year)
    label = get_class_label(class_id)

    if not data:
        return None, "No data found."

    lines = []
    W = 70
    def bar(): lines.append("=" * W)

    bar()
    lines.append("PUPIL RESULTS MANAGEMENT SYSTEM (PRMS)".center(W))
    lines.append(f"CLASS RESULTS SHEET — {label} | TERM {term} | {year}".center(W))
    bar()
    lines.append(
        f"  {'POS':<5}{'ADMISSION':<12}{'NAME':<28}{'AVG':<7}{'GRADE':<7}REMARK"
    )
    bar()
    for r in data:
        lines.append(
            f"  {r['position']:<5}{r['admission_no']:<12}{r['name']:<28}"
            f"{r['average']:<7.1f}{r['grade']:<7}{r['remark']}"
        )
    bar()
    lines.append(f"  Total pupils: {len(data)}")
    bar()

    filename = f"ClassResults_{label.replace(' ','_')}_T{term}_{year}.txt"
    filepath = os.path.join(REPORTS_DIR, filename)
    with open(filepath, "w") as f:
        f.write("\n".join(lines))

    return filepath, f"Class results saved: {filename}"
