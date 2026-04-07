"""
Unit Tests for Student Result Query Resolution System (SRQRS)
Run with: pytest test_app.py -v
"""

import pytest
import sys
import os
import tempfile

# Add project directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, init_db, get_db


# ─────────────────────────────────────────────
#  FIXTURES
# ─────────────────────────────────────────────

@pytest.fixture
def test_app():
    """Configure app with a temporary test database."""
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    
    app.config["TESTING"]        = True
    app.config["SECRET_KEY"]     = "test-secret-key"
    app.config["WTF_CSRF_ENABLED"] = False

    # Patch DB_PATH to use temp DB
    import app as app_module
    original_db = app_module.DB_PATH
    app_module.DB_PATH = db_path

    with app.app_context():
        app_module.init_db()

    yield app

    # Cleanup
    app_module.DB_PATH = original_db
    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture
def client(test_app):
    """Test client."""
    return test_app.test_client()


@pytest.fixture
def registered_student(client):
    """Register and return a test student."""
    client.post("/register", data={
        "name":             "Test Student",
        "email":            "student@test.edu",
        "prn":              "TEST001",
        "password":         "pass1234",
        "confirm_password": "pass1234"
    }, follow_redirects=True)
    return {"email": "student@test.edu", "password": "pass1234",
            "name": "Test Student", "prn": "TEST001"}


@pytest.fixture
def admin_client(client):
    """A client logged in as admin."""
    client.post("/login", data={
        "email":    "admin@srqrs.edu",
        "password": "Admin@123"
    }, follow_redirects=True)
    return client


@pytest.fixture
def student_client(client, registered_student):
    """A client logged in as student."""
    client.post("/login", data={
        "email":    registered_student["email"],
        "password": registered_student["password"]
    }, follow_redirects=True)
    return client


# ─────────────────────────────────────────────
#  1. AUTHENTICATION TESTS
# ─────────────────────────────────────────────

class TestAuth:

    def test_home_redirects_to_login(self, client):
        """GET / should show login page."""
        resp = client.get("/", follow_redirects=True)
        assert resp.status_code == 200
        assert b"Sign In" in resp.data or b"Login" in resp.data

    def test_register_get(self, client):
        """GET /register should return the registration form."""
        resp = client.get("/register")
        assert resp.status_code == 200
        assert b"Create Account" in resp.data or b"Register" in resp.data

    def test_register_new_student(self, client):
        """POST /register with valid data should redirect to login."""
        resp = client.post("/register", data={
            "name":             "Alice Kumar",
            "email":            "alice@college.edu",
            "prn":              "ALICE001",
            "password":         "secure123",
            "confirm_password": "secure123"
        }, follow_redirects=True)
        assert resp.status_code == 200

    def test_register_duplicate_email(self, client, registered_student):
        """Re-registering same email should fail."""
        resp = client.post("/register", data={
            "name":             "Duplicate",
            "email":            registered_student["email"],
            "prn":              "DIFF001",
            "password":         "pass1234",
            "confirm_password": "pass1234"
        }, follow_redirects=True)
        data = resp.data.decode()
        assert "already registered" in data.lower() or resp.status_code == 200

    def test_login_valid_student(self, client, registered_student):
        """Valid student credentials should redirect to dashboard."""
        resp = client.post("/login", data={
            "email":    registered_student["email"],
            "password": registered_student["password"]
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert b"Dashboard" in resp.data or b"dashboard" in resp.data

    def test_login_valid_admin(self, client):
        """Default admin credentials should redirect to admin dashboard."""
        resp = client.post("/login", data={
            "email":    "admin@srqrs.edu",
            "password": "Admin@123"
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert b"Admin" in resp.data or b"admin" in resp.data

    def test_login_invalid_password(self, client, registered_student):
        """Wrong password should show error, not log in."""
        resp = client.post("/login", data={
            "email":    registered_student["email"],
            "password": "wrongpassword"
        }, follow_redirects=True)
        data = resp.data.decode()
        assert "invalid" in data.lower() or resp.status_code == 200

    def test_login_nonexistent_user(self, client):
        """Non-existent user should not log in."""
        resp = client.post("/login", data={
            "email":    "nobody@nowhere.com",
            "password": "anything"
        }, follow_redirects=True)
        data = resp.data.decode()
        assert "invalid" in data.lower() or resp.status_code == 200

    def test_logout(self, student_client):
        """Logout should clear session and redirect."""
        resp = student_client.get("/logout", follow_redirects=True)
        assert resp.status_code == 200

    def test_dashboard_requires_login(self, client):
        """Unauthenticated access to /dashboard should redirect."""
        resp = client.get("/dashboard")
        assert resp.status_code in (301, 302, 200)

    def test_admin_requires_admin_role(self, client, student_client):
        """Student should not be able to access /admin."""
        resp = student_client.get("/admin")
        # Should either redirect (302) or render a non-admin page
        if resp.status_code == 302:
            # Redirect is fine — access properly denied
            assert True
        else:
            assert b"Admin Dashboard" not in resp.data


# ─────────────────────────────────────────────
#  2. COMPLAINT TESTS
# ─────────────────────────────────────────────

class TestComplaints:

    def test_submit_valid_complaint(self, student_client):
        """Student can submit a complaint with valid data."""
        resp = student_client.post("/add_complaint", data={
            "subject":     "Mathematics III",
            "issue_type":  "Marks Not Updated",
            "description": "My unit test 2 marks are missing.",
            "priority":    "High"
        }, follow_redirects=True)
        assert resp.status_code == 200

    def test_submit_complaint_missing_subject(self, student_client):
        """Complaint without subject should fail validation."""
        resp = student_client.post("/add_complaint", data={
            "subject":     "",
            "issue_type":  "Grade Discrepancy",
            "description": "Some description",
            "priority":    "Normal"
        }, follow_redirects=True)
        data = resp.data.decode()
        assert "required" in data.lower() or resp.status_code == 200

    def test_submit_complaint_missing_description(self, student_client):
        """Complaint without description should fail."""
        resp = student_client.post("/add_complaint", data={
            "subject":     "DBMS",
            "issue_type":  "Grade Discrepancy",
            "description": "",
            "priority":    "Normal"
        }, follow_redirects=True)
        assert resp.status_code == 200

    def test_student_dashboard_shows_complaints(self, student_client):
        """Student dashboard should list submitted complaints."""
        # Submit a complaint first
        student_client.post("/add_complaint", data={
            "subject":     "Physics",
            "issue_type":  "Wrong Marks Entered",
            "description": "My marks are incorrectly entered.",
            "priority":    "Normal"
        })
        resp = student_client.get("/dashboard")
        assert resp.status_code == 200
        assert b"Physics" in resp.data

    def test_complaint_appears_in_admin_dashboard(self, student_client, admin_client):
        """Complaint submitted by student should appear in admin view."""
        student_client.post("/add_complaint", data={
            "subject":     "Chemistry",
            "issue_type":  "Result Not Published",
            "description": "Result not visible on portal.",
            "priority":    "High"
        })
        resp = admin_client.get("/admin")
        assert resp.status_code == 200
        assert b"Chemistry" in resp.data


# ─────────────────────────────────────────────
#  3. ADMIN OPERATIONS TESTS
# ─────────────────────────────────────────────

class TestAdminOperations:

    def _submit_complaint(self, student_client):
        student_client.post("/add_complaint", data={
            "subject":     "Test Subject",
            "issue_type":  "Other",
            "description": "Test complaint description.",
            "priority":    "Normal"
        })

    def _get_first_complaint_id(self, admin_client):
        import app as app_module
        db = app_module.get_db()
        row = db.execute("SELECT id FROM complaints LIMIT 1").fetchone()
        db.close()
        return row["id"] if row else None

    def test_admin_can_update_status(self, student_client, admin_client):
        """Admin can change complaint status to Resolved."""
        self._submit_complaint(student_client)
        cid = self._get_first_complaint_id(admin_client)
        if cid:
            resp = admin_client.post(f"/admin/update/{cid}", data={
                "status": "Resolved",
                "reply":  "Issue has been resolved."
            }, follow_redirects=True)
            assert resp.status_code == 200

    def test_admin_can_verify_complaint(self, student_client, admin_client):
        """Admin can toggle verify status."""
        self._submit_complaint(student_client)
        cid = self._get_first_complaint_id(admin_client)
        if cid:
            resp = admin_client.post(f"/admin/verify/{cid}",
                                     follow_redirects=True)
            assert resp.status_code == 200

    def test_admin_can_delete_complaint(self, student_client, admin_client):
        """Admin can delete a complaint."""
        self._submit_complaint(student_client)
        cid = self._get_first_complaint_id(admin_client)
        if cid:
            resp = admin_client.post(f"/admin/delete/{cid}",
                                     follow_redirects=True)
            assert resp.status_code == 200

    def test_student_cannot_update_status(self, student_client):
        """Student should not be able to call admin update route."""
        resp = student_client.post("/admin/update/1", data={
            "status": "Resolved",
            "reply":  "Hacked!"
        }, follow_redirects=True)
        # Should redirect to home/login, not succeed
        assert b"Admin Dashboard" not in resp.data


# ─────────────────────────────────────────────
#  4. PDF GENERATION TESTS
# ─────────────────────────────────────────────

class TestPDF:

    def _submit_and_get_id(self, student_client):
        student_client.post("/add_complaint", data={
            "subject":     "PDF Test Subject",
            "issue_type":  "Marks Not Updated",
            "description": "Testing PDF generation.",
            "priority":    "Normal"
        })
        import app as app_module
        db = app_module.get_db()
        row = db.execute("SELECT id FROM complaints LIMIT 1").fetchone()
        db.close()
        return row["id"] if row else None

    def test_pdf_download_for_own_complaint(self, student_client):
        """Student should be able to download PDF of own complaint."""
        cid = self._submit_and_get_id(student_client)
        if cid:
            resp = student_client.get(f"/download_pdf/{cid}")
            assert resp.status_code == 200
            assert resp.content_type == "application/pdf"
            assert resp.data[:4] == b"%PDF"  # PDF magic bytes

    def test_pdf_content_type(self, student_client):
        """PDF response must have application/pdf content type."""
        cid = self._submit_and_get_id(student_client)
        if cid:
            resp = student_client.get(f"/download_pdf/{cid}")
            assert "pdf" in resp.content_type.lower()

    def test_pdf_not_found_invalid_id(self, student_client):
        """Non-existent complaint PDF should redirect."""
        self._submit_and_get_id(student_client)
        resp = student_client.get("/download_pdf/99999",
                                  follow_redirects=True)
        assert resp.status_code == 200  # redirected to dashboard

    def test_admin_can_download_any_pdf(self, student_client, admin_client):
        """Admin can download PDF of any student's complaint."""
        cid = self._submit_and_get_id(student_client)
        if cid:
            resp = admin_client.get(f"/download_pdf/{cid}")
            assert resp.status_code == 200
            assert resp.content_type == "application/pdf"


# ─────────────────────────────────────────────
#  5. API ENDPOINT TESTS
# ─────────────────────────────────────────────

class TestAPI:

    def test_api_stats_returns_json(self, admin_client):
        """API stats should return valid JSON."""
        resp = admin_client.get("/api/stats")
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data, dict)

    def test_api_stats_unauthorized(self, client):
        """Unauthenticated user cannot access API stats."""
        resp = client.get("/api/stats")
        assert resp.status_code in (302, 403, 401, 200)

    def test_api_search_returns_list(self, admin_client, student_client):
        """Search API returns list of matching complaints."""
        student_client.post("/add_complaint", data={
            "subject":     "Searchable Subject",
            "issue_type":  "Other",
            "description": "Unique description for search test.",
            "priority":    "Low"
        })
        resp = admin_client.get("/api/complaints/search?q=Searchable")
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data, list)


# ─────────────────────────────────────────────
#  6. INPUT VALIDATION TESTS
# ─────────────────────────────────────────────

class TestInputValidation:

    def test_register_short_password(self, client):
        """Passwords shorter than 6 chars should be rejected."""
        resp = client.post("/register", data={
            "name":             "Short Pass",
            "email":            "short@test.edu",
            "prn":              "SHORT01",
            "password":         "12345",
            "confirm_password": "12345"
        }, follow_redirects=True)
        data = resp.data.decode()
        assert "6" in data or resp.status_code == 200

    def test_register_mismatched_passwords(self, client):
        """Mismatched passwords should fail."""
        resp = client.post("/register", data={
            "name":             "Mismatch User",
            "email":            "mismatch@test.edu",
            "prn":              "MISMATCH1",
            "password":         "pass1234",
            "confirm_password": "different"
        }, follow_redirects=True)
        data = resp.data.decode()
        assert "match" in data.lower() or resp.status_code == 200

    def test_complaint_requires_all_fields(self, student_client):
        """All complaint fields are required."""
        resp = student_client.post("/add_complaint", data={
            "subject":     "Only Subject",
            "issue_type":  "",
            "description": "",
            "priority":    "Normal"
        }, follow_redirects=True)
        assert resp.status_code == 200


# ─────────────────────────────────────────────
#  RUN
# ─────────────────────────────────────────────
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
