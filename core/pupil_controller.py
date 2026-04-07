"""
PRMS - Pupil Controller
CRUD operations for pupil registration and management
"""

from core.database import get_connection


def add_pupil(admission_no, first_name, last_name, gender, dob, class_id, parent_name, parent_phone, parent_email):
    conn = get_connection()
    try:
        conn.execute("""
            INSERT INTO pupil (admission_no, first_name, last_name, gender, date_of_birth,
                               class_id, parent_name, parent_phone, parent_email)
            VALUES (?,?,?,?,?,?,?,?,?)
        """, (admission_no, first_name, last_name, gender, dob, class_id, parent_name, parent_phone, parent_email))
        conn.commit()
        return True, "Pupil registered successfully."
    except Exception as e:
        return False, str(e)
    finally:
        conn.close()


def update_pupil(pupil_id, first_name, last_name, gender, dob, class_id, parent_name, parent_phone, parent_email):
    conn = get_connection()
    try:
        conn.execute("""
            UPDATE pupil SET first_name=?, last_name=?, gender=?, date_of_birth=?,
                             class_id=?, parent_name=?, parent_phone=?, parent_email=?
            WHERE id=?
        """, (first_name, last_name, gender, dob, class_id, parent_name, parent_phone, parent_email, pupil_id))
        conn.commit()
        return True, "Pupil updated."
    except Exception as e:
        return False, str(e)
    finally:
        conn.close()


def delete_pupil(pupil_id):
    conn = get_connection()
    try:
        conn.execute("DELETE FROM pupil WHERE id=?", (pupil_id,))
        conn.commit()
        return True, "Pupil deleted."
    except Exception as e:
        return False, str(e)
    finally:
        conn.close()


def get_all_pupils(class_id=None, search=None):
    conn = get_connection()
    query = """
        SELECT p.*, c.grade, c.section
        FROM pupil p
        LEFT JOIN class c ON p.class_id = c.id
        WHERE 1=1
    """
    params = []
    if class_id:
        query += " AND p.class_id = ?"
        params.append(class_id)
    if search:
        query += " AND (p.first_name LIKE ? OR p.last_name LIKE ? OR p.admission_no LIKE ?)"
        params += [f"%{search}%", f"%{search}%", f"%{search}%"]
    query += " ORDER BY p.last_name, p.first_name"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_pupil_by_id(pupil_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM pupil WHERE id=?", (pupil_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def next_admission_number():
    conn = get_connection()
    row = conn.execute("SELECT MAX(CAST(SUBSTR(admission_no,5) AS INTEGER)) FROM pupil WHERE admission_no LIKE 'PRMS%'").fetchone()
    conn.close()
    last = row[0] or 0
    return f"PRMS{last+1:04d}"
