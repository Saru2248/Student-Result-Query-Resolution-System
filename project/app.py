"""
Student Result Query Resolution System
Full-Stack Flask Application
Author: Student Project
"""

from flask import (Flask, render_template, request, redirect,
                   session, jsonify, url_for, flash, send_from_directory,
                   abort, make_response, send_file)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import sqlite3
import os
import uuid
import io
from datetime import datetime
from functools import wraps

# PDF generation
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                 Table, TableStyle, HRFlowable, Image as RLImage)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.pdfgen import canvas as pdfcanvas

# PDF merging
from pypdf import PdfWriter, PdfReader

# Image handling (proof images → PDF page)
from PIL import Image as PILImage

# ─────────────────────────────────────────────
#  APP CONFIGURATION
# ─────────────────────────────────────────────
BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
DB_PATH      = os.path.join(BASE_DIR, "database.db")
UPLOAD_FOLDER = os.path.join(BASE_DIR, "..", "static", "uploads")
ALLOWED_EXT  = {"pdf", "png", "jpg", "jpeg"}
MAX_FILE_MB  = 5

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "..", "templates"),
    static_folder=os.path.join(BASE_DIR, "..", "static")
)
app.secret_key  = "SRQRSystem@2024#SecretKey!"
app.config["UPLOAD_FOLDER"]    = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = MAX_FILE_MB * 1024 * 1024


def allowed_file(filename):
    return ("." in filename and
            filename.rsplit(".", 1)[1].lower() in ALLOWED_EXT)


# ─────────────────────────────────────────────
#  DATABASE HELPERS
# ─────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row          # access columns by name
    return conn


def init_db():
    """Create tables and seed default admin."""
    db = get_db()

    # Users table
    db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            name     TEXT    NOT NULL,
            email    TEXT    UNIQUE NOT NULL,
            prn      TEXT    UNIQUE,
            password TEXT    NOT NULL,
            role     TEXT    NOT NULL DEFAULT 'student',
            created_at TEXT  DEFAULT (datetime('now','localtime'))
        )
    """)

    # Complaints table
    db.execute("""
        CREATE TABLE IF NOT EXISTS complaints (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id          INTEGER NOT NULL,
            subject          TEXT    NOT NULL,
            issue_type       TEXT    NOT NULL,
            description      TEXT    NOT NULL,
            status           TEXT    NOT NULL DEFAULT 'Pending',
            priority         TEXT    NOT NULL DEFAULT 'Normal',
            reply            TEXT    DEFAULT '',
            application_file TEXT    DEFAULT NULL,
            hod_sign_file    TEXT    DEFAULT NULL,
            proof_file       TEXT    DEFAULT NULL,
            is_verified      INTEGER DEFAULT 0,
            doc_status       TEXT    DEFAULT 'pending',
            created_at       TEXT    DEFAULT (datetime('now','localtime')),
            updated_at       TEXT    DEFAULT (datetime('now','localtime')),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    # Migration: add new columns to existing databases gracefully
    _safe_add_column(db, "complaints", "proof_file",   "TEXT DEFAULT NULL")
    _safe_add_column(db, "complaints", "doc_status",   "TEXT DEFAULT 'pending'")
    _safe_add_column(db, "complaints", "is_verified",  "INTEGER DEFAULT 0")
    _safe_add_column(db, "complaints", "application_file", "TEXT DEFAULT NULL")
    _safe_add_column(db, "complaints", "hod_sign_file", "TEXT DEFAULT NULL")

    # Notifications table
    db.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id      INTEGER NOT NULL,
            message      TEXT    NOT NULL,
            is_read      INTEGER DEFAULT 0,
            created_at   TEXT    DEFAULT (datetime('now','localtime')),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    # Document uploads table
    db.execute("""
        CREATE TABLE IF NOT EXISTS uploads (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id         INTEGER NOT NULL,
            complaint_id    INTEGER,
            title           TEXT    NOT NULL,
            description     TEXT    DEFAULT '',
            application_file TEXT,
            hod_sign_file   TEXT,
            created_at      TEXT    DEFAULT (datetime('now','localtime')),
            FOREIGN KEY (user_id)      REFERENCES users(id),
            FOREIGN KEY (complaint_id) REFERENCES complaints(id)
        )
    """)

    # Complaint History Timeline table
    db.execute("""
        CREATE TABLE IF NOT EXISTS complaint_history (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            complaint_id    INTEGER NOT NULL,
            action          TEXT    NOT NULL,
            action_by       INTEGER NOT NULL,
            details         TEXT,
            created_at      TEXT    DEFAULT (datetime('now','localtime')),
            FOREIGN KEY (complaint_id) REFERENCES complaints(id),
            FOREIGN KEY (action_by)    REFERENCES users(id)
        )
    """)

    # Chat Messaging table
    db.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            complaint_id    INTEGER NOT NULL,
            sender_id       INTEGER NOT NULL,
            message         TEXT    NOT NULL,
            created_at      TEXT    DEFAULT (datetime('now','localtime')),
            FOREIGN KEY (complaint_id) REFERENCES complaints(id),
            FOREIGN KEY (sender_id)    REFERENCES users(id)
        )
    """)

    # Seed default admin
    admin = db.execute(
        "SELECT id FROM users WHERE email='admin@srqrs.edu'"
    ).fetchone()
    if not admin:
        db.execute(
            "INSERT INTO users(name,email,prn,password,role) VALUES (?,?,?,?,?)",
            ("Administrator", "admin@srqrs.edu", "ADMIN001",
             generate_password_hash("Admin@123"), "admin")
        )

    db.commit()
    db.close()


def _safe_add_column(db, table, column, col_def):
    """Add a column if it doesn't exist (idempotent migration helper)."""
    existing = [row[1] for row in
                db.execute(f"PRAGMA table_info({table})").fetchall()]
    if column not in existing:
        db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_def}")


# ─────────────────────────────────────────────
#  DECORATORS
# ─────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            flash("Please login to continue.", "warning")
            return redirect(url_for("home"))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get("role") != "admin":
            flash("Admin access required.", "danger")
            return redirect(url_for("home"))
        return f(*args, **kwargs)
    return decorated


# ─────────────────────────────────────────────
#  HOME / AUTH
# ─────────────────────────────────────────────
@app.route("/")
def home():
    if "user_id" in session:
        return redirect(url_for("admin_dashboard") if session["role"] == "admin"
                        else url_for("student_dashboard"))
    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name     = request.form.get("name", "").strip()
        email    = request.form.get("email", "").strip().lower()
        prn      = request.form.get("prn", "").strip().upper()
        password = request.form.get("password", "")
        confirm  = request.form.get("confirm_password", "")

        if not all([name, email, prn, password]):
            flash("All fields are required.", "danger")
            return render_template("register.html")

        if password != confirm:
            flash("Passwords do not match.", "danger")
            return render_template("register.html")

        if len(password) < 6:
            flash("Password must be at least 6 characters.", "danger")
            return render_template("register.html")

        db = get_db()
        existing = db.execute(
            "SELECT id FROM users WHERE email=? OR prn=?", (email, prn)
        ).fetchone()
        if existing:
            flash("Email or PRN already registered.", "danger")
            db.close()
            return render_template("register.html")

        db.execute(
            "INSERT INTO users(name,email,prn,password,role) VALUES(?,?,?,?,?)",
            (name, email, prn, generate_password_hash(password), "student")
        )
        db.commit()
        db.close()
        flash("Registration successful! Please login.", "success")
        return redirect(url_for("home"))

    return render_template("register.html")


@app.route("/login", methods=["POST"])
def login():
    email    = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    db   = get_db()
    user = db.execute(
        "SELECT * FROM users WHERE email=?", (email,)
    ).fetchone()
    db.close()

    if user and check_password_hash(user["password"], password):
        session.clear()
        session["user_id"]   = user["id"]
        session["user_name"] = user["name"]
        session["role"]      = user["role"]
        session["email"]     = user["email"]

        if user["role"] == "admin":
            return redirect(url_for("admin_dashboard"))
        return redirect(url_for("student_dashboard"))

    flash("Invalid email or password.", "danger")
    return redirect(url_for("home"))


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("home"))


# ─────────────────────────────────────────────
#  STUDENT ROUTES
# ─────────────────────────────────────────────
@app.route("/dashboard")
@login_required
def student_dashboard():
    db = get_db()
    complaints = db.execute(
        "SELECT * FROM complaints WHERE user_id=? ORDER BY created_at DESC",
        (session["user_id"],)
    ).fetchall()

    # Stats
    total    = len(complaints)
    pending  = sum(1 for c in complaints if c["status"] == "Pending")
    progress = sum(1 for c in complaints if c["status"] == "In Progress")
    resolved = sum(1 for c in complaints if c["status"] == "Resolved")

    # Unread notifications
    notifs = db.execute(
        "SELECT * FROM notifications WHERE user_id=? AND is_read=0 ORDER BY created_at DESC",
        (session["user_id"],)
    ).fetchall()

    # Student's uploaded documents
    uploads = db.execute(
        "SELECT * FROM uploads WHERE user_id=? ORDER BY created_at DESC",
        (session["user_id"],)
    ).fetchall()

    # Complaints list for linking uploads
    complaint_list = db.execute(
        "SELECT id, subject FROM complaints WHERE user_id=? ORDER BY created_at DESC",
        (session["user_id"],)
    ).fetchall()

    db.close()

    return render_template(
        "student_dashboard.html",
        complaints=complaints,
        total=total, pending=pending,
        progress=progress, resolved=resolved,
        notifications=notifs,
        uploads=uploads,
        complaint_list=complaint_list
    )


@app.route("/add_complaint", methods=["POST"])
@login_required
def add_complaint():
    subject     = request.form.get("subject", "").strip()
    issue_type  = request.form.get("issue_type", "").strip()
    description = request.form.get("description", "").strip()
    priority    = request.form.get("priority", "Normal")

    if not all([subject, issue_type, description]):
        flash("All complaint fields are required.", "danger")
        return redirect(url_for("student_dashboard"))

    # Handle optional file uploads
    app_file   = request.files.get("application_file")
    hod_file   = request.files.get("hod_sign_file")
    proof_file = request.files.get("proof_file")        # NEW: result proof

    saved_app   = save_upload(app_file)
    saved_hod   = save_upload(hod_file)
    saved_proof = save_upload(proof_file)

    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        """INSERT INTO complaints(user_id, subject, issue_type, description,
           status, priority, reply, application_file, hod_sign_file,
           proof_file, doc_status)
           VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
        (session["user_id"], subject, issue_type, description,
         "Pending", priority, "", saved_app, saved_hod,
         saved_proof, "pending")
    )
    new_complaint_id = cursor.lastrowid

    # ➕ Added: Log the timeline creation
    cursor.execute(
        """INSERT INTO complaint_history(complaint_id, action, action_by, details)
           VALUES(?, ?, ?, ?)""",
        (new_complaint_id, "Created Complaint", session["user_id"], f"Priority: {priority}, Type: {issue_type}")
    )

    db.commit()
    db.close()
    flash("Complaint submitted successfully! Tracker started.", "success")
    return redirect(url_for("student_dashboard"))


@app.route("/mark_notifications_read", methods=["POST"])
@login_required
def mark_notifications_read():
    db = get_db()
    db.execute(
        "UPDATE notifications SET is_read=1 WHERE user_id=?",
        (session["user_id"],)
    )
    db.commit()
    db.close()
    return jsonify({"status": "ok"})


# ─────────────────────────────────────────────
#  DOCUMENT UPLOAD ROUTES
# ─────────────────────────────────────────────
def save_upload(file_obj):
    """Save a file to UPLOAD_FOLDER with a unique name; return stored filename."""
    if not file_obj or file_obj.filename == "":
        return None
    if not allowed_file(file_obj.filename):
        return None
    ext      = file_obj.filename.rsplit(".", 1)[1].lower()
    filename = f"{uuid.uuid4().hex}.{ext}"
    file_obj.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
    return filename


@app.route("/upload_document", methods=["POST"])
@login_required
def upload_document():
    title        = request.form.get("doc_title", "").strip()
    description  = request.form.get("doc_description", "").strip()
    complaint_id = request.form.get("linked_complaint", None) or None

    if not title:
        flash("Document title is required.", "danger")
        return redirect(url_for("student_dashboard"))

    app_file = request.files.get("application_file")
    hod_file = request.files.get("hod_sign_file")

    if not app_file or app_file.filename == "":
        flash("Application document is required.", "danger")
        return redirect(url_for("student_dashboard"))

    if not allowed_file(app_file.filename):
        flash("Only PDF, PNG, JPG files are allowed (max 5 MB).", "danger")
        return redirect(url_for("student_dashboard"))

    saved_app = save_upload(app_file)
    saved_hod = save_upload(hod_file)   # optional

    db = get_db()
    db.execute(
        """INSERT INTO uploads(user_id, complaint_id, title, description,
           application_file, hod_sign_file) VALUES(?,?,?,?,?,?)""",
        (session["user_id"], complaint_id, title, description,
         saved_app, saved_hod)
    )
    db.commit()
    db.close()
    flash("Document uploaded successfully! Admin can now review it.", "success")
    return redirect(url_for("student_dashboard"))


@app.route("/uploads/<filename>")
@login_required
def serve_upload(filename):
    """Serve an uploaded file. Students can only access their own; admins see all."""
    db = get_db()

    # Check uploads table first
    row = db.execute(
        "SELECT user_id FROM uploads WHERE application_file=? OR hod_sign_file=?",
        (filename, filename)
    ).fetchone()

    # If not found there, check complaints table (complaint-attached files)
    if row is None:
        row = db.execute(
            "SELECT user_id FROM complaints WHERE application_file=? OR hod_sign_file=? OR proof_file=?",
            (filename, filename, filename)
        ).fetchone()

    db.close()

    if row is None:
        abort(404)
    if session.get("role") != "admin" and row["user_id"] != session["user_id"]:
        abort(403)

    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


# ─────────────────────────────────────────────
#  ADMIN ROUTES
# ─────────────────────────────────────────────
@app.route("/admin")
@admin_required
def admin_dashboard():
    db = get_db()

    # All complaints with student name + email
    complaints = db.execute("""
        SELECT c.*, u.name AS student_name, u.email AS student_email, u.prn
          FROM complaints c
          JOIN users u ON c.user_id = u.id
         ORDER BY c.created_at DESC
    """).fetchall()

    # Analytics
    total    = len(complaints)
    pending  = sum(1 for c in complaints if c["status"] == "Pending")
    progress = sum(1 for c in complaints if c["status"] == "In Progress")
    resolved = sum(1 for c in complaints if c["status"] == "Resolved")

    # Student count
    students = db.execute(
        "SELECT COUNT(*) AS cnt FROM users WHERE role='student'"
    ).fetchone()["cnt"]

    # Issue-type breakdown for chart
    issue_stats = db.execute("""
        SELECT issue_type, COUNT(*) AS cnt
          FROM complaints
         GROUP BY issue_type
    """).fetchall()

    # All student document uploads with student info
    all_uploads = db.execute("""
        SELECT up.*, u.name AS student_name, u.email AS student_email, u.prn,
               c.subject AS linked_subject
          FROM uploads up
          JOIN users u ON up.user_id = u.id
          LEFT JOIN complaints c ON up.complaint_id = c.id
         ORDER BY up.created_at DESC
    """).fetchall()

    # Recent 5 complaints
    recent = complaints[:5]

    db.close()

    return render_template(
        "admin_dashboard.html",
        complaints=complaints,
        total=total, pending=pending,
        progress=progress, resolved=resolved,
        students=students, recent=recent,
        issue_stats=issue_stats,
        all_uploads=all_uploads
    )


@app.route("/admin/update/<int:complaint_id>", methods=["POST"])
@admin_required
def update_complaint(complaint_id):
    status = request.form.get("status", "Pending")
    reply  = request.form.get("reply", "").strip()

    db = get_db()
    # Get complaint owner
    complaint = db.execute(
        "SELECT user_id, subject FROM complaints WHERE id=?", (complaint_id,)
    ).fetchone()

    if complaint:
        db.execute(
            """UPDATE complaints
                  SET status=?, reply=?, updated_at=datetime('now','localtime')
                WHERE id=?""",
            (status, reply, complaint_id)
        )

        # Notify student
        if reply:
            msg = (f"Your complaint '{complaint['subject']}' has been updated "
                   f"to '{status}'. Admin reply: {reply}")
        else:
            msg = (f"Your complaint '{complaint['subject']}' "
                   f"status changed to '{status}'.")

        db.execute(
            "INSERT INTO notifications(user_id, message) VALUES(?,?)",
            (complaint["user_id"], msg)
        )
        # ➕ Added: Timeline History
        db.execute(
            """INSERT INTO complaint_history(complaint_id, action, action_by, details)
               VALUES(?, ?, ?, ?)""",
            (complaint_id, "Status/Reply Updated", session["user_id"],
             f"Status: {status}. Reply: {reply[:30]}...")
        )

        db.commit()

    db.close()
    flash(f"Complaint #{complaint_id} updated successfully.", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/delete/<int:complaint_id>", methods=["POST"])
@admin_required
def delete_complaint(complaint_id):
    db = get_db()
    db.execute("DELETE FROM complaints WHERE id=?", (complaint_id,))
    db.commit()
    db.close()
    flash("Complaint deleted.", "success")
    return redirect(url_for("admin_dashboard"))


# ─────────────────────────────────────────────
#  PDF GENERATION
# ─────────────────────────────────────────────
def _draw_watermark(c, text, color_rgb):
    """Draw diagonal watermark text on a ReportLab canvas page."""
    c.saveState()
    c.setFont("Helvetica-Bold", 72)
    c.setFillColorRGB(*color_rgb, alpha=0.07)
    c.translate(A4[0] / 2, A4[1] / 2)
    c.rotate(45)
    c.drawCentredString(0, 0, text)
    c.restoreState()


class WatermarkCanvas(pdfcanvas.Canvas):
    """Custom canvas that draws a status watermark on every page."""
    def __init__(self, *args, watermark="", wm_color=(0,0,0), **kwargs):
        super().__init__(*args, **kwargs)
        self._watermark  = watermark
        self._wm_color   = wm_color

    def showPage(self):
        if self._watermark:
            _draw_watermark(self, self._watermark, self._wm_color)
        super().showPage()

    def save(self):
        if self._watermark:
            _draw_watermark(self, self._watermark, self._wm_color)
        super().save()


def generate_complaint_pdf(complaint, student):
    """Build and return a PDF BytesIO for the given complaint."""
    buf = io.BytesIO()

    # Watermark based on status
    status = complaint["status"]
    if status == "Resolved":
        wm_text, wm_color = "APPROVED",  (0.04, 0.74, 0.51)   # green
    elif status == "In Progress":
        wm_text, wm_color = "IN PROGRESS", (0.23, 0.51, 0.96) # blue
    else:
        wm_text, wm_color = "PENDING",   (0.96, 0.62, 0.04)   # amber

    def canvas_maker(*args, **kwargs):
        return WatermarkCanvas(*args, watermark=wm_text,
                               wm_color=wm_color, **kwargs)

    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        rightMargin=2*cm, leftMargin=2*cm,
        topMargin=2.5*cm, bottomMargin=2.5*cm
    )

    styles = getSampleStyleSheet()
    s_title  = ParagraphStyle('title',  fontSize=18, leading=22,
                              alignment=TA_CENTER, fontName='Helvetica-Bold',
                              textColor=colors.HexColor('#1e1b4b'), spaceAfter=6)
    s_sub    = ParagraphStyle('sub',    fontSize=10, alignment=TA_CENTER,
                              textColor=colors.HexColor('#4f46e5'), spaceAfter=4)
    s_label  = ParagraphStyle('label',  fontSize=8.5, fontName='Helvetica-Bold',
                              textColor=colors.HexColor('#374151'))
    s_value  = ParagraphStyle('value',  fontSize=9.5,
                              textColor=colors.HexColor('#111827'))
    s_sign   = ParagraphStyle('sign',   fontSize=9, alignment=TA_CENTER,
                              textColor=colors.HexColor('#6b7280'))
    s_h2     = ParagraphStyle('h2',     fontSize=11, fontName='Helvetica-Bold',
                              textColor=colors.HexColor('#1e1b4b'), spaceBefore=10, spaceAfter=4)

    # Status badge colors
    badge_bg = {
        'Pending':     colors.HexColor('#fef3c7'),
        'In Progress': colors.HexColor('#dbeafe'),
        'Resolved':    colors.HexColor('#d1fae5'),
    }
    badge_fg = {
        'Pending':     colors.HexColor('#92400e'),
        'In Progress': colors.HexColor('#1e40af'),
        'Resolved':    colors.HexColor('#065f46'),
    }

    verified_text = "✓ VERIFIED BY ADMIN" if complaint["is_verified"] else ""

    story = []

    # ── Header ──────────────────────────────────────────────
    csmss_style = ParagraphStyle('csmss', fontSize=26, leading=30, fontName='Helvetica-Bold', alignment=TA_CENTER, textColor=colors.HexColor('#1e1b4b'), spaceAfter=8)
    story.append(Paragraph("CSMSS", csmss_style))
    story.append(Paragraph("Student Result Query Resolution System", s_title))
    story.append(Paragraph("Official Complaint Document", s_sub))
    if verified_text:
        story.append(Paragraph(
            f'<font color="#065f46"><b>{verified_text}</b></font>', s_sub))
    story.append(HRFlowable(width="100%", thickness=2,
                             color=colors.HexColor('#4f46e5'), spaceAfter=12))

    # ── Meta info row ────────────────────────────────────────
    meta_data = [
        [Paragraph('<b>Complaint ID</b>', s_label),
         Paragraph(f'CSMSS-{complaint["id"]:04d}', s_value),
         Paragraph('<b>Date Submitted</b>', s_label),
         Paragraph(complaint['created_at'][:10], s_value)],
        [Paragraph('<b>Priority</b>', s_label),
         Paragraph(complaint['priority'], s_value),
         Paragraph('<b>Status</b>', s_label),
         Paragraph(
             f'<font color="#{badge_fg.get(status, colors.black).hexval()[2:]}"><b>{status}</b></font>',
             s_value)],
    ]
    meta_tbl = Table(meta_data, colWidths=[3.5*cm, 5.5*cm, 3.5*cm, 5.5*cm])
    meta_tbl.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f8fafc')),
        ('BOX',        (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
        ('INNERGRID',  (0,0), (-1,-1), 0.3, colors.HexColor('#e2e8f0')),
        ('TOPPADDING',    (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING',   (0,0), (-1,-1), 6),
    ]))
    story.append(meta_tbl)
    story.append(Spacer(1, 14))

    # ── Student Details ──────────────────────────────────────
    story.append(Paragraph("Student Information", s_h2))
    stu_data = [
        [Paragraph('<b>Full Name</b>', s_label),
         Paragraph(student['name'], s_value),
         Paragraph('<b>PRN</b>', s_label),
         Paragraph(student['prn'] or '—', s_value)],
        [Paragraph('<b>Email</b>', s_label),
         Paragraph(student['email'], s_value),
         Paragraph('<b>Role</b>', s_label),
         Paragraph('Student', s_value)],
    ]
    stu_tbl = Table(stu_data, colWidths=[3.5*cm, 5.5*cm, 3.5*cm, 5.5*cm])
    stu_tbl.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f0fdf4')),
        ('BOX',        (0,0), (-1,-1), 0.5, colors.HexColor('#bbf7d0')),
        ('INNERGRID',  (0,0), (-1,-1), 0.3, colors.HexColor('#d1fae5')),
        ('TOPPADDING',    (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING',   (0,0), (-1,-1), 6),
    ]))
    story.append(stu_tbl)
    story.append(Spacer(1, 14))

    # ── Complaint Details ────────────────────────────────────
    story.append(Paragraph("Complaint Details", s_h2))
    cmp_data = [
        [Paragraph('<b>Subject / Course</b>', s_label),
         Paragraph(complaint['subject'], s_value),
         Paragraph('<b>Issue Type</b>', s_label),
         Paragraph(complaint['issue_type'], s_value)],
    ]
    cmp_tbl = Table(cmp_data, colWidths=[3.5*cm, 5.5*cm, 3.5*cm, 5.5*cm])
    cmp_tbl.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#eff6ff')),
        ('BOX',        (0,0), (-1,-1), 0.5, colors.HexColor('#bfdbfe')),
        ('INNERGRID',  (0,0), (-1,-1), 0.3, colors.HexColor('#dbeafe')),
        ('TOPPADDING',    (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING',   (0,0), (-1,-1), 6),
    ]))
    story.append(cmp_tbl)
    story.append(Spacer(1, 6))

    # Description box
    desc_data = [[Paragraph('<b>Description of Issue</b>', s_label)],
                 [Paragraph(complaint['description'], s_value)]]
    desc_tbl = Table(desc_data, colWidths=[18*cm])
    desc_tbl.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#f1f5f9')),
        ('BACKGROUND', (0,1), (-1,-1), colors.white),
        ('BOX',        (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('TOPPADDING',    (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('LEFTPADDING',   (0,0), (-1,-1), 8),
    ]))
    story.append(desc_tbl)
    story.append(Spacer(1, 12))

    # Admin reply (if any)
    if complaint['reply']:
        story.append(Paragraph("Admin Reply / Resolution", s_h2))
        reply_data = [[Paragraph(complaint['reply'], s_value)]]
        reply_tbl = Table(reply_data, colWidths=[18*cm])
        reply_tbl.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f0fdf4')),
            ('BOX',        (0,0), (-1,-1), 0.5, colors.HexColor('#86efac')),
            ('LEFTPADDING',   (0,0), (-1,-1), 8),
            ('TOPPADDING',    (0,0), (-1,-1), 6),
            ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ]))
        story.append(reply_tbl)
        story.append(Spacer(1, 12))

    # ── Signature Section ────────────────────────────────────
    story.append(Spacer(1, 20))
    story.append(HRFlowable(width="100%", thickness=0.5,
                             color=colors.HexColor('#94a3b8'), spaceAfter=8))
    story.append(Paragraph("Signatures & Authorization", s_h2))

    sig_data = [[
        Paragraph("Student Signature", s_sign),
        Paragraph("HOD Signature", s_sign),
        Paragraph("Admin / Exam Cell", s_sign),
    ],[
        Paragraph("<br/><br/><br/>__________________________", s_sign),
        Paragraph("<br/><br/><br/>__________________________", s_sign),
        Paragraph("<br/><br/><br/>__________________________", s_sign),
    ],[
        Paragraph(f"{student['name']}", s_sign),
        Paragraph("Head of Department", s_sign),
        Paragraph("Exam Cell / Administrator", s_sign),
    ],[
        Paragraph(f"Date: ___________", s_sign),
        Paragraph(f"Date: ___________", s_sign),
        Paragraph(f"Date: ___________", s_sign),
    ]]
    sig_tbl = Table(sig_data, colWidths=[6*cm, 6*cm, 6*cm])
    sig_tbl.setStyle(TableStyle([
        ('ALIGN',   (0,0), (-1,-1), 'CENTER'),
        ('VALIGN',  (0,0), (-1,-1), 'MIDDLE'),
        ('BOX',     (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
        ('INNERGRID',(0,0),(-1,-1), 0.3, colors.HexColor('#f1f5f9')),
        ('TOPPADDING',    (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#f8fafc')),
    ]))
    story.append(sig_tbl)
    story.append(Spacer(1, 10))

    # Footer
    story.append(HRFlowable(width="100%", thickness=0.5,
                             color=colors.HexColor('#94a3b8'), spaceAfter=4))
    story.append(Paragraph(
        f"Generated by CSMSS • {datetime.now().strftime('%d %b %Y %H:%M')} • "
        f"Complaint ID: CSMSS-{complaint['id']:04d}",
        ParagraphStyle('footer', fontSize=7.5, alignment=TA_CENTER,
                       textColor=colors.HexColor('#94a3b8'))
    ))

    doc.build(story, canvasmaker=canvas_maker)
    buf.seek(0)
    return buf


@app.route("/download_pdf/<int:complaint_id>")
@login_required
def download_pdf(complaint_id):
    """Generate and serve the complaint PDF."""
    db = get_db()
    complaint = db.execute(
        "SELECT * FROM complaints WHERE id=?", (complaint_id,)
    ).fetchone()

    if complaint is None:
        db.close()
        flash("Complaint not found.", "danger")
        return redirect(url_for("student_dashboard"))

    # Access control: student can only download their own
    if (session["role"] != "admin" and
            complaint["user_id"] != session["user_id"]):
        db.close()
        abort(403)

    student = db.execute(
        "SELECT * FROM users WHERE id=?", (complaint["user_id"],)
    ).fetchone()
    db.close()

    pdf_buf = generate_complaint_pdf(complaint, student)

    return send_file(
        pdf_buf,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"CSMSS-{complaint_id:04d}.pdf"
    )


# ─────────────────────────────────────────────
#  ADMIN – MARK AS VERIFIED
# ─────────────────────────────────────────────
@app.route("/admin/verify/<int:complaint_id>", methods=["POST"])
@admin_required
def verify_complaint(complaint_id):
    db = get_db()
    row = db.execute(
        "SELECT is_verified, user_id, subject FROM complaints WHERE id=?",
        (complaint_id,)
    ).fetchone()
    if row:
        new_val = 0 if row["is_verified"] else 1
        db.execute(
            "UPDATE complaints SET is_verified=? WHERE id=?",
            (new_val, complaint_id)
        )
        action = "verified" if new_val else "unverified"
        db.execute(
            "INSERT INTO notifications(user_id, message) VALUES(?,?)",
            (row["user_id"],
             f"Your complaint '{row['subject']}' has been {action} by Admin.")
        )
        db.commit()
        flash(f"Complaint #{complaint_id} marked as {action}.", "success")
    db.close()
    return redirect(url_for("admin_dashboard"))


# ─────────────────────────────────────────────
#  PDF MERGING  (Application + Proof)
# ─────────────────────────────────────────────

def _proof_to_pdf_bytes(proof_path):
    """Return a BytesIO PDF for the proof file (PDF passthrough or image page)."""
    ext = proof_path.rsplit(".", 1)[-1].lower()
    if ext == "pdf":
        with open(proof_path, "rb") as f:
            return io.BytesIO(f.read())
    # Image → single A4 PDF page via reportlab
    buf = io.BytesIO()
    img = PILImage.open(proof_path).convert("RGB")
    w, h = img.size
    MAX_W, MAX_H = 540, 780          # pts with margin inside A4
    ratio = min(MAX_W / w, MAX_H / h)
    nw, nh = int(w * ratio), int(h * ratio)
    img = img.resize((nw, nh), PILImage.LANCZOS)

    tmp = io.BytesIO()
    img.save(tmp, format="JPEG")
    tmp.seek(0)

    from reportlab.lib.utils import ImageReader
    c = pdfcanvas.Canvas(buf, pagesize=A4)
    x = (A4[0] - nw) / 2
    y = (A4[1] - nh) / 2
    c.drawImage(ImageReader(tmp), x, y, width=nw, height=nh)
    c.showPage()
    c.save()
    buf.seek(0)
    return buf


def generate_merged_pdf(complaint, student):
    """
    Merge:
      Pages 1+  → Application form PDF (reportlab)
      Pages N+  → Uploaded proof document (result marksheet)
    Returns (BytesIO, filename_str)
    """
    writer = PdfWriter()

    # 1. Application form PDF
    app_buf = generate_complaint_pdf(complaint, student)
    for pg in PdfReader(app_buf).pages:
        writer.add_page(pg)

    # 2. Proof document (if uploaded)
    if complaint["proof_file"]:
        proof_path = os.path.join(app.config["UPLOAD_FOLDER"],
                                  complaint["proof_file"])
        if os.path.exists(proof_path):
            for pg in PdfReader(_proof_to_pdf_bytes(proof_path)).pages:
                writer.add_page(pg)

    out_buf = io.BytesIO()
    writer.write(out_buf)
    out_buf.seek(0)

    safe_name = student["name"].replace(" ", "")
    filename  = f"CSMSS_{complaint['id']:04d}_{safe_name}_Final.pdf"
    return out_buf, filename


@app.route("/download_merged/<int:complaint_id>")
@login_required
def download_merged(complaint_id):
    """Download merged PDF: application form + proof document."""
    db        = get_db()
    complaint = db.execute("SELECT * FROM complaints WHERE id=?",
                           (complaint_id,)).fetchone()

    if complaint is None:
        db.close()
        flash("Complaint not found.", "danger")
        return redirect(url_for("student_dashboard"))

    if (session["role"] != "admin" and
            complaint["user_id"] != session["user_id"]):
        db.close()
        abort(403)

    student = db.execute("SELECT * FROM users WHERE id=?",
                         (complaint["user_id"],)).fetchone()
    db.close()

    pdf_buf, filename = generate_merged_pdf(complaint, student)
    return send_file(
        pdf_buf,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=filename
    )


# ─────────────────────────────────────────────
#  ADMIN – DOCUMENT STATUS (Verified/Rejected/Pending)
# ─────────────────────────────────────────────
@app.route("/admin/doc_status/<int:complaint_id>", methods=["POST"])
@admin_required
def set_doc_status(complaint_id):
    """Admin sets document status: verified | rejected | pending."""
    new_status = request.form.get("doc_status", "pending").strip()
    if new_status not in ("verified", "rejected", "pending"):
        flash("Invalid document status.", "danger")
        return redirect(url_for("admin_dashboard"))

    db  = get_db()
    row = db.execute(
        "SELECT user_id, subject FROM complaints WHERE id=?", (complaint_id,)
    ).fetchone()

    if row:
        db.execute(
            "UPDATE complaints SET doc_status=?, is_verified=? WHERE id=?",
            (new_status, 1 if new_status == "verified" else 0, complaint_id)
        )
        label = {"verified": "✓ Verified", "rejected": "✗ Rejected",
                 "pending": "⏳ Pending Review"}[new_status]
        db.execute(
            "INSERT INTO notifications(user_id, message) VALUES(?,?)",
            (row["user_id"],
             f"Your document for '{row['subject']}' is now: {label}")
        )
        # ➕ Added: Timeline History
        db.execute(
            """INSERT INTO complaint_history(complaint_id, action, action_by, details)
               VALUES(?, ?, ?, ?)""",
            (complaint_id, "Document Verification", session["user_id"],
             f"Admin updated verification status to '{new_status}'.")
        )

        db.commit()
        flash(f"Document marked as '{new_status}' for #{complaint_id}.", "success")
    db.close()
    return redirect(url_for("admin_dashboard"))


# ─────────────────────────────────────────────
#  API ENDPOINTS (JSON)
# ─────────────────────────────────────────────
@app.route("/api/stats")
@admin_required
def api_stats():
    db = get_db()
    rows = db.execute("""
        SELECT status, COUNT(*) AS cnt FROM complaints GROUP BY status
    """).fetchall()
    db.close()
    return jsonify({r["status"]: r["cnt"] for r in rows})


@app.route("/api/complaints/search")
@admin_required
def api_search():
    q = request.args.get("q", "").strip()
    db = get_db()
    complaints = db.execute("""
        SELECT c.*, u.name AS student_name, u.prn
          FROM complaints c JOIN users u ON c.user_id=u.id
         WHERE u.name LIKE ? OR u.prn LIKE ? OR c.subject LIKE ?
           OR c.issue_type LIKE ? OR c.status LIKE ?
         ORDER BY c.created_at DESC
    """, (f"%{q}%",)*5).fetchall()
    db.close()
    return jsonify([dict(r) for r in complaints])


# ➕ Added: Timeline Tracking API
@app.route("/api/timeline/<int:complaint_id>")
@login_required
def api_timeline(complaint_id):
    db = get_db()
    # Quick auth check
    if session["role"] != "admin":
        c = db.execute("SELECT user_id FROM complaints WHERE id=?", (complaint_id,)).fetchone()
        if not c or c["user_id"] != session["user_id"]:
            db.close(); abort(403)

    history = db.execute("""
        SELECT h.action, h.details, h.created_at, u.name as action_by_name, u.role
          FROM complaint_history h
          JOIN users u ON h.action_by = u.id
         WHERE h.complaint_id=?
         ORDER BY h.created_at ASC
    """, (complaint_id,)).fetchall()
    db.close()
    return jsonify([dict(r) for r in history])


# ➕ Added: Chat Messaging API
@app.route("/api/chat/<int:complaint_id>", methods=["GET", "POST"])
@login_required
def api_chat(complaint_id):
    db = get_db()
    
    # Auth check
    c = db.execute("SELECT user_id, subject FROM complaints WHERE id=?", (complaint_id,)).fetchone()
    if not c or (session["role"] != "admin" and c["user_id"] != session["user_id"]):
        db.close(); abort(403)

    if request.method == "POST":
        data = request.get_json() or {}
        msg = data.get("message", "").strip()
        if msg:
            db.execute("INSERT INTO messages(complaint_id, sender_id, message) VALUES(?,?,?)",
                       (complaint_id, session["user_id"], msg))
            db.commit()
            db.close()
            return jsonify({"status": "ok"})
        db.close()
        return jsonify({"error": "Empty message"}), 400

    messages = db.execute("""
        SELECT m.message, m.created_at, u.name as sender_name, u.role as sender_role
          FROM messages m
          JOIN users u ON m.sender_id = u.id
         WHERE m.complaint_id=?
         ORDER BY m.created_at ASC
    """, (complaint_id,)).fetchall()
    db.close()
    return jsonify([dict(r) for r in messages])


# ─────────────────────────────────────────────
#  ENTRY POINT  — init_db runs at module level
#  so it works with both `python app.py` AND
#  Flask's auto-reloader / gunicorn workers.
# ─────────────────────────────────────────────
with app.app_context():
    init_db()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)