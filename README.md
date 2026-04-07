🎓 Student Result Query Resolution System (SRQRS)

Production-Ready Full-Stack Web Application for Academic Complaint Management

📌 Overview

The Student Result Query Resolution System (SRQRS) is a full-stack web platform designed to digitize and streamline the process of handling student result-related complaints.

It replaces inefficient manual workflows with a secure, trackable, and automated system, enabling both students and administrators to interact seamlessly.

🚨 Problem Statement

Traditional result grievance systems suffer from:

Manual paperwork and physical visits
Lost or delayed complaint forms
No real-time tracking
Lack of transparency
No centralized data or analytics
✅ Solution

SRQRS introduces:

Online complaint submission
Document uploads (Application + HOD approval)
Real-time status tracking
Admin dashboard with analytics
Instant PDF generation with verification
🛠 Tech Stack
Layer	Technology
Frontend	HTML5, CSS3, Bootstrap 5, JavaScript
Backend	Python (Flask)
Database	SQLite3 (scalable to PostgreSQL/MySQL)
PDF Engine	ReportLab
Authentication	Flask Sessions + Werkzeug Security
Charts	Chart.js
✨ Core Features
👨‍🎓 Student Module
Secure registration & login
Submit complaints with priority & issue type
Upload:
Application document
HOD-signed document
Track complaint status:
Pending → In Progress → Resolved
View admin replies
Download official complaint PDF
🛠 Admin Module
Secure admin login
Dashboard with analytics (charts + stats)
Manage all complaints:
Update status
Add replies
Mark as verified
View uploaded documents
Download complaint PDFs
Delete complaints
📄 PDF Generation
Unique Complaint ID (e.g., SRQRS-0001)
Student + complaint details
Status-based watermark:
Pending → Amber
In Progress → Blue
Resolved → Green
Admin remarks section
Signature section:
Student
HOD
Admin
🗄 Database Design
Users Table
id INTEGER PRIMARY KEY,
name TEXT,
email TEXT UNIQUE,
prn TEXT UNIQUE,
password TEXT,
role TEXT DEFAULT 'student'
Complaints Table
id INTEGER PRIMARY KEY,
user_id INTEGER,
subject TEXT,
issue_type TEXT,
description TEXT,
status TEXT DEFAULT 'Pending',
priority TEXT,
reply TEXT,
application_file TEXT,
hod_sign_file TEXT,
is_verified INTEGER DEFAULT 0
🏗 System Architecture
Client (Browser)
     ↓
Frontend (HTML, Bootstrap, JS)
     ↓
Flask Backend (Routes + Auth + PDF)
     ↓
SQLite Database
     ↓
File Storage (Uploads)
🔒 Security Features
Password hashing (PBKDF2-SHA256)
Session-based authentication
Role-based access control
File validation & secure upload
SQL injection prevention
XSS protection via Jinja2
IDOR prevention (user ownership checks)
🚀 Installation & Setup
Prerequisites
Python 3.10+
pip
Steps
git clone https://github.com/your-username/srqrs.git
cd srqrs

python -m venv venv
venv\Scripts\activate   # Windows
# source venv/bin/activate  # Linux/Mac

pip install -r project/requirements.txt

cd project
python app.py
🌐 Access
http://localhost:5000
Default Admin Credentials
Email	Password
admin@srqrs.edu
	Admin@123
🧪 Testing

Run test suite:

pytest test_app.py -v

✔ Covers:

Authentication
Complaint flow
Admin operations
PDF generation
API endpoints
🔌 API Endpoints
Get Stats
GET /api/stats
Search Complaints
GET /api/complaints/search?q=
Download PDF
GET /download_pdf/<id>
☁️ Deployment
Render / Railway Supported

Start Command:

cd project && gunicorn app:app

Add to requirements:

gunicorn==21.2.0
🔮 Future Enhancements
AI-based query assistant
Email/SMS notifications
Mobile application
Multi-college SaaS model
SLA-based complaint tracking
Two-factor authentication
👤 Author

Sarthak Dhumal
Computer Engineering (6th Semester)
Mini Project

📄 License

MIT License
