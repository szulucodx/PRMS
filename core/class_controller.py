"""
PRMS - Class & Subject Controller
"""

from core.database import get_connection


# ── Classes ───────────────────────────────────────────────────────────────────

def get_all_classes():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM class ORDER BY grade, section, year DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_class(grade, section, year):
    conn = get_connection()
    try:
        conn.execute("INSERT INTO class (grade, section, year) VALUES (?,?,?)", (grade, section, year))
        conn.commit()
        return True, "Class added."
    except Exception as e:
        return False, str(e)
    finally:
        conn.close()


def delete_class(class_id):
    conn = get_connection()
    try:
        conn.execute("DELETE FROM class WHERE id=?", (class_id,))
        conn.commit()
        return True, "Class deleted."
    except Exception as e:
        return False, str(e)
    finally:
        conn.close()


def get_class_label(class_id):
    conn = get_connection()
    row = conn.execute("SELECT grade, section, year FROM class WHERE id=?", (class_id,)).fetchone()
    conn.close()
    if row:
        return f"Grade {row['grade']}{row['section']} ({row['year']})"
    return "Unknown"


# ── Subjects ──────────────────────────────────────────────────────────────────

def get_all_subjects():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM subject ORDER BY name").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_subject(name, code, max_marks=100):
    conn = get_connection()
    try:
        conn.execute("INSERT INTO subject (name, code, max_marks) VALUES (?,?,?)", (name, code, max_marks))
        conn.commit()
        return True, "Subject added."
    except Exception as e:
        return False, str(e)
    finally:
        conn.close()


def delete_subject(subject_id):
    conn = get_connection()
    try:
        conn.execute("DELETE FROM subject WHERE id=?", (subject_id,))
        conn.commit()
        return True, "Subject deleted."
    except Exception as e:
        return False, str(e)
    finally:
        conn.close()


# ── Stats ─────────────────────────────────────────────────────────────────────

def get_dashboard_stats():
    conn = get_connection()
    pupils   = conn.execute("SELECT COUNT(*) FROM pupil").fetchone()[0]
    classes  = conn.execute("SELECT COUNT(*) FROM class").fetchone()[0]
    subjects = conn.execute("SELECT COUNT(*) FROM subject").fetchone()[0]
    marks    = conn.execute("SELECT COUNT(*) FROM marks").fetchone()[0]
    conn.close()
    return {"pupils": pupils, "classes": classes, "subjects": subjects, "marks_entered": marks}
