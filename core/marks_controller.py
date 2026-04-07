"""
PRMS - Marks Controller
Handles marks entry, retrieval, and grade calculations
"""

from core.database import get_connection, get_grade


def save_marks(pupil_id, subject_id, class_id, term, year, ca_score, exam_score):
    conn = get_connection()
    try:
        conn.execute("""
            INSERT INTO marks (pupil_id, subject_id, class_id, term, year, ca_score, exam_score, updated_at)
            VALUES (?,?,?,?,?,?,?, datetime('now'))
            ON CONFLICT(pupil_id, subject_id, term, year)
            DO UPDATE SET ca_score=excluded.ca_score, exam_score=excluded.exam_score,
                          updated_at=datetime('now')
        """, (pupil_id, subject_id, class_id, term, year, ca_score, exam_score))
        conn.commit()
        return True, "Marks saved."
    except Exception as e:
        return False, str(e)
    finally:
        conn.close()


def get_pupil_marks(pupil_id, term, year):
    conn = get_connection()
    rows = conn.execute("""
        SELECT m.*, s.name as subject_name, s.code as subject_code, s.max_marks
        FROM marks m
        JOIN subject s ON m.subject_id = s.id
        WHERE m.pupil_id=? AND m.term=? AND m.year=?
        ORDER BY s.name
    """, (pupil_id, term, year)).fetchall()
    conn.close()
    results = []
    for r in rows:
        d = dict(r)
        d['grade'], d['remark'] = get_grade(d['total'])
        results.append(d)
    return results


def get_class_marks(class_id, subject_id, term, year):
    conn = get_connection()
    rows = conn.execute("""
        SELECT p.id, p.admission_no, p.first_name, p.last_name,
               COALESCE(m.ca_score, 0) as ca_score,
               COALESCE(m.exam_score, 0) as exam_score,
               COALESCE(m.total, 0) as total
        FROM pupil p
        LEFT JOIN marks m ON m.pupil_id=p.id AND m.subject_id=? AND m.term=? AND m.year=?
        WHERE p.class_id=?
        ORDER BY p.last_name, p.first_name
    """, (subject_id, term, year, class_id)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_class_report_data(class_id, term, year):
    """Returns all pupils with their full marks summary for a class/term."""
    conn = get_connection()
    pupils = conn.execute(
        "SELECT id, admission_no, first_name, last_name FROM pupil WHERE class_id=? ORDER BY last_name",
        (class_id,)
    ).fetchall()

    results = []
    for p in pupils:
        marks = conn.execute("""
            SELECT s.name, m.ca_score, m.exam_score, m.total
            FROM marks m JOIN subject s ON m.subject_id=s.id
            WHERE m.pupil_id=? AND m.term=? AND m.year=?
        """, (p['id'], term, year)).fetchall()

        total_marks = sum(m['total'] for m in marks) if marks else 0
        avg = total_marks / len(marks) if marks else 0
        grade, remark = get_grade(avg)

        results.append({
            'id':           p['id'],
            'admission_no': p['admission_no'],
            'name':         f"{p['first_name']} {p['last_name']}",
            'subjects':     [dict(m) for m in marks],
            'total':        total_marks,
            'average':      round(avg, 1),
            'grade':        grade,
            'remark':       remark,
        })

    # Assign positions
    results.sort(key=lambda x: x['average'], reverse=True)
    for i, r in enumerate(results):
        r['position'] = i + 1

    conn.close()
    return results
