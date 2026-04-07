"""
PRMS - Main GUI Application
Pupil Results Management System for Zambian Schools (Grades 1–12)
Built with Python Tkinter + SQLite
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
import csv
import os, sys

# ── Ensure imports work from project root ─────────────────────────────────────
sys.path.insert(0, os.path.dirname(__file__))

from core.database       import initialize_db, get_grade, get_app_settings, save_app_settings
from core.pupil_controller  import (add_pupil, update_pupil, delete_pupil,
                                    get_all_pupils, get_pupil_by_id, next_admission_number)
from core.marks_controller  import save_marks, get_pupil_marks, get_class_marks
from core.class_controller  import (get_all_classes, add_class, delete_class,
                                    get_all_subjects, add_subject, delete_subject,
                                    get_dashboard_stats, get_class_label)
from reports.report_generator import (
    generate_report_card_text,
    generate_class_results_text,
    get_report_card_context,
)
from reports.messaging import (
    build_report_summary,
    get_report_delivery_history,
    log_report_delivery,
    send_email_with_attachment,
    send_sms,
    send_whatsapp,
)

# ── Colour palette ─────────────────────────────────────────────────────────────
C = {
    "bg":        "#F0F4F8",
    "sidebar":   "#1A3A5C",
    "sidebar_h": "#2563EB",
    "accent":    "#2563EB",
    "accent2":   "#16A34A",
    "danger":    "#DC2626",
    "card":      "#FFFFFF",
    "header":    "#1E3A5F",
    "text":      "#1F2937",
    "light":     "#6B7280",
    "border":    "#D1D5DB",
    "row_even":  "#F9FAFB",
    "row_odd":   "#FFFFFF",
    "green":     "#DCFCE7",
    "red":       "#FEE2E2",
}

FONT      = ("Segoe UI", 10)
FONT_BOLD = ("Segoe UI", 10, "bold")
FONT_H1   = ("Segoe UI", 18, "bold")
FONT_H2   = ("Segoe UI", 13, "bold")
FONT_SM   = ("Segoe UI", 9)


# ═══════════════════════════════════════════════════════════════════════════════
#  LOGIN WINDOW
# ═══════════════════════════════════════════════════════════════════════════════

class LoginWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        initialize_db()
        self.title("PRMS – Login")
        self.geometry("420x340")
        self.resizable(False, False)
        self.configure(bg=C["bg"])
        self._build()
        self.eval('tk::PlaceWindow . center')

    def _build(self):
        # Header
        hdr = tk.Frame(self, bg=C["header"], height=80)
        hdr.pack(fill="x")
        tk.Label(hdr, text="PRMS", font=("Segoe UI", 28, "bold"),
                 bg=C["header"], fg="white").pack(pady=(12, 0))
        tk.Label(hdr, text="Pupil Results Management System",
                 font=FONT_SM, bg=C["header"], fg="#93C5FD").pack()

        # Card
        card = tk.Frame(self, bg=C["card"], padx=30, pady=25)
        card.pack(fill="both", expand=True, padx=20, pady=20)

        tk.Label(card, text="Username", font=FONT_BOLD, bg=C["card"], fg=C["text"]).pack(anchor="w")
        self.user_var = tk.StringVar(value="admin")
        tk.Entry(card, textvariable=self.user_var, font=FONT, relief="flat",
                 highlightthickness=1, highlightbackground=C["border"],
                 highlightcolor=C["accent"]).pack(fill="x", pady=(2, 10), ipady=6)

        tk.Label(card, text="Password", font=FONT_BOLD, bg=C["card"], fg=C["text"]).pack(anchor="w")
        self.pass_var = tk.StringVar(value="admin123")
        tk.Entry(card, textvariable=self.pass_var, show="•", font=FONT, relief="flat",
                 highlightthickness=1, highlightbackground=C["border"],
                 highlightcolor=C["accent"]).pack(fill="x", pady=(2, 16), ipady=6)

        btn = tk.Button(card, text="  LOG IN  ", font=FONT_BOLD,
                        bg=C["accent"], fg="white", relief="flat",
                        activebackground=C["sidebar_h"], activeforeground="white",
                        cursor="hand2", command=self._login)
        btn.pack(fill="x", ipady=8)

        self.err_lbl = tk.Label(card, text="", font=FONT_SM, bg=C["card"], fg=C["danger"])
        self.err_lbl.pack(pady=(6, 0))

        self.bind("<Return>", lambda e: self._login())

    def _login(self):
        from core.database import get_connection
        u, p = self.user_var.get().strip(), self.pass_var.get().strip()
        conn  = get_connection()
        row   = conn.execute(
            "SELECT * FROM users WHERE username=? AND password=?", (u, p)
        ).fetchone()
        conn.close()
        if row:
            self.destroy()
            app = MainApp(dict(row))
            app.mainloop()
        else:
            self.err_lbl.config(text="Invalid username or password.")


# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN APPLICATION
# ═══════════════════════════════════════════════════════════════════════════════

class MainApp(tk.Tk):
    def __init__(self, user):
        super().__init__()
        self.user = user
        self.title(f"PRMS – {user['full_name']} ({user['role'].title()})")
        self.geometry("1100x680")
        self.minsize(900, 580)
        self.configure(bg=C["bg"])
        self._active_btn = None
        self._build_layout()
        self._show_dashboard()
        self.eval('tk::PlaceWindow . center')

    # ── Layout skeleton ────────────────────────────────────────────────────────

    def _build_layout(self):
        # Sidebar
        self.sidebar = tk.Frame(self, bg=C["sidebar"], width=200)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        tk.Label(self.sidebar, text="PRMS", font=("Segoe UI", 20, "bold"),
                 bg=C["sidebar"], fg="white").pack(pady=(20, 2))
        tk.Label(self.sidebar, text="School Management", font=FONT_SM,
                 bg=C["sidebar"], fg="#93C5FD").pack(pady=(0, 20))

        sep = tk.Frame(self.sidebar, bg="#2D5A8A", height=1)
        sep.pack(fill="x", padx=10)

        # Navigation buttons
        nav = [
            ("🏠  Dashboard",    self._show_dashboard),
            ("🎓  Pupils",       self._show_pupils),
            ("📝  Marks Entry",  self._show_marks),
            ("📊  Reports",      self._show_reports),
            ("🏫  Classes",      self._show_classes),
            ("📚  Subjects",     self._show_subjects),
            ("⚙️  Settings",     self._show_settings),
        ]
        self._nav_buttons = []
        for label, cmd in nav:
            btn = tk.Button(self.sidebar, text=label, font=FONT,
                            bg=C["sidebar"], fg="white", relief="flat",
                            activebackground=C["sidebar_h"], activeforeground="white",
                            anchor="w", padx=18, cursor="hand2",
                            command=lambda c=cmd, b=None: self._nav_click(c))
            btn.pack(fill="x", pady=1)
            self._nav_buttons.append((btn, cmd))
            btn.config(command=lambda c=cmd, bt=btn: self._nav_click(c, bt))

        # Bottom: user info + logout
        tk.Frame(self.sidebar, bg=C["sidebar"]).pack(expand=True)
        tk.Label(self.sidebar, text=f"👤 {self.user['full_name']}",
                 font=FONT_SM, bg=C["sidebar"], fg="#93C5FD",
                 wraplength=180).pack(pady=(0, 2))
        tk.Button(self.sidebar, text="Logout", font=FONT_SM,
                  bg="#7F1D1D", fg="white", relief="flat", cursor="hand2",
                  command=self._logout).pack(pady=(0, 16), padx=14, fill="x")

        # Main content area
        self.content = tk.Frame(self, bg=C["bg"])
        self.content.pack(side="left", fill="both", expand=True)

    def _nav_click(self, cmd, btn=None):
        if self._active_btn:
            self._active_btn.config(bg=C["sidebar"])
        if btn:
            btn.config(bg=C["sidebar_h"])
            self._active_btn = btn
        cmd()

    def _clear_content(self):
        for w in self.content.winfo_children():
            w.destroy()

    def _logout(self):
        self.destroy()
        LoginWindow().mainloop()

    # ── Reusable widgets ───────────────────────────────────────────────────────

    def _page_header(self, title, subtitle=""):
        hdr = tk.Frame(self.content, bg=C["header"], padx=24, pady=14)
        hdr.pack(fill="x")
        tk.Label(hdr, text=title, font=FONT_H1, bg=C["header"], fg="white").pack(anchor="w")
        if subtitle:
            tk.Label(hdr, text=subtitle, font=FONT_SM, bg=C["header"], fg="#93C5FD").pack(anchor="w")

    def _card(self, parent, **kw):
        f = tk.Frame(parent, bg=C["card"], relief="flat", bd=0, **kw)
        return f

    def _btn(self, parent, text, cmd, color=None, **kw):
        color = color or C["accent"]
        return tk.Button(parent, text=text, font=FONT_BOLD,
                         bg=color, fg="white", relief="flat",
                         activebackground=color, activeforeground="white",
                         cursor="hand2", padx=12, pady=6,
                         command=cmd, **kw)

    def _make_treeview(self, parent, columns, heights=16):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("PRMS.Treeview",
                        background=C["card"],
                        fieldbackground=C["card"],
                        rowheight=28,
                        font=FONT,
                        borderwidth=0)
        style.configure("PRMS.Treeview.Heading",
                        background=C["header"],
                        foreground="white",
                        font=FONT_BOLD,
                        relief="flat")
        style.map("PRMS.Treeview", background=[("selected", C["accent"])])

        tree = ttk.Treeview(parent, columns=columns, show="headings",
                            style="PRMS.Treeview", height=heights)
        sb = ttk.Scrollbar(parent, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=sb.set)
        tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        tree.tag_configure("even", background=C["row_even"])
        tree.tag_configure("odd",  background=C["row_odd"])
        return tree

    # ═══════════════════════════════════════════════════════════════════════════
    #  DASHBOARD
    # ═══════════════════════════════════════════════════════════════════════════

    def _show_dashboard(self):
        self._clear_content()
        self._page_header("Dashboard", "Welcome to the Pupil Results Management System")

        stats = get_dashboard_stats()

        body = tk.Frame(self.content, bg=C["bg"], padx=24, pady=20)
        body.pack(fill="both", expand=True)

        # Stat cards row
        stat_data = [
            ("🎓 Total Pupils",   stats["pupils"],        C["accent"]),
            ("🏫 Classes",        stats["classes"],       "#7C3AED"),
            ("📚 Subjects",       stats["subjects"],      "#D97706"),
            ("📝 Marks Entered",  stats["marks_entered"], C["accent2"]),
        ]
        row = tk.Frame(body, bg=C["bg"])
        row.pack(fill="x", pady=(0, 20))

        for label, val, color in stat_data:
            card = tk.Frame(row, bg=color, padx=20, pady=16)
            card.pack(side="left", fill="both", expand=True, padx=(0, 12))
            tk.Label(card, text=str(val), font=("Segoe UI", 32, "bold"),
                     bg=color, fg="white").pack()
            tk.Label(card, text=label, font=FONT_BOLD,
                     bg=color, fg="white").pack()

        # Quick-action buttons
        qa = tk.Frame(body, bg=C["card"], padx=20, pady=20)
        qa.pack(fill="x")
        tk.Label(qa, text="Quick Actions", font=FONT_H2,
                 bg=C["card"], fg=C["text"]).pack(anchor="w", pady=(0, 12))

        btns_row = tk.Frame(qa, bg=C["card"])
        btns_row.pack(fill="x")
        actions = [
            ("➕ Register Pupil",   self._show_pupils,   C["accent"]),
            ("📝 Enter Marks",      self._show_marks,    "#7C3AED"),
            ("📊 Generate Report",  self._show_reports,  C["accent2"]),
            ("🏫 Add Class",        self._show_classes,  "#D97706"),
        ]
        for text, cmd, color in actions:
            tk.Button(btns_row, text=text, font=FONT_BOLD,
                      bg=color, fg="white", relief="flat",
                      cursor="hand2", padx=16, pady=10,
                      command=cmd).pack(side="left", padx=(0, 10))

        # Footer note
        tk.Label(body,
                 text="PRMS — Designed for Zambian Schools (Grades 1–12) | Powered by Python & SQLite",
                 font=FONT_SM, bg=C["bg"], fg=C["light"]).pack(side="bottom")

    # ═══════════════════════════════════════════════════════════════════════════
    #  PUPILS
    # ═══════════════════════════════════════════════════════════════════════════

    def _show_pupils(self):
        self._clear_content()
        self._page_header("Pupil Registration", "Register, search, edit, and delete pupils")

        body = tk.Frame(self.content, bg=C["bg"], padx=20, pady=16)
        body.pack(fill="both", expand=True)

        # Toolbar
        toolbar = tk.Frame(body, bg=C["bg"])
        toolbar.pack(fill="x", pady=(0, 10))

        self._btn(toolbar, "➕ Register New Pupil", self._open_pupil_form).pack(side="left")

        self.pupil_search = tk.StringVar()
        tk.Entry(toolbar, textvariable=self.pupil_search, font=FONT,
                 relief="flat", highlightthickness=1,
                 highlightbackground=C["border"], width=28,
                 highlightcolor=C["accent"]).pack(side="left", padx=(12, 4), ipady=5)
        self._btn(toolbar, "🔍 Search", lambda: self._load_pupils(), color="#6B7280").pack(side="left")
        self._btn(toolbar, "↺ Reset", self._reset_pupil_search, color="#6B7280").pack(side="left", padx=(4,0))

        # Table
        tbl_frame = tk.Frame(body, bg=C["card"])
        tbl_frame.pack(fill="both", expand=True)

        cols = ("admission_no", "name", "gender", "class", "parent", "phone")
        self.pupil_tree = self._make_treeview(tbl_frame, cols)
        for col, w, label in [
            ("admission_no", 110, "Adm. No."),
            ("name",         200, "Full Name"),
            ("gender",        70, "Gender"),
            ("class",        120, "Class"),
            ("parent",       160, "Parent/Guardian"),
            ("phone",        120, "Phone"),
        ]:
            self.pupil_tree.heading(col, text=label)
            self.pupil_tree.column(col, width=w, anchor="w")

        # Action buttons below table
        act = tk.Frame(body, bg=C["bg"], pady=8)
        act.pack(fill="x")
        self._btn(act, "✏️ Edit Selected",   self._edit_pupil,   color="#D97706").pack(side="left")
        self._btn(act, "🗑️ Delete Selected", self._delete_pupil, color=C["danger"]).pack(side="left", padx=(8,0))

        self._load_pupils()

    def _load_pupils(self, search=None):
        search = self.pupil_search.get().strip() or None
        pupils = get_all_pupils(search=search)
        self.pupil_tree.delete(*self.pupil_tree.get_children())
        for i, p in enumerate(pupils):
            class_lbl = f"Grade {p['grade']}{p['section']}" if p.get('grade') else "—"
            tag = "even" if i % 2 == 0 else "odd"
            self.pupil_tree.insert("", "end", iid=str(p['id']),
                values=(p['admission_no'],
                        f"{p['first_name']} {p['last_name']}",
                        p['gender'], class_lbl,
                        p.get('parent_name') or "—",
                        p.get('parent_phone') or "—"),
                tags=(tag,))

    def _reset_pupil_search(self):
        self.pupil_search.set("")
        self._load_pupils()

    def _open_pupil_form(self, pupil_data=None):
        PupilForm(self, pupil_data, on_save=self._load_pupils)

    def _edit_pupil(self):
        sel = self.pupil_tree.selection()
        if not sel:
            messagebox.showinfo("Select Pupil", "Please select a pupil to edit.")
            return
        pid  = int(sel[0])
        data = get_pupil_by_id(pid)
        self._open_pupil_form(data)

    def _delete_pupil(self):
        sel = self.pupil_tree.selection()
        if not sel:
            messagebox.showinfo("Select Pupil", "Please select a pupil to delete.")
            return
        pid = int(sel[0])
        p   = get_pupil_by_id(pid)
        if messagebox.askyesno("Confirm Delete",
                f"Delete {p['first_name']} {p['last_name']}?\nAll their marks will also be removed."):
            ok, msg = delete_pupil(pid)
            messagebox.showinfo("Result", msg)
            self._load_pupils()

    # ═══════════════════════════════════════════════════════════════════════════
    #  MARKS ENTRY
    # ═══════════════════════════════════════════════════════════════════════════

    def _show_marks(self):
        self._clear_content()
        self._page_header("Marks Entry", "Enter CA (40) and Exam (60) scores per subject")

        body = tk.Frame(self.content, bg=C["bg"], padx=20, pady=16)
        body.pack(fill="both", expand=True)

        # Filter bar
        filt = self._card(body, padx=16, pady=12)
        filt.pack(fill="x", pady=(0, 12))

        tk.Label(filt, text="Class:", font=FONT_BOLD, bg=C["card"]).grid(row=0, col=0, sticky="w", padx=(0,4))
        self.m_class_var = tk.StringVar()
        classes = get_all_classes()
        class_labels = [f"Grade {c['grade']}{c['section']} ({c['year']})" for c in classes]
        self.m_class_ids = [c['id'] for c in classes]
        cb_class = ttk.Combobox(filt, textvariable=self.m_class_var, values=class_labels,
                                state="readonly", width=22, font=FONT)
        cb_class.grid(row=0, column=1, padx=(0, 16))
        if class_labels: cb_class.current(0)

        tk.Label(filt, text="Term:", font=FONT_BOLD, bg=C["card"]).grid(row=0, column=2, sticky="w", padx=(0,4))
        self.m_term_var = tk.StringVar(value="1")
        ttk.Combobox(filt, textvariable=self.m_term_var,
                     values=["1","2","3"], state="readonly", width=6, font=FONT).grid(row=0, column=3, padx=(0,16))

        tk.Label(filt, text="Year:", font=FONT_BOLD, bg=C["card"]).grid(row=0, column=4, sticky="w", padx=(0,4))
        self.m_year_var = tk.StringVar(value="2024")
        ttk.Combobox(filt, textvariable=self.m_year_var,
                     values=["2022","2023","2024","2025","2026"],
                     state="readonly", width=8, font=FONT).grid(row=0, column=5, padx=(0,16))

        tk.Label(filt, text="Subject:", font=FONT_BOLD, bg=C["card"]).grid(row=0, column=6, sticky="w", padx=(0,4))
        self.m_subj_var = tk.StringVar()
        subjects = get_all_subjects()
        subj_labels = [s['name'] for s in subjects]
        self.m_subj_ids = [s['id'] for s in subjects]
        cb_subj = ttk.Combobox(filt, textvariable=self.m_subj_var, values=subj_labels,
                               state="readonly", width=22, font=FONT)
        cb_subj.grid(row=0, column=7, padx=(0,12))
        if subj_labels: cb_subj.current(0)

        self._btn(filt, "Load Pupils", self._load_marks_table,
                  color=C["accent"]).grid(row=0, column=8, padx=(0,8))
        self._btn(filt, "➕ Add Marks", self._add_marks_for_selected,
              color="#0EA5E9").grid(row=0, column=9, padx=(0,8))
        self._btn(filt, "💾 Save All", self._save_all_marks,
              color=C["accent2"]).grid(row=0, column=10)

        tk.Label(
            filt,
            text="Tip: Select a pupil and click Add Marks, or double-click a pupil row for one-step entry.",
            font=FONT_SM,
            bg=C["card"],
            fg=C["light"]
        ).grid(row=1, column=0, columnspan=11, sticky="w", pady=(10, 0))

        # Marks table
        tbl_wrap = tk.Frame(body, bg=C["card"])
        tbl_wrap.pack(fill="both", expand=True)

        cols = ("admission_no", "name", "ca", "exam", "total", "grade")
        self.marks_tree = ttk.Treeview(tbl_wrap, columns=cols, show="headings",
                                       style="PRMS.Treeview", height=18)
        for col, w, label in [
            ("admission_no", 110, "Adm. No."),
            ("name",         220, "Pupil Name"),
            ("ca",            90, "CA Score (40)"),
            ("exam",         100, "Exam Score (60)"),
            ("total",         80, "Total (100)"),
            ("grade",         80, "Grade"),
        ]:
            self.marks_tree.heading(col, text=label)
            self.marks_tree.column(col, width=w, anchor="center")
        sb = ttk.Scrollbar(tbl_wrap, orient="vertical", command=self.marks_tree.yview)
        self.marks_tree.configure(yscrollcommand=sb.set)
        self.marks_tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self.marks_tree.bind("<Double-1>", self._open_add_marks_on_double_click)

        actions = tk.Frame(body, bg=C["bg"], pady=8)
        actions.pack(fill="x")
        self._btn(actions, "✏️ Edit Selected CA", self._edit_selected_ca, color="#D97706").pack(side="left")
        self._btn(actions, "✏️ Edit Selected Exam", self._edit_selected_exam, color="#7C3AED").pack(side="left", padx=(8, 0))

        self._marks_data = {}  # pupil_id -> {ca, exam}

    def _load_marks_table(self):
        classes = get_all_classes()
        class_labels = [f"Grade {c['grade']}{c['section']} ({c['year']})" for c in classes]
        if self.m_class_var.get() not in class_labels:
            messagebox.showwarning("Select Class", "Please select a class first.")
            return
        cid = classes[class_labels.index(self.m_class_var.get())]['id']

        subjects = get_all_subjects()
        subj_labels = [s['name'] for s in subjects]
        if self.m_subj_var.get() not in subj_labels:
            messagebox.showwarning("Select Subject", "Please select a subject first.")
            return
        sid = subjects[subj_labels.index(self.m_subj_var.get())]['id']

        term = int(self.m_term_var.get())
        year = int(self.m_year_var.get())

        rows = get_class_marks(cid, sid, term, year)
        self.marks_tree.delete(*self.marks_tree.get_children())
        self._marks_data = {}

        for i, r in enumerate(rows):
            g, _ = get_grade(r['total'])
            tag = "even" if i % 2 == 0 else "odd"
            self.marks_tree.insert("", "end", iid=str(r['id']),
                values=(r['admission_no'], f"{r['first_name']} {r['last_name']}",
                        r['ca_score'], r['exam_score'], r['total'], g),
                tags=(tag,))
            self._marks_data[r['id']] = {"ca": r['ca_score'], "exam": r['exam_score'],
                                          "class_id": cid, "subject_id": sid,
                                          "term": term, "year": year}

    def _prompt_mark(self, title, current, max_value):
        return simpledialog.askfloat(
            title,
            f"Enter {title}:",
            initialvalue=current,
            minvalue=0,
            maxvalue=max_value,
        )

    def _update_marks_row(self, pid, field, value):
        if pid not in self._marks_data:
            return
        self._marks_data[pid][field] = value
        ca = self._marks_data[pid]["ca"]
        exam = self._marks_data[pid]["exam"]
        total = ca + exam
        grade, _ = get_grade(total)
        self.marks_tree.set(str(pid), field, value)
        self.marks_tree.set(str(pid), "total", total)
        self.marks_tree.set(str(pid), "grade", grade)

    def _add_marks_for_selected(self):
        sel = self.marks_tree.selection()
        if not sel:
            messagebox.showinfo("Select Pupil", "Please select a pupil row first.")
            return

        pid = int(sel[0])
        current = self._marks_data.get(pid, {})
        pupil_name = self.marks_tree.set(sel[0], "name")

        dialog = tk.Toplevel(self)
        dialog.title("Add Marks")
        dialog.geometry("360x210")
        dialog.resizable(False, False)
        dialog.configure(bg=C["bg"])
        dialog.transient(self)
        dialog.grab_set()

        card = tk.Frame(dialog, bg=C["card"], padx=16, pady=14)
        card.pack(fill="both", expand=True, padx=14, pady=14)

        tk.Label(card, text=f"Pupil: {pupil_name}", font=FONT_BOLD, bg=C["card"], fg=C["text"]).grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 10)
        )

        tk.Label(card, text="CA Score (0-40)", font=FONT_BOLD, bg=C["card"], fg=C["text"]).grid(
            row=1, column=0, sticky="w", padx=(0, 8), pady=4
        )
        ca_var = tk.StringVar(value=str(current.get("ca", 0)))
        tk.Entry(
            card,
            textvariable=ca_var,
            font=FONT,
            width=12,
            relief="flat",
            highlightthickness=1,
            highlightbackground=C["border"],
            highlightcolor=C["accent"],
        ).grid(row=1, column=1, sticky="w", pady=4, ipady=4)

        tk.Label(card, text="Exam Score (0-60)", font=FONT_BOLD, bg=C["card"], fg=C["text"]).grid(
            row=2, column=0, sticky="w", padx=(0, 8), pady=4
        )
        exam_var = tk.StringVar(value=str(current.get("exam", 0)))
        tk.Entry(
            card,
            textvariable=exam_var,
            font=FONT,
            width=12,
            relief="flat",
            highlightthickness=1,
            highlightbackground=C["border"],
            highlightcolor=C["accent"],
        ).grid(row=2, column=1, sticky="w", pady=4, ipady=4)

        btn_row = tk.Frame(card, bg=C["card"])
        btn_row.grid(row=3, column=0, columnspan=2, sticky="w", pady=(14, 0))

        def submit():
            try:
                ca = float(ca_var.get())
                exam = float(exam_var.get())
            except ValueError:
                messagebox.showwarning("Invalid Input", "Enter numeric values for CA and Exam.", parent=dialog)
                return

            if not (0 <= ca <= 40):
                messagebox.showwarning("Invalid CA", "CA score must be between 0 and 40.", parent=dialog)
                return
            if not (0 <= exam <= 60):
                messagebox.showwarning("Invalid Exam", "Exam score must be between 0 and 60.", parent=dialog)
                return

            self._update_marks_row(pid, "ca", ca)
            self._update_marks_row(pid, "exam", exam)
            dialog.destroy()

        self._btn(btn_row, "Save", submit, color=C["accent2"]).pack(side="left")
        self._btn(btn_row, "Cancel", dialog.destroy, color=C["light"]).pack(side="left", padx=(8, 0))

        dialog.bind("<Return>", lambda _e: submit())
        dialog.bind("<Escape>", lambda _e: dialog.destroy())

    def _edit_selected_ca(self):
        sel = self.marks_tree.selection()
        if not sel:
            messagebox.showinfo("Select Pupil", "Please select a pupil row first.")
            return
        pid = int(sel[0])
        current = self._marks_data.get(pid, {}).get("ca", 0)
        val = self._prompt_mark("CA Score (max 40)", current, 40)
        if val is None:
            return
        self._update_marks_row(pid, "ca", val)

    def _edit_selected_exam(self):
        sel = self.marks_tree.selection()
        if not sel:
            messagebox.showinfo("Select Pupil", "Please select a pupil row first.")
            return
        pid = int(sel[0])
        current = self._marks_data.get(pid, {}).get("exam", 0)
        val = self._prompt_mark("Exam Score (max 60)", current, 60)
        if val is None:
            return
        self._update_marks_row(pid, "exam", val)

    def _open_add_marks_on_double_click(self, event):
        item = self.marks_tree.identify_row(event.y)
        if not item:
            return
        self.marks_tree.selection_set(item)
        self.marks_tree.focus(item)
        self._add_marks_for_selected()

    def _edit_marks_cell(self, event):
        item = self.marks_tree.identify_row(event.y)
        col  = self.marks_tree.identify_column(event.x)
        if not item or col not in ("#3", "#4"):
            return
        pid  = int(item)
        data = self._marks_data.get(pid, {})
        field = "CA Score (max 40)" if col == "#3" else "Exam Score (max 60)"
        current = data.get("ca" if col == "#3" else "exam", 0)
        val = self._prompt_mark(field, current, 40 if col == "#3" else 60)
        if val is None:
            return
        self._update_marks_row(pid, "ca" if col == "#3" else "exam", val)

    def _save_all_marks(self):
        if not self._marks_data:
            messagebox.showwarning("No Data", "Load pupils first.")
            return
        errors = []
        for pid, d in self._marks_data.items():
            ok, msg = save_marks(pid, d['subject_id'], d['class_id'],
                                 d['term'], d['year'], d['ca'], d['exam'])
            if not ok:
                errors.append(msg)
        if errors:
            messagebox.showerror("Errors", "\n".join(errors))
        else:
            messagebox.showinfo("Saved", f"Marks saved for {len(self._marks_data)} pupils.")

    # ═══════════════════════════════════════════════════════════════════════════
    #  REPORTS
    # ═══════════════════════════════════════════════════════════════════════════

    def _show_reports(self):
        self._clear_content()
        self._page_header("Reports", "Generate individual report cards and class result sheets")

        body = tk.Frame(self.content, bg=C["bg"], padx=20, pady=16)
        body.pack(fill="both", expand=True)

        # ── Individual Report Card ────────────────────────────────────────────
        card1 = self._card(body, padx=20, pady=16)
        card1.pack(fill="x", pady=(0, 14))
        tk.Label(card1, text="📄 Individual Report Card", font=FONT_H2,
                 bg=C["card"], fg=C["text"]).grid(row=0, column=0, columnspan=6, sticky="w", pady=(0,10))

        tk.Label(card1, text="Pupil Adm. No.:", font=FONT_BOLD, bg=C["card"]).grid(row=1, column=0, sticky="w", padx=(0,6))
        self.r_adm = tk.StringVar()
        tk.Entry(card1, textvariable=self.r_adm, font=FONT, width=14, relief="flat",
                 highlightthickness=1, highlightbackground=C["border"]).grid(row=1, column=1, padx=(0,14), ipady=4)

        tk.Label(card1, text="Term:", font=FONT_BOLD, bg=C["card"]).grid(row=1, column=2, sticky="w", padx=(0,4))
        self.r_term = tk.StringVar(value="1")
        ttk.Combobox(card1, textvariable=self.r_term, values=["1","2","3"],
                     state="readonly", width=5, font=FONT).grid(row=1, column=3, padx=(0,14))

        tk.Label(card1, text="Year:", font=FONT_BOLD, bg=C["card"]).grid(row=1, column=4, sticky="w", padx=(0,4))
        self.r_year = tk.StringVar(value="2024")
        ttk.Combobox(card1, textvariable=self.r_year,
                     values=["2022","2023","2024","2025","2026"],
                     state="readonly", width=7, font=FONT).grid(row=1, column=5, padx=(0,14))

        self._btn(card1, "📄 Generate PDF", self._gen_report_card,
              color=C["accent"]).grid(row=1, column=6, padx=(0,8))
        self._btn(card1, "📧 Email Parent", self._send_report_email,
              color="#0EA5E9").grid(row=2, column=1, sticky="w", pady=(10, 0), padx=(0, 8))
        self._btn(card1, "📱 SMS Parent", self._send_report_sms,
              color="#7C3AED").grid(row=2, column=2, sticky="w", pady=(10, 0), padx=(0, 8))
        self._btn(card1, "💬 WhatsApp Parent", self._send_report_whatsapp,
              color="#16A34A").grid(row=2, column=3, sticky="w", pady=(10, 0), padx=(0, 8))
        tk.Label(card1, text="Uses the pupil's stored parent contact details.", font=FONT_SM,
             bg=C["card"], fg=C["light"]).grid(row=3, column=0, columnspan=7, sticky="w", pady=(8, 0))

        # ── Class Results Sheet ───────────────────────────────────────────────
        card2 = self._card(body, padx=20, pady=16)
        card2.pack(fill="x", pady=(0, 14))
        tk.Label(card2, text="📊 Class Results Sheet", font=FONT_H2,
                 bg=C["card"], fg=C["text"]).grid(row=0, column=0, columnspan=6, sticky="w", pady=(0,10))

        tk.Label(card2, text="Class:", font=FONT_BOLD, bg=C["card"]).grid(row=1, column=0, sticky="w", padx=(0,4))
        self.rc_class_var = tk.StringVar()
        classes = get_all_classes()
        class_labels = [f"Grade {c['grade']}{c['section']} ({c['year']})" for c in classes]
        self._rc_class_ids = [c['id'] for c in classes]
        cb = ttk.Combobox(card2, textvariable=self.rc_class_var, values=class_labels,
                          state="readonly", width=24, font=FONT)
        cb.grid(row=1, column=1, padx=(0,14))
        if class_labels: cb.current(0)

        tk.Label(card2, text="Term:", font=FONT_BOLD, bg=C["card"]).grid(row=1, column=2, sticky="w", padx=(0,4))
        self.rc_term = tk.StringVar(value="1")
        ttk.Combobox(card2, textvariable=self.rc_term, values=["1","2","3"],
                     state="readonly", width=5, font=FONT).grid(row=1, column=3, padx=(0,14))

        tk.Label(card2, text="Year:", font=FONT_BOLD, bg=C["card"]).grid(row=1, column=4, sticky="w", padx=(0,4))
        self.rc_year = tk.StringVar(value="2024")
        ttk.Combobox(card2, textvariable=self.rc_year,
                     values=["2022","2023","2024","2025","2026"],
                     state="readonly", width=7, font=FONT).grid(row=1, column=5, padx=(0,14))

        self._btn(card2, "📊 Generate Class PDF", self._gen_class_sheet,
                  color="#7C3AED").grid(row=1, column=6, padx=(0,8))

        self._btn(card2, "📜 Delivery History", self._show_delivery_history,
              color="#475569").grid(row=2, column=1, sticky="w", pady=(10, 0), padx=(0, 8))

        # ── Output log ────────────────────────────────────────────────────────
        card3 = self._card(body, padx=16, pady=12)
        card3.pack(fill="both", expand=True)
        tk.Label(card3, text="Output Log", font=FONT_H2, bg=C["card"], fg=C["text"]).pack(anchor="w")
        self.log_text = tk.Text(card3, font=FONT_SM, height=10, relief="flat",
                                bg="#F8FAFC", fg=C["text"],
                                highlightthickness=1, highlightbackground=C["border"])
        self.log_text.pack(fill="both", expand=True, pady=(6, 0))
        self.log_text.insert("end", "Reports will be saved to: reports_output/\n")
        self.log_text.config(state="disabled")

    def _log(self, msg):
        self.log_text.config(state="normal")
        self.log_text.insert("end", f"✅ {msg}\n")
        self.log_text.see("end")
        self.log_text.config(state="disabled")

    def _delivery_settings(self):
        settings = dict(os.environ)
        settings.update(get_app_settings())
        return settings

    def _show_settings(self):
        self._clear_content()
        self._page_header("Settings", "Configure report delivery credentials and defaults")

        body = tk.Frame(self.content, bg=C["bg"], padx=20, pady=16)
        body.pack(fill="both", expand=True)

        card = self._card(body, padx=20, pady=18)
        card.pack(fill="both", expand=True)

        tk.Label(card, text="Messaging Configuration", font=FONT_H2, bg=C["card"], fg=C["text"]).grid(
            row=0, column=0, columnspan=4, sticky="w", pady=(0, 12)
        )

        fields = [
            ("EMAIL_SMTP_HOST", "SMTP Host", 0, 0, False),
            ("EMAIL_SMTP_PORT", "SMTP Port", 0, 2, False),
            ("EMAIL_SMTP_USER", "SMTP Username", 1, 0, False),
            ("EMAIL_SMTP_PASSWORD", "SMTP Password", 1, 2, True),
            ("EMAIL_FROM", "From Email", 2, 0, False),
            ("EMAIL_USE_STARTTLS", "Use STARTTLS (1/0)", 2, 2, False),
            ("TWILIO_ACCOUNT_SID", "Twilio Account SID", 3, 0, False),
            ("TWILIO_AUTH_TOKEN", "Twilio Auth Token", 3, 2, True),
            ("TWILIO_FROM_SMS", "Twilio SMS Number", 4, 0, False),
            ("TWILIO_FROM_WHATSAPP", "Twilio WhatsApp Number", 4, 2, False),
        ]

        self.settings_vars = {}
        current = self._delivery_settings()

        for key, label, row, col, is_secret in fields:
            tk.Label(card, text=label, font=FONT_BOLD, bg=C["card"], fg=C["text"]).grid(
                row=row * 2 + 1, column=col, sticky="w", padx=(0, 10), pady=(4, 2)
            )
            var = tk.StringVar(value=current.get(key, "") or "")
            self.settings_vars[key] = var
            tk.Entry(
                card,
                textvariable=var,
                font=FONT,
                width=30,
                show="*" if is_secret else "",
                relief="flat",
                highlightthickness=1,
                highlightbackground=C["border"],
                highlightcolor=C["accent"],
            ).grid(row=row * 2 + 2, column=col, sticky="w", padx=(0, 18), pady=(0, 10), ipady=4)

        btn_row = tk.Frame(card, bg=C["card"])
        btn_row.grid(row=11, column=0, columnspan=4, sticky="w", pady=(12, 0))
        self._btn(btn_row, "💾 Save Settings", self._save_settings, color=C["accent2"]).pack(side="left")
        tk.Label(
            card,
            text="SMS and WhatsApp use a Twilio-compatible provider. Leave fields blank if you want to use environment variables.",
            font=FONT_SM,
            bg=C["card"],
            fg=C["light"],
            wraplength=700,
            justify="left",
        ).grid(row=12, column=0, columnspan=4, sticky="w", pady=(14, 0))

    def _save_settings(self):
        payload = {key: var.get().strip() for key, var in self.settings_vars.items()}
        ok, msg = save_app_settings(payload)
        if ok:
            self._log("Delivery settings saved.")
            messagebox.showinfo("Settings Saved", msg)
        else:
            messagebox.showerror("Settings Error", msg)

    def _get_selected_report_context(self):
        adm = self.r_adm.get().strip()
        if not adm:
            messagebox.showwarning("Input Required", "Enter pupil admission number.")
            return None, None, None

        from core.database import get_connection

        conn = get_connection()
        row = conn.execute(
            "SELECT id, first_name, last_name, parent_name, parent_phone, parent_email FROM pupil WHERE admission_no=?",
            (adm,),
        ).fetchone()
        conn.close()

        if not row:
            messagebox.showerror("Not Found", f"No pupil with admission no: {adm}")
            return None, None, None

        term = int(self.r_term.get())
        year = int(self.r_year.get())
        context = get_report_card_context(row["id"], term, year)
        if not context:
            messagebox.showerror("No Marks", "No marks found for this term/year.")
            return None, None, None

        pdf_path, msg = generate_report_card_text(row["id"], term, year)
        if not pdf_path:
            messagebox.showerror("Error", msg)
            return None, None, None

        return row, context, pdf_path

    def _gen_report_card(self):
        row, context, path = self._get_selected_report_context()
        if not path or not row or not context:
            return
        self._log(f"Report card saved: {os.path.basename(path)}")
        messagebox.showinfo("Generated", f"PDF report card saved!\n{path}")

    def _send_report_email(self):
        row, context, pdf_path = self._get_selected_report_context()
        if not pdf_path or not row or not context:
            return

        recipient = (row.get("parent_email") or "").strip()
        if not recipient:
            messagebox.showwarning("Missing Email", "This pupil has no parent email saved.")
            return

        subject = f"PRMS Report Card - {context['pupil']['first_name']} {context['pupil']['last_name']}"
        body = build_report_summary(context) + "\n\nAttached is the PDF report card."
        ok, msg = send_email_with_attachment(recipient, subject, body, pdf_path, self._delivery_settings())
        log_report_delivery(row["id"], "REPORT_CARD", "EMAIL", recipient, "SENT" if ok else "FAILED", msg)
        if ok:
            self._log(f"Email sent to {recipient}.")
            messagebox.showinfo("Email Sent", msg)
        else:
            messagebox.showerror("Email Failed", msg)

    def _send_report_sms(self):
        self._send_report_message("SMS")

    def _send_report_whatsapp(self):
        self._send_report_message("WHATSAPP")

    def _send_report_message(self, channel):
        row, context, pdf_path = self._get_selected_report_context()
        if not pdf_path or not row or not context:
            return

        phone = (row.get("parent_phone") or "").strip()
        if not phone:
            messagebox.showwarning("Missing Phone", "This pupil has no parent phone saved.")
            return

        body = build_report_summary(context)
        if channel == "SMS":
            ok, msg = send_sms(phone, body, self._delivery_settings())
        else:
            ok, msg = send_whatsapp(phone, body, self._delivery_settings())

        log_report_delivery(row["id"], "REPORT_CARD", channel, phone, "SENT" if ok else "FAILED", msg)
        if ok:
            self._log(f"{channel.title()} sent to {phone}.")
            messagebox.showinfo(f"{channel.title()} Sent", msg)
        else:
            messagebox.showerror(f"{channel.title()} Failed", msg)

    def _gen_class_sheet(self):
        if not self._rc_class_ids:
            messagebox.showwarning("No Classes", "No classes available.")
            return
        classes = get_all_classes()
        labels  = [f"Grade {c['grade']}{c['section']} ({c['year']})" for c in classes]
        if self.rc_class_var.get() not in labels:
            return
        cid  = classes[labels.index(self.rc_class_var.get())]['id']
        term = int(self.rc_term.get())
        year = int(self.rc_year.get())
        path, msg = generate_class_results_text(cid, term, year)
        if path:
            self._log(msg)
            messagebox.showinfo("Generated", f"Class results saved!\n{path}")
        else:
            messagebox.showerror("Error", msg)

    def _show_delivery_history(self):
        self._clear_content()
        self._page_header("Delivery History", "View report cards sent to parents and guardians")

        body = tk.Frame(self.content, bg=C["bg"], padx=20, pady=16)
        body.pack(fill="both", expand=True)

        toolbar = tk.Frame(body, bg=C["bg"])
        toolbar.pack(fill="x", pady=(0, 10))
        tk.Label(toolbar, text="Pupil:", font=FONT_BOLD, bg=C["bg"], fg=C["text"]).pack(side="left", padx=(0, 4))
        self.delivery_search_var = tk.StringVar()
        tk.Entry(
            toolbar,
            textvariable=self.delivery_search_var,
            font=FONT,
            width=22,
            relief="flat",
            highlightthickness=1,
            highlightbackground=C["border"],
            highlightcolor=C["accent"],
        ).pack(side="left", padx=(0, 12), ipady=4)

        tk.Label(toolbar, text="Method:", font=FONT_BOLD, bg=C["bg"], fg=C["text"]).pack(side="left", padx=(0, 4))
        self.delivery_method_var = tk.StringVar(value="All")
        ttk.Combobox(
            toolbar,
            textvariable=self.delivery_method_var,
            values=["All", "EMAIL", "SMS", "WHATSAPP"],
            state="readonly",
            width=12,
            font=FONT,
        ).pack(side="left", padx=(0, 12))

        tk.Label(toolbar, text="Status:", font=FONT_BOLD, bg=C["bg"], fg=C["text"]).pack(side="left", padx=(0, 4))
        self.delivery_status_var = tk.StringVar(value="All")
        ttk.Combobox(
            toolbar,
            textvariable=self.delivery_status_var,
            values=["All", "SENT", "FAILED"],
            state="readonly",
            width=10,
            font=FONT,
        ).pack(side="left", padx=(0, 12))

        self._btn(toolbar, "Filter", self._load_delivery_history, color=C["accent"]).pack(side="left", padx=(0, 8))
        self._btn(toolbar, "Clear", self._clear_delivery_filters, color="#6B7280").pack(side="left", padx=(0, 8))
        self._btn(toolbar, "↺ Refresh", self._load_delivery_history, color="#6B7280").pack(side="left")
        self._btn(toolbar, "CSV", self._export_delivery_history_csv, color="#0F766E").pack(side="right", padx=(8, 0))
        self._btn(toolbar, "PDF", self._export_delivery_history_pdf, color="#7C3AED").pack(side="right", padx=(8, 0))
        self._btn(toolbar, "Open Export Folder", self._open_reports_folder, color="#475569").pack(side="right", padx=(8, 0))

        tbl_wrap = tk.Frame(body, bg=C["card"])
        tbl_wrap.pack(fill="both", expand=True)

        cols = ("created_at", "pupil", "admission_no", "method", "recipient", "status", "report_type", "detail")
        self.delivery_tree = self._make_treeview(tbl_wrap, cols, heights=18)
        headings = [
            ("created_at", 150, "Date/Time"),
            ("pupil", 180, "Pupil"),
            ("admission_no", 100, "Adm. No."),
            ("method", 100, "Method"),
            ("recipient", 160, "Recipient"),
            ("status", 90, "Status"),
            ("report_type", 110, "Report Type"),
            ("detail", 260, "Details"),
        ]
        for col, width, label in headings:
            self.delivery_tree.heading(col, text=label)
            self.delivery_tree.column(col, width=width, anchor="w")
        self.delivery_tree.bind("<Double-1>", self._show_delivery_row_details)

        self._load_delivery_history()

    def _get_filtered_delivery_rows(self):
        return get_report_delivery_history(
            pupil_search=getattr(self, "delivery_search_var", tk.StringVar()).get().strip() or None,
            delivery_method=getattr(self, "delivery_method_var", tk.StringVar(value="All")).get(),
            status=getattr(self, "delivery_status_var", tk.StringVar(value="All")).get(),
        )

    def _load_delivery_history(self):
        if not hasattr(self, "delivery_tree"):
            return
        self.delivery_tree.delete(*self.delivery_tree.get_children())
        rows = self._get_filtered_delivery_rows()
        for index, row in enumerate(rows):
            tag = "even" if index % 2 == 0 else "odd"
            pupil_name = "—"
            if row.get("first_name") or row.get("last_name"):
                pupil_name = f"{row.get('first_name', '')} {row.get('last_name', '')}".strip()
            self.delivery_tree.insert(
                "",
                "end",
                iid=str(row["id"]),
                values=(
                    row.get("created_at") or "—",
                    pupil_name,
                    row.get("admission_no") or "—",
                    row.get("delivery_method") or "—",
                    row.get("recipient") or "—",
                    row.get("status") or "—",
                    row.get("report_type") or "—",
                    row.get("detail") or "—",
                ),
                tags=(tag,),
            )

    def _show_delivery_row_details(self, event):
        item = self.delivery_tree.identify_row(event.y)
        if not item:
            return

        row = None
        for candidate in self._get_filtered_delivery_rows():
            if str(candidate.get("id")) == str(item):
                row = candidate
                break
        if not row:
            return

        pupil_name = "—"
        if row.get("first_name") or row.get("last_name"):
            pupil_name = f"{row.get('first_name', '')} {row.get('last_name', '')}".strip()

        lines = [
            ("Date/Time", row.get("created_at") or "—"),
            ("Pupil", pupil_name),
            ("Admission No.", row.get("admission_no") or "—"),
            ("Report Type", row.get("report_type") or "—"),
            ("Delivery Method", row.get("delivery_method") or "—"),
            ("Status", row.get("status") or "—"),
            ("Recipient", row.get("recipient") or "—"),
            ("Parent Name", row.get("parent_name") or "—"),
            ("Parent Phone", row.get("parent_phone") or "—"),
            ("Parent Email", row.get("parent_email") or "—"),
            ("Details", row.get("detail") or "—"),
        ]

        dialog = tk.Toplevel(self)
        dialog.title("Delivery Details")
        dialog.geometry("520x420")
        dialog.resizable(False, False)
        dialog.configure(bg=C["bg"])
        dialog.transient(self)
        dialog.grab_set()

        card = self._card(dialog, padx=18, pady=16)
        card.pack(fill="both", expand=True, padx=16, pady=16)
        tk.Label(card, text="Delivery Details", font=FONT_H2, bg=C["card"], fg=C["text"]).pack(anchor="w", pady=(0, 10))

        detail_frame = tk.Frame(card, bg=C["card"])
        detail_frame.pack(fill="both", expand=True)

        for label, value in lines:
            row_frame = tk.Frame(detail_frame, bg=C["card"])
            row_frame.pack(fill="x", anchor="w", pady=3)
            tk.Label(row_frame, text=f"{label}:", font=FONT_BOLD, bg=C["card"], fg=C["text"], width=16, anchor="w").pack(side="left")
            tk.Label(row_frame, text=value, font=FONT, bg=C["card"], fg=C["text"], wraplength=340, justify="left").pack(side="left", fill="x", expand=True)

        self._btn(card, "Close", dialog.destroy, color="#6B7280").pack(anchor="e", pady=(12, 0))

    def _export_delivery_history_csv(self):
        rows = self._get_filtered_delivery_rows()
        if not rows:
            messagebox.showinfo("No Data", "There are no delivery records to export.")
            return

        path = filedialog.asksaveasfilename(
            parent=self,
            title="Export Delivery History to CSV",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            initialfile="delivery_history.csv",
        )
        if not path:
            return

        with open(path, "w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.writer(handle)
            writer.writerow(["Date/Time", "Pupil", "Admission No.", "Method", "Recipient", "Status", "Report Type", "Details"])
            for row in rows:
                pupil_name = "—"
                if row.get("first_name") or row.get("last_name"):
                    pupil_name = f"{row.get('first_name', '')} {row.get('last_name', '')}".strip()
                writer.writerow([
                    row.get("created_at") or "",
                    pupil_name,
                    row.get("admission_no") or "",
                    row.get("delivery_method") or "",
                    row.get("recipient") or "",
                    row.get("status") or "",
                    row.get("report_type") or "",
                    row.get("detail") or "",
                ])

        messagebox.showinfo("Exported", f"Delivery history exported to:\n{path}")
        self._open_exported_file(path)

    def _export_delivery_history_pdf(self):
        rows = self._get_filtered_delivery_rows()
        if not rows:
            messagebox.showinfo("No Data", "There are no delivery records to export.")
            return

        path = filedialog.asksaveasfilename(
            parent=self,
            title="Export Delivery History to PDF",
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")],
            initialfile="delivery_history.pdf",
        )
        if not path:
            return

        from reports.messaging import export_delivery_history_pdf

        export_delivery_history_pdf(path, rows)
        messagebox.showinfo("Exported", f"Delivery history exported to:\n{path}")
        self._open_exported_file(path)

    def _open_exported_file(self, path):
        try:
            os.startfile(path)
        except Exception:
            messagebox.showinfo("Exported", f"File saved here:\n{path}")

    def _open_reports_folder(self):
        folder = os.path.join(os.path.dirname(__file__), "reports_output")
        try:
            os.startfile(folder)
        except Exception:
            messagebox.showinfo("Reports Folder", f"Reports folder:\n{folder}")

    def _clear_delivery_filters(self):
        if hasattr(self, "delivery_search_var"):
            self.delivery_search_var.set("")
        if hasattr(self, "delivery_method_var"):
            self.delivery_method_var.set("All")
        if hasattr(self, "delivery_status_var"):
            self.delivery_status_var.set("All")
        self._load_delivery_history()

    # ═══════════════════════════════════════════════════════════════════════════
    #  CLASSES
    # ═══════════════════════════════════════════════════════════════════════════

    def _show_classes(self):
        self._clear_content()
        self._page_header("Class Management", "Add and manage school classes")

        body = tk.Frame(self.content, bg=C["bg"], padx=20, pady=16)
        body.pack(fill="both", expand=True)

        # Add form
        form = self._card(body, padx=16, pady=12)
        form.pack(fill="x", pady=(0, 12))
        tk.Label(form, text="Add New Class", font=FONT_H2, bg=C["card"], fg=C["text"]).grid(
            row=0, column=0, columnspan=7, sticky="w", pady=(0, 8))

        tk.Label(form, text="Grade:", font=FONT_BOLD, bg=C["card"]).grid(row=1, column=0, sticky="w", padx=(0,4))
        self.cl_grade = tk.StringVar(value="1")
        ttk.Combobox(form, textvariable=self.cl_grade,
                     values=[str(i) for i in range(1,13)],
                     state="readonly", width=6, font=FONT).grid(row=1, column=1, padx=(0,12))

        tk.Label(form, text="Section:", font=FONT_BOLD, bg=C["card"]).grid(row=1, column=2, sticky="w", padx=(0,4))
        self.cl_section = tk.StringVar(value="A")
        ttk.Combobox(form, textvariable=self.cl_section,
                     values=["A","B","C","D"],
                     state="readonly", width=6, font=FONT).grid(row=1, column=3, padx=(0,12))

        tk.Label(form, text="Year:", font=FONT_BOLD, bg=C["card"]).grid(row=1, column=4, sticky="w", padx=(0,4))
        self.cl_year = tk.StringVar(value="2024")
        ttk.Combobox(form, textvariable=self.cl_year,
                     values=["2022","2023","2024","2025","2026"],
                     state="readonly", width=8, font=FONT).grid(row=1, column=5, padx=(0,12))

        self._btn(form, "➕ Add Class", self._add_class, color=C["accent"]).grid(row=1, column=6)

        # Table
        tbl = tk.Frame(body, bg=C["card"])
        tbl.pack(fill="both", expand=True)
        cols = ("grade", "section", "year", "pupils")
        self.class_tree = self._make_treeview(tbl, cols, heights=14)
        for col, w, label in [("grade",80,"Grade"),("section",80,"Section"),("year",90,"Year"),("pupils",120,"No. of Pupils")]:
            self.class_tree.heading(col, text=label)
            self.class_tree.column(col, width=w, anchor="center")

        act = tk.Frame(body, bg=C["bg"], pady=8)
        act.pack(fill="x")
        self._btn(act, "🗑️ Delete Selected", self._delete_class, color=C["danger"]).pack(side="left")

        self._load_classes()

    def _load_classes(self):
        from core.database import get_connection
        self.class_tree.delete(*self.class_tree.get_children())
        for i, c in enumerate(get_all_classes()):
            conn = get_connection()
            n = conn.execute("SELECT COUNT(*) FROM pupil WHERE class_id=?", (c['id'],)).fetchone()[0]
            conn.close()
            tag = "even" if i % 2 == 0 else "odd"
            self.class_tree.insert("", "end", iid=str(c['id']),
                values=(f"Grade {c['grade']}", c['section'], c['year'], n), tags=(tag,))

    def _add_class(self):
        ok, msg = add_class(int(self.cl_grade.get()), self.cl_section.get(), int(self.cl_year.get()))
        messagebox.showinfo("Result", msg)
        if ok: self._load_classes()

    def _delete_class(self):
        sel = self.class_tree.selection()
        if not sel:
            messagebox.showinfo("Select", "Select a class first.")
            return
        if messagebox.askyesno("Confirm", "Delete this class? Pupils will be unassigned."):
            ok, msg = delete_class(int(sel[0]))
            messagebox.showinfo("Result", msg)
            if ok: self._load_classes()

    # ═══════════════════════════════════════════════════════════════════════════
    #  SUBJECTS
    # ═══════════════════════════════════════════════════════════════════════════

    def _show_subjects(self):
        self._clear_content()
        self._page_header("Subject Management", "View and manage school subjects")

        body = tk.Frame(self.content, bg=C["bg"], padx=20, pady=16)
        body.pack(fill="both", expand=True)

        form = self._card(body, padx=16, pady=12)
        form.pack(fill="x", pady=(0, 12))
        tk.Label(form, text="Add New Subject", font=FONT_H2, bg=C["card"], fg=C["text"]).grid(
            row=0, column=0, columnspan=5, sticky="w", pady=(0,8))

        tk.Label(form, text="Name:", font=FONT_BOLD, bg=C["card"]).grid(row=1, column=0, sticky="w", padx=(0,4))
        self.s_name = tk.StringVar()
        tk.Entry(form, textvariable=self.s_name, font=FONT, width=26, relief="flat",
                 highlightthickness=1, highlightbackground=C["border"]).grid(row=1, column=1, padx=(0,12), ipady=4)

        tk.Label(form, text="Code:", font=FONT_BOLD, bg=C["card"]).grid(row=1, column=2, sticky="w", padx=(0,4))
        self.s_code = tk.StringVar()
        tk.Entry(form, textvariable=self.s_code, font=FONT, width=8, relief="flat",
                 highlightthickness=1, highlightbackground=C["border"]).grid(row=1, column=3, padx=(0,12), ipady=4)

        self._btn(form, "➕ Add Subject", self._add_subject, color=C["accent"]).grid(row=1, column=4)

        tbl = tk.Frame(body, bg=C["card"])
        tbl.pack(fill="both", expand=True)
        cols = ("code", "name", "max_marks")
        self.subj_tree = self._make_treeview(tbl, cols)
        for col, w, label in [("code",80,"Code"),("name",280,"Subject Name"),("max_marks",100,"Max Marks")]:
            self.subj_tree.heading(col, text=label)
            self.subj_tree.column(col, width=w, anchor="center" if col != "name" else "w")

        act = tk.Frame(body, bg=C["bg"], pady=8)
        act.pack(fill="x")
        self._btn(act, "🗑️ Delete Selected", self._delete_subject, color=C["danger"]).pack(side="left")

        self._load_subjects()

    def _load_subjects(self):
        self.subj_tree.delete(*self.subj_tree.get_children())
        for i, s in enumerate(get_all_subjects()):
            tag = "even" if i % 2 == 0 else "odd"
            self.subj_tree.insert("", "end", iid=str(s['id']),
                values=(s['code'], s['name'], s['max_marks']), tags=(tag,))

    def _add_subject(self):
        name = self.s_name.get().strip()
        code = self.s_code.get().strip().upper()
        if not name or not code:
            messagebox.showwarning("Input Required", "Enter both name and code.")
            return
        ok, msg = add_subject(name, code)
        messagebox.showinfo("Result", msg)
        if ok:
            self.s_name.set("")
            self.s_code.set("")
            self._load_subjects()

    def _delete_subject(self):
        sel = self.subj_tree.selection()
        if not sel:
            messagebox.showinfo("Select", "Select a subject first.")
            return
        if messagebox.askyesno("Confirm", "Delete this subject? All related marks will be removed."):
            ok, msg = delete_subject(int(sel[0]))
            messagebox.showinfo("Result", msg)
            if ok: self._load_subjects()


# ═══════════════════════════════════════════════════════════════════════════════
#  PUPIL FORM (Modal)
# ═══════════════════════════════════════════════════════════════════════════════

class PupilForm(tk.Toplevel):
    def __init__(self, parent, pupil_data=None, on_save=None):
        super().__init__(parent)
        self.pupil_data = pupil_data
        self.on_save    = on_save
        self.title("Edit Pupil" if pupil_data else "Register New Pupil")
        self.geometry("520x500")
        self.resizable(False, False)
        self.configure(bg=C["bg"])
        self.grab_set()
        self._build()
        if pupil_data:
            self._populate()

    def _build(self):
        hdr = tk.Frame(self, bg=C["header"], padx=20, pady=12)
        hdr.pack(fill="x")
        tk.Label(hdr,
                 text="Edit Pupil" if self.pupil_data else "Register New Pupil",
                 font=FONT_H2, bg=C["header"], fg="white").pack(anchor="w")

        body = tk.Frame(self, bg=C["bg"], padx=24, pady=16)
        body.pack(fill="both", expand=True)

        def lbl(text, row, col): tk.Label(body, text=text, font=FONT_BOLD, bg=C["bg"], fg=C["text"]).grid(
            row=row, column=col, sticky="w", pady=4, padx=(0,6))
        def ent(var, row, col, w=22): return tk.Entry(body, textvariable=var, font=FONT, width=w,
            relief="flat", highlightthickness=1, highlightbackground=C["border"],
            highlightcolor=C["accent"]).grid(row=row, column=col, sticky="w", pady=4, ipady=5, padx=(0,16))

        self.v_adm    = tk.StringVar(value=next_admission_number())
        self.v_fname  = tk.StringVar()
        self.v_lname  = tk.StringVar()
        self.v_gender = tk.StringVar(value="Male")
        self.v_dob    = tk.StringVar()
        self.v_parent = tk.StringVar()
        self.v_phone  = tk.StringVar()
        self.v_email  = tk.StringVar()
        self.v_class  = tk.StringVar()

        lbl("Admission No.", 0, 0); ent(self.v_adm,    0, 1)
        lbl("First Name",    1, 0); ent(self.v_fname,  1, 1)
        lbl("Last Name",     2, 0); ent(self.v_lname,  2, 1)

        lbl("Gender", 3, 0)
        ttk.Combobox(body, textvariable=self.v_gender, values=["Male","Female"],
                     state="readonly", width=14, font=FONT).grid(row=3, column=1, sticky="w", pady=4)

        lbl("Date of Birth", 4, 0)
        tk.Entry(body, textvariable=self.v_dob, font=FONT, width=16,
                 relief="flat", highlightthickness=1,
                 highlightbackground=C["border"]).grid(row=4, column=1, sticky="w", pady=4, ipady=5)
        tk.Label(body, text="(YYYY-MM-DD)", font=FONT_SM, bg=C["bg"], fg=C["light"]).grid(row=4, column=2, sticky="w")

        lbl("Class", 5, 0)
        classes = get_all_classes()
        self._class_labels = [f"Grade {c['grade']}{c['section']} ({c['year']})" for c in classes]
        self._class_ids    = [c['id'] for c in classes]
        cb = ttk.Combobox(body, textvariable=self.v_class, values=self._class_labels,
                          state="readonly", width=22, font=FONT)
        cb.grid(row=5, column=1, sticky="w", pady=4)
        if self._class_labels: cb.current(0)

        lbl("Parent/Guardian", 6, 0); ent(self.v_parent, 6, 1)
        lbl("Parent Phone",    7, 0); ent(self.v_phone,  7, 1)
        lbl("Parent Email",    8, 0); ent(self.v_email,  8, 1, w=26)

        btn_row = tk.Frame(body, bg=C["bg"])
        btn_row.grid(row=9, column=0, columnspan=3, pady=(16, 0))
        tk.Button(btn_row, text="💾 Save", font=FONT_BOLD,
                  bg=C["accent2"], fg="white", relief="flat",
                  cursor="hand2", padx=20, pady=8, command=self._save).pack(side="left", padx=(0, 8))
        tk.Button(btn_row, text="Cancel", font=FONT_BOLD,
                  bg=C["light"], fg="white", relief="flat",
                  cursor="hand2", padx=20, pady=8, command=self.destroy).pack(side="left")

    def _populate(self):
        p = self.pupil_data
        self.v_adm.set(p['admission_no'])
        self.v_fname.set(p['first_name'])
        self.v_lname.set(p['last_name'])
        self.v_gender.set(p['gender'])
        self.v_dob.set(p.get('date_of_birth') or "")
        self.v_parent.set(p.get('parent_name') or "")
        self.v_phone.set(p.get('parent_phone') or "")
        self.v_email.set(p.get('parent_email') or "")
        if p.get('class_id') and p['class_id'] in self._class_ids:
            idx = self._class_ids.index(p['class_id'])
            self.v_class.set(self._class_labels[idx])

    def _save(self):
        fname  = self.v_fname.get().strip()
        lname  = self.v_lname.get().strip()
        adm    = self.v_adm.get().strip()
        gender = self.v_gender.get()
        dob    = self.v_dob.get().strip() or None
        parent = self.v_parent.get().strip() or None
        phone  = self.v_phone.get().strip() or None
        email  = self.v_email.get().strip() or None

        if not fname or not lname or not adm:
            messagebox.showwarning("Required Fields", "Admission No., First Name, and Last Name are required.")
            return

        cid = None
        if self.v_class.get() in self._class_labels:
            cid = self._class_ids[self._class_labels.index(self.v_class.get())]

        if self.pupil_data:
            ok, msg = update_pupil(self.pupil_data['id'], fname, lname, gender, dob, cid, parent, phone, email)
        else:
            ok, msg = add_pupil(adm, fname, lname, gender, dob, cid, parent, phone, email)

        if ok:
            if self.on_save: self.on_save()
            self.destroy()
        else:
            messagebox.showerror("Error", msg)


# ═══════════════════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    app = LoginWindow()
    app.mainloop()
