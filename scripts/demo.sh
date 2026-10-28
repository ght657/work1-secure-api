#!/usr/bin/env bash
# End-to-end API demonstration + evidence capture.
# Usage: ./scripts/demo.sh [evidence-dir]
set -euo pipefail
cd "$(dirname "$0")/.."

OUT="${1:-evidence}"
mkdir -p "$OUT"
BASE_URL="${BASE_URL:-http://127.0.0.1:5000}"

# Start the API in the background and wait until it is healthy.
.venv/bin/python run.py &
SERVER_PID=$!
trap 'kill "$SERVER_PID" 2>/dev/null || true' EXIT
for _ in $(seq 1 40); do
  curl -sf "$BASE_URL/health" >/dev/null 2>&1 && break
  sleep 0.5
done

echo ">>> 1) POST /auth/login - successful authentication" | tee "$OUT/01_login_success.txt"
curl -s -X POST "$BASE_URL/auth/login" -H "Content-Type: application/json" \
  -d '{"login":"alice","password":"Alice#Strong1"}' | tee -a "$OUT/01_login_success.txt"
echo | tee -a "$OUT/01_login_success.txt"

TOKEN=$(curl -s -X POST "$BASE_URL/auth/login" -H "Content-Type: application/json" \
  -d '{"login":"alice","password":"Alice#Strong1"}' | /usr/bin/python3 -c "import sys,json;print(json.load(sys.stdin)['token'])")

echo ">>> 2) POST /auth/login - wrong password (401)" | tee "$OUT/02_login_wrong_password.txt"
curl -s -o - -w "\nHTTP %{http_code}\n" -X POST "$BASE_URL/auth/login" \
  -H "Content-Type: application/json" -d '{"login":"alice","password":"WRONG"}' \
  | tee -a "$OUT/02_login_wrong_password.txt"

echo ">>> 3) GET /api/data WITHOUT token (must be denied, 401)" | tee "$OUT/03_data_denied.txt"
curl -s -o - -w "\nHTTP %{http_code}\n" "$BASE_URL/api/data" | tee -a "$OUT/03_data_denied.txt"

echo ">>> 4) GET /api/data WITH valid JWT (200, data returned)" | tee "$OUT/04_data_with_token.txt"
curl -s -o - -w "\nHTTP %{http_code}\n" "$BASE_URL/api/data" \
  -H "Authorization: Bearer $TOKEN" | tee -a "$OUT/04_data_with_token.txt"

echo ">>> 5) SQL injection attempt on GET /api/users/search (payload treated as data)" | tee "$OUT/05_sqli_attempt.txt"
curl -s -o - -w "\nHTTP %{http_code}\n" "$BASE_URL/api/users/search?q=%27%20OR%20%271%27%3D%271" \
  -H "Authorization: Bearer $TOKEN" | tee -a "$OUT/05_sqli_attempt.txt"

echo ">>> 6) Stored XSS: POST a <script> payload, then read it back escaped" | tee "$OUT/06_xss_post.txt"
curl -s -o - -w "\nHTTP %{http_code}\n" -X POST "$BASE_URL/api/posts" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"title":"<script>alert(\"xss\")</script>","body":"<img src=x onerror=alert(1)>"}' \
  | tee -a "$OUT/06_xss_post.txt"
curl -s "$BASE_URL/api/data" -H "Authorization: Bearer $TOKEN" | tee "$OUT/06_xss_readback.txt"

echo "done"
