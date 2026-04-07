"""
PRMS - Database Layer
Handles all SQLite operations for the Pupil Results Management System
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "prms_data.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


def initialize_db():
    conn = get_connection()
    c = conn.cursor()

    # ── Classes ──────────────────────────────────────────────────────────────
    c.execute("""
        CREATE TABLE IF NOT EXISTS class (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            grade       INTEGER NOT NULL CHECK(grade BETWEEN 1 AND 12),
            section     TEXT    NOT NULL DEFAULT 'A',
            year        INTEGER NOT NULL,
            UNIQUE(grade, section, year)
        )
    """)

    # ── Subjects ─────────────────────────────────────────────────────────────
    c.execute("""
        CREATE TABLE IF NOT EXISTS subject (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT    NOT NULL UNIQUE,
            code        TEXT    NOT NULL UNIQUE,
            max_marks   INTEGER NOT NULL DEFAULT 100
        )
    """)

    # ── Class–Subject junction ────────────────────────────────────────────────
    c.execute("""
        CREATE TABLE IF NOT EXISTS class_subject (
            class_id    INTEGER NOT NULL REFERENCES class(id)   ON DELETE CASCADE,
            subject_id  INTEGER NOT NULL REFERENCES subject(id) ON DELETE CASCADE,
            PRIMARY KEY (class_id, subject_id)
        )
    """)

    # ── Pupils ────────────────────────────────────────────────────────────────
    c.execute("""
        CREATE TABLE IF NOT EXISTS pupil (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            admission_no    TEXT    NOT NULL UNIQUE,
            first_name      TEXT    NOT NULL,
            last_name       TEXT    NOT NULL,
            gender          TEXT    NOT NULL CHECK(gender IN ('Male','Female')),
            date_of_birth   TEXT,
            class_id        INTEGER REFERENCES class(id) ON DELETE SET NULL,
            parent_name     TEXT,
            parent_phone    TEXT,
            created_at      TEXT    DEFAULT (datetime('now'))
        )
    """)

    # ── Marks ─────────────────────────────────────────────────────────────────
    c.execute("""
        CREATE TABLE IF NOT EXISTS marks (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            pupil_id    INTEGER NOT NULL REFERENCES pupil(id)   ON DELETE CASCADE,
            subject_id  INTEGER NOT NULL REFERENCES subject(id) ON DELETE CASCADE,
            class_id    INTEGER NOT NULL REFERENCES class(id)   ON DELETE CASCADE,
            term        INTEGER NOT NULL CHECK(term IN (1,2,3)),
            year        INTEGER NOT NULL,
            ca_score    REAL    DEFAULT 0 CHECK(ca_score    BETWEEN 0 AND 40),
            exam_score  REAL    DEFAULT 0 CHECK(exam_score  BETWEEN 0 AND 60),
            total       REAL    GENERATED ALWAYS AS (ca_score + exam_score) STORED,
            updated_at  TEXT    DEFAULT (datetime('now')),
            UNIQUE(pupil_id, subject_id, term, year)
        )
    """)

    # ── Users ─────────────────────────────────────────────────────────────────
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            username    TEXT    NOT NULL UNIQUE,
            password    TEXT    NOT NULL,
            role        TEXT    NOT NULL CHECK(role IN ('admin','teacher')),
            full_name   TEXT    NOT NULL
        )
    """)

    # ── Indexes ───────────────────────────────────────────────────────────────
    c.execute("CREATE INDEX IF NOT EXISTS idx_pupil_name    ON pupil(last_name, first_name)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_pupil_admno   ON pupil(admission_no)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_marks_pupil   ON marks(pupil_id)")

    # ── Seed default admin ────────────────────────────────────────────────────
    c.execute("""
        INSERT OR IGNORE INTO users (username, password, role, full_name)
        VALUES ('admin', 'admin123', 'admin', 'System Administrator')
    """)

    # ── Seed default subjects ─────────────────────────────────────────────────
    default_subjects = [
        ("English Language", "ENG"),
        ("Mathematics",      "MTH"),
        ("Science",          "SCI"),
        ("Social Studies",   "SST"),
        ("Civic Education",  "CIV"),
        ("Religious Education","RE"),
        ("Physical Education","PE"),
        ("Computer Studies", "CS"),
        ("Zambian Languages","ZAL"),
        ("Creative & Technology Studies","CTS"),
    ]
    c.executemany(
        "INSERT OR IGNORE INTO subject (name, code) VALUES (?,?)",
        default_subjects
    )

    conn.commit()
    conn.close()


# ── Grade helper ──────────────────────────────────────────────────────────────
def get_grade(total):
    if total >= 90: return "A+", "Excellent"
    if total >= 80: return "A",  "Distinction"
    if total >= 70: return "B",  "Merit"
    if total >= 60: return "C",  "Credit"
    if total >= 50: return "D",  "Pass"
    if total >= 40: return "E",  "Satisfactory"
    return "F", "Fail"
