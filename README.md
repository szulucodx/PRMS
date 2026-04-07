# PRMS — Pupil Results Management System
**Zambian Schools | Grades 1–12 | Python + Tkinter + SQLite**

---

## Requirements
- Python 3.8+
- Tkinter (bundled with most Python installs)
  - Ubuntu/Debian: `sudo apt install python3-tk`
  - Windows/macOS: included by default

---

## How to Run

```bash
cd PRMS
python main.py
```

**Default login:**
- Username: `admin`
- Password: `admin123`

---

## Project Structure

```
PRMS/
├── main.py                  ← Entry point (GUI)
├── prms_data.db             ← SQLite database (auto-created on first run)
├── core/
│   ├── database.py          ← DB init, schema, grade helper
│   ├── pupil_controller.py  ← Pupil CRUD
│   ├── marks_controller.py  ← Marks entry & retrieval
│   └── class_controller.py  ← Class & subject management
├── reports/
│   ├── report_generator.py  ← Report card & class results generator
│   └── messaging.py         ← Email/SMS/WhatsApp delivery helpers
└── reports_output/          ← Generated report files saved here
```

Generated report cards and class results are saved as both `.txt` and `.pdf` files in `reports_output/`.

To use parent sharing features, set these environment variables before launching the app:
- `EMAIL_SMTP_HOST`, `EMAIL_SMTP_PORT`, `EMAIL_SMTP_USER`, `EMAIL_SMTP_PASSWORD`
- `EMAIL_FROM` and optionally `EMAIL_USE_STARTTLS`
- `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_SMS`, `TWILIO_FROM_WHATSAPP`

SMS and WhatsApp delivery use a Twilio-compatible API. Parent email and phone details are stored on the pupil record.

---

## Features

| Module          | Features                                                   |
|-----------------|------------------------------------------------------------|
| Dashboard       | Live stats: pupils, classes, subjects, marks entered        |
| Pupil Register  | Add / edit / delete pupils, search by name or admission no. |
| Marks Entry     | Add marks with one popup or edit CA / Exam per subject      |
| Reports         | Individual report cards + Class results sheets (.txt/.pdf)  |
| Sharing         | Email, SMS, and WhatsApp delivery for parent/guardian results |
| Settings        | In-app screen for saving email/SMS/WhatsApp credentials      |
| Classes         | Add Grade 1–12 classes with sections (A/B/C/D) and year    |
| Subjects        | Add / delete school subjects                                |

---

## Grading Scale (Zambian ECZ-style)

| Total | Grade | Remark      |
|-------|-------|-------------|
| 90–100 | A+   | Excellent   |
| 80–89  | A    | Distinction |
| 70–79  | B    | Merit       |
| 60–69  | C    | Credit      |
| 50–59  | D    | Pass        |
| 40–49  | E    | Satisfactory|
| 0–39   | F    | Fail        |

---

## Architecture (from Research Proposal)
- **Presentation Layer**: Tkinter GUI
- **Application Layer**: Python business logic (controllers)
- **Data Access Layer**: SQLite connection manager + CRUD
- **Data Layer**: Single-file SQLite database (`prms_data.db`)

Aligns with the layered architecture specified in Chapter 3 of the PRMS Research Proposal (DSRM methodology).
