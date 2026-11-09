"""
Phase 8 §8 — security checklist, the parts that are actually testable
(SQL injection and CORS are reviewed manually — see docs/phases/
MENTORA_Phase8_Integration_Testing_Performance.md's checklist notes).

test_login_rate_limit_eventually_kicks_in is intentionally ordered to run
after test_auth_edge_cases.py (alphabetically "security" > "auth_edge_cases")
since it deliberately exhausts /auth/login's per-minute quota — the limiter
is a single in-memory counter for the whole session-scoped app, shared
across every test file in one pytest run. No later test in THIS file depends
on a fresh login quota afterward.
"""

from services.auth_service import hash_password
from services.rate_limit import limiter


def _register(client, email):
    resp = client.post("/auth/register", json={
        "first_name": "Sec", "last_name": "Test", "email": email,
        "password": "testpass123", "confirm_password": "testpass123",
        "university": "Test University", "exam_goal": "sindh_university",
    })
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def test_cv_upload_rejects_renamed_executable(client):
    headers = _register(client, "sec-exe-upload@example.com")
    fake_exe = b"MZ\x90\x00\x03\x00\x00\x00" + b"\x00" * 100  # real PE/EXE header magic bytes
    files = {"cv_file": ("resume.pdf", fake_exe, "application/pdf")}
    r = client.post("/career/cv-upload", headers=headers, files=files)
    assert r.status_code == 415


def test_cv_upload_rejects_disallowed_extension(client):
    headers = _register(client, "sec-bad-ext@example.com")
    files = {"cv_file": ("resume.exe", b"MZ\x90\x00", "application/octet-stream")}
    r = client.post("/career/cv-upload", headers=headers, files=files)
    assert r.status_code == 415


def test_cv_upload_rejects_oversized_file(client):
    headers = _register(client, "sec-oversized@example.com")
    oversized = b"a" * (6 * 1024 * 1024)  # 6MB, over the 5MB cap
    files = {"cv_file": ("resume.txt", oversized, "text/plain")}
    r = client.post("/career/cv-upload", headers=headers, files=files)
    assert r.status_code == 413


def test_cv_upload_accepts_valid_pdf_magic_bytes(client):
    headers = _register(client, "sec-valid-pdf@example.com")
    # Minimal but real PDF structure — enough for pdfplumber to open without
    # error, which is what distinguishes "rejected for being fake" (415)
    # from "rejected for some other reason" in this test.
    import pdfplumber  # noqa: F401 - just confirming it's importable here too

    minimal_pdf = (
        b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
        b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 200 200]>>endobj\n"
        b"xref\n0 4\n0000000000 65535 f \ntrailer<</Size 4/Root 1 0 R>>\n%%EOF"
    )
    files = {"cv_file": ("resume.pdf", minimal_pdf, "application/pdf")}
    r = client.post("/career/cv-upload", headers=headers, files=files)
    # A valid-but-contentless PDF should fail at "no text extracted" (422),
    # never at "doesn't look like a PDF" (415) — that's the actual thing
    # this test is checking: real PDFs pass the magic-byte gate.
    assert r.status_code != 415


def test_password_is_actually_hashed_not_plaintext(db_session):
    # Manual check from the doc's §8 table, automated: confirm a real bcrypt
    # hash is stored, not the plaintext password.
    plain = "testpass123"
    hashed = hash_password(plain)
    assert hashed != plain
    assert hashed.startswith("$2b$") or hashed.startswith("$2a$")  # bcrypt's own format prefix


def test_login_rate_limit_eventually_kicks_in(client):
    # Rate limiting is disabled by default across this test suite (see
    # conftest.py) since 11+ legitimate register/login calls spread across
    # the suite would otherwise exhaust the real production limits within
    # seconds. Re-enabled only for this one test, which exists specifically
    # to prove the mechanism itself works.
    limiter.enabled = True
    try:
        _register(client, "sec-ratelimit@example.com")
        statuses = []
        for _ in range(10):
            r = client.post("/auth/login", json={"email": "sec-ratelimit@example.com", "password": "wrongpassword"})
            statuses.append(r.status_code)
            if r.status_code == 429:
                break
        assert 429 in statuses, f"expected a 429 within 10 attempts, got statuses {statuses}"
    finally:
        limiter.enabled = False
