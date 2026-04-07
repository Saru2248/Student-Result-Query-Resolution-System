# 🎓 Student Result Query Resolution System (SRQRS)

> **Industry-Level, Full-Stack Cloud-Ready Web Application**  
> Built for college administration — digitizing the result complaint process end-to-end.

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-2.3-000?logo=flask)](https://flask.palletsprojects.com)
[![SQLite](https://img.shields.io/badge/Database-SQLite3-003B57?logo=sqlite)](https://sqlite.org)
[![reportlab](https://img.shields.io/badge/PDF-ReportLab-FF4136)](https://reportlab.com)
[![Bootstrap](https://img.shields.io/badge/UI-Bootstrap_5-7952B3?logo=bootstrap)](https://getbootstrap.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-green)](LICENSE)

---

## 📋 Table of Contents
1. [Overview](#-overview)
2. [Real-World Problem Solved](#-real-world-problem-solved)
3. [Tech Stack](#-tech-stack)
4. [Core Features](#-core-features)
5. [Database Design](#-database-design)
6. [System Architecture](#-system-architecture)
7. [Project Structure](#-project-structure)
8. [Security Features](#-security-features)
9. [PDF Document Generation](#-pdf-document-generation)
10. [Running Locally](#-running-locally)
11. [Deployment Guide](#-deployment-guide)
12. [Testing](#-testing)
13. [API Reference](#-api-reference)
14. [Future Scope](#-future-scope)

---

## 🔎 Overview

The **Student Result Query Resolution System (SRQRS)** is a production-grade, full-stack web application designed to digitize and streamline the process of raising, tracking, and resolving student academic result complaints in colleges and universities.

Students can submit complaints about result discrepancies (wrong marks, grade errors, missing marks), attach supporting documents (application form, HOD-signed letter), and download an official PDF — all without physically visiting the exam cell.

Administrators get a real-time dashboard with analytics, complaint management, verification tracking, and the ability to reply and export official PDFs for every complaint.

---

## 🌍 Real-World Problem Solved

| Manual Process (Old)                         | SRQRS (New)                                    |
|----------------------------------------------|------------------------------------------------|
| Students physically visit exam cell           | Online complaint submission anytime            |
| Paper applications lost or delayed            | Documents uploaded and stored securely         |
| No tracking — students left in the dark       | Real-time status: Pending → In Progress → Resolved |
| HOD signatures handled informally             | HOD-signed documents uploaded digitally        |
| No audit trail                                | All actions logged with timestamps             |
| Manual PDF/print requests                     | Instant professional PDF with watermark        |
| No data analytics                             | Admin dashboard with charts and statistics     |

---

## 🛠 Tech Stack

```
Frontend:  HTML5, CSS3 (Custom Glassmorphism), Bootstrap 5.3, Vanilla JS
Backend:   Python 3.10+, Flask 2.3
Database:  SQLite3 (upgrade-ready to PostgreSQL/MySQL)
PDF:       ReportLab 4.x (with watermarks + signatures)
Auth:      Werkzeug password hashing + Flask sessions
Charts:    Chart.js 4.x
Icons:     Font Awesome 6.5
Testing:   pytest 9.x
Uploads:   Werkzeug secure_filename + UUID-based storage
```

---

## ✨ Core Features

### 👨‍🎓 Student Module
- ✅ Secure Registration & Login (hashed passwords)
- ✅ Submit result complaint (Subject, Issue Type, Priority, Description)
- ✅ Attach **Application Document** + **HOD-Signed Document** in the same form
- ✅ View complaint history with status badges
- ✅ Track status: **Pending → In Progress → Resolved**
- ✅ View admin replies inline
- ✅ See "Admin Verified" badge when complaint is verified
- ✅ **Download official PDF** of any complaint (with watermark)
- ✅ Real-time notifications for admin updates

### 🛠 Admin Module
- ✅ Dedicated admin login (separate from students)
- ✅ Analytics dashboard (Donut chart + Bar chart via Chart.js)
- ✅ All complaints table with live search & filter
- ✅ Filter by status (Pending / In Progress / Resolved)
- ✅ Update complaint status + write reply
- ✅ **Mark as Verified** (toggle — notifies student)
- ✅ **View attached documents** (Application + HOD Signed)
- ✅ **Download PDF** for any complaint
- ✅ Delete complaints
- ✅ REST API endpoints for stats and search

### 📄 PDF Document
- ✅ Complaint ID (e.g. `SRQRS-0001`)
- ✅ Student details, complaint metadata
- ✅ Status-based diagonal **watermark**: PENDING / IN PROGRESS / APPROVED
- ✅ Admin reply section (if provided)
- ✅ 3-column **signature section**: Student | HOD | Admin/Exam Cell
- ✅ Generated on-the-fly — no storage needed

---

## 🗄 Database Design

### Users Table
```sql
CREATE TABLE users (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    name      TEXT    NOT NULL,
    email     TEXT    NOT NULL UNIQUE,
    prn       TEXT    UNIQUE,
    password  TEXT    NOT NULL,
    role      TEXT    NOT NULL DEFAULT 'student',  -- 'student' | 'admin'
    created_at TEXT   DEFAULT (datetime('now','localtime'))
);
```

### Complaints Table
```sql
CREATE TABLE complaints (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id          INTEGER NOT NULL,
    subject          TEXT    NOT NULL,
    issue_type       TEXT    NOT NULL,
    description      TEXT    NOT NULL,
    status           TEXT    DEFAULT 'Pending',
    priority         TEXT    DEFAULT 'Normal',
    reply            TEXT    DEFAULT '',
    application_file TEXT    DEFAULT NULL,   -- UUID filename in /uploads/
    hod_sign_file    TEXT    DEFAULT NULL,   -- UUID filename in /uploads/
    is_verified      INTEGER DEFAULT 0,
    created_at       TEXT    DEFAULT (datetime('now','localtime')),
    updated_at       TEXT    DEFAULT (datetime('now','localtime')),
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

### Notifications Table
```sql
CREATE TABLE notifications (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL,
    message    TEXT    NOT NULL,
    is_read    INTEGER DEFAULT 0,
    created_at TEXT    DEFAULT (datetime('now','localtime')),
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

### Uploads Table (Standalone uploads)
```sql
CREATE TABLE uploads (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id          INTEGER NOT NULL,
    complaint_id     INTEGER DEFAULT NULL,
    title            TEXT    NOT NULL,
    description      TEXT,
    application_file TEXT,
    hod_sign_file    TEXT,
    created_at       TEXT    DEFAULT (datetime('now','localtime')),
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

---

## 🏗 System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         SRQRS Architecture                          │
│                                                                     │
│  Student/Admin Browser                                              │
│       │  HTML + Bootstrap + JS (Chart.js)                          │
│       │                                                             │
│       ▼                                                             │
│  ┌─────────────────────────────────────────┐                        │
│  │            Flask Application             │                        │
│  │  ┌──────────┐  ┌────────────────────┐   │                        │
│  │  │  Routes  │  │    Middleware       │   │                        │
│  │  │ /login   │  │  @login_required   │   │                        │
│  │  │ /register│  │  @admin_required   │   │                        │
│  │  │ /dashboard│ │  Session Manager   │   │                        │
│  │  │ /admin   │  └────────────────────┘   │                        │
│  │  │ /download│                           │                        │
│  │  │ /uploads │  ┌────────────────────┐   │                        │
│  │  └──────────┘  │  PDF Generator     │   │                        │
│  │                │  (ReportLab)       │   │                        │
│  │                │  + Watermark Canvas│   │                        │
│  │                └────────────────────┘   │                        │
│  └──────────────────────┬──────────────────┘                        │
│                         │                                           │
│                         ▼                                           │
│  ┌─────────────────────────────────────────┐                        │
│  │           SQLite3 Database               │                        │
│  │  users │ complaints │ notifications      │                        │
│  │  uploads                                 │                        │
│  └─────────────────────────────────────────┘                        │
│                         │                                           │
│                         ▼                                           │
│                   static/uploads/                                   │
│            (UUID-named document files)                              │
└─────────────────────────────────────────────────────────────────────┘
```

**Data Flow:**
1. Student registers → hashed password stored → session created
2. Student submits complaint → optionally attaches files → form POST with `multipart/form-data`
3. Files saved as `UUID.ext` in `static/uploads/` → filename stored in DB
4. Admin views complaint table → sees Documents column with clickable links
5. Admin verifies/replies → notification inserted → student sees badge
6. Either party clicks "Download PDF" → Flask generates PDF in-memory → browser downloads

---

## 📁 Project Structure

```
6 th sem mini project/
├── project/
│   ├── app.py              # Flask app, all routes, PDF generation
│   ├── requirements.txt    # Python dependencies
│   ├── test_app.py         # Pytest unit tests (30 test cases)
│   └── database.db         # Auto-created SQLite database
├── templates/
│   ├── login.html          # Login + Register page
│   ├── register.html       # Registration form
│   ├── student_dashboard.html  # Student portal
│   └── admin_dashboard.html    # Admin control panel
├── static/
│   ├── css/
│   │   └── style.css       # Custom glassmorphism design system
│   ├── js/
│   │   └── script.js       # Charts, modals, search, animations
│   └── uploads/            # Student-uploaded documents (auto-created)
└── README.md
```

---

## 🔒 Security Features

| Feature | Implementation |
|---------|----------------|
| Password Hashing | `werkzeug.security.generate_password_hash` (PBKDF2-SHA256) |
| Session Auth | Flask server-side sessions with secret key |
| Route Protection | `@login_required`, `@admin_required` decorators |
| File Validation | Extension whitelist (pdf, png, jpg), max 5 MB |
| File Storage | UUID-renamed files → prevent directory traversal |
| File Serving | Ownership check before serving each file |
| SQL Injection | Parameterized queries (no string formatting in SQL) |
| XSS Protection | Jinja2 auto-escaping in templates |
| IDOR Prevention | User ID verified against session on every resource request |

---

## 📄 PDF Document Generation

The PDF is built entirely in-memory using **ReportLab** — no disk storage needed.

### PDF Structure:
```
┌────────────────────────────────────────────────────────┐
│     Student Result Query Resolution System              │
│              Official Complaint Document                │
│                  ✓ VERIFIED BY ADMIN   (if verified)   │
│ ══════════════════════════════════════════════════      │
│  Complaint ID: SRQRS-0001  │  Date: 2026-04-07         │
│  Priority: High            │  Status: ██ PENDING        │
│ ────────────────────────────────────────────────────── │
│  Student Information                                    │
│  Name: Alice Kumar   │  PRN: ALICE001                  │
│  Email: alice@edu    │  Role: Student                  │
│ ────────────────────────────────────────────────────── │
│  Complaint Details                                      │
│  Subject: Math III   │  Issue: Marks Not Updated        │
│  Description: ... (full text)                          │
│ ────────────────────────────────────────────────────── │
│  Admin Reply (if any): "Issue resolved ..."            │
│ ════════════════════════════════════════════════════   │
│  Student Sig     │  HOD Signature   │  Admin/Exam Cell  │
│  ____________    │  ____________    │  ____________     │
│  Alice Kumar     │  Head of Dept    │  Exam Cell        │
│  Date: _____     │  Date: _____     │  Date: _____      │
└────────────────────────────────────────────────────────┘
        [PENDING watermark diagonal in background]
```

### Watermark Colors:
- `Pending` → **Amber** diagonal text: "PENDING"
- `In Progress` → **Blue** diagonal text: "IN PROGRESS"
- `Resolved` → **Green** diagonal text: "APPROVED"

---

## 🚀 Running Locally

### Prerequisites
- Python 3.10+
- pip

### Steps

```bash
# 1. Clone the repository
git clone https://github.com/your-username/srqrs.git
cd srqrs

# 2. Create and activate virtual environment
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

# 3. Install dependencies
pip install -r project/requirements.txt

# 4. Run the application
cd project
python app.py
```

Visit: **http://localhost:5000**

### Default Admin Credentials
| Field | Value |
|-------|-------|
| Email | `admin@srqrs.edu` |
| Password | `Admin@123` |

---

## ☁️ Deployment Guide

### Option 1: Render (Free)

1. Push project to GitHub
2. Go to [render.com](https://render.com) → New → Web Service
3. Connect your GitHub repo
4. Settings:
   - **Build Command:** `pip install -r project/requirements.txt`
   - **Start Command:** `cd project && gunicorn app:app`
   - **Environment:** Python 3

```bash
pip install gunicorn
```

Add to `requirements.txt`:
```
gunicorn==21.2.0
```

### Option 2: Railway

```bash
# Install Railway CLI
npm install -g @railway/cli
railway login
railway init
railway up
```

### Production Config (app.py)
```python
import os
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "fallback-key")
app.config["DEBUG"] = False
```

### Switch to PostgreSQL (Production)
```bash
pip install psycopg2-binary flask-sqlalchemy
```
Update `DATABASE_URI` env variable and replace `sqlite3` calls with SQLAlchemy ORM.

---

## 🧪 Testing

Run the full test suite (30 test cases):

```bash
# Activate venv first
python -m pytest test_app.py -v
```

### Test Categories

| Category | Tests | Coverage |
|----------|-------|----------|
| Authentication | 10 | Register, Login, Logout, Access Control |
| Complaints | 5 | Submit, Validate, History, Admin visibility |
| Admin Operations | 5 | Update, Verify, Delete, RBAC |
| PDF Generation | 4 | Content-type, Magic bytes, Access control, 404 |
| API Endpoints | 3 | Stats, Search, Unauthorized access |
| Input Validation | 3 | Short password, Mismatch, Required fields |

**Expected Result:** ✅ 30 passed

---

## 🔌 API Reference

### `GET /api/stats` *(Admin only)*
Returns complaint count by status.
```json
{ "Pending": 5, "In Progress": 2, "Resolved": 8 }
```

### `GET /api/complaints/search?q=<query>` *(Admin only)*
Search complaints by student name, PRN, subject, or status.
```json
[
  {
    "id": 1,
    "student_name": "Alice Kumar",
    "prn": "ALICE001",
    "subject": "Mathematics III",
    "status": "Pending",
    ...
  }
]
```

### `GET /download_pdf/<id>` *(Authenticated)*
Downloads complaint PDF. Students: own complaints only. Admin: all.

### `POST /admin/verify/<id>` *(Admin only)*
Toggle verified status of a complaint.

---

## 🔮 Future Scope

| Feature | Description |
|---------|-------------|
| 🤖 AI Chatbot | GPT-powered chatbot to answer common result queries |
| 📊 Analytics Dashboard | Trends, avg resolution time, department-wise breakdown |
| 📱 Mobile App | React Native app for students |
| 🔔 Email Notifications | Send email alerts on status changes (Flask-Mail) |
| 🏫 Multi-College | SaaS model — one system for multiple colleges |
| 📆 Deadline Tracking | SLA enforcement — escalation if not resolved in N days |
| 🔐 2FA | Two-factor authentication for admin accounts |
| 🗃️ PostgreSQL | Upgrade to production-grade relational DB |

---

## 📸 Screenshots

| Page | Description |
|------|-------------|
| Login/Register | Glassmorphism dark-mode authentication page |
| Student Dashboard | Stats cards, complaint form with file upload, complaint history |
| Admin Dashboard | Analytics charts, complaints table with verify/PDF/delete |
| PDF Output | Professional A4 document with watermark and signatures |

---

## 👤 Author

**[Your Name]**  
6th Semester – Computer Engineering  
Mini Project – Industry-Oriented Full Stack Application  
Guided by: *[Nata]*

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.


Admin credentials:
      admin@srqrs.edu / Admin@123
#   S t u d e n t - R e s u l t - Q u e r y - R e s o l u t i o n - S y s t e m  
 