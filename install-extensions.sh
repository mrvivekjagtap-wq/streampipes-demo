#!/usr/bin/env bash
# Installs all available StreamPipes pipeline elements (adapters, processors, sinks).
#
# WHY: A fresh StreamPipes install registers the ~121 bundled elements as
# "available" but not "installed". The first-run Setup wizard normally installs
# them, but the compose auto-provisions the default admin and skips that step —
# so Connect > New Adapter shows an empty list until they're installed once.
# The result is stored in CouchDB (persists across restarts); re-run this only
# after a fresh Codespace or a `docker compose down -v`.
#
# Usage:  ./install-extensions.sh            (defaults to http://localhost:80)
#         BASE=http://localhost ./install-extensions.sh
set -euo pipefail
BASE="${BASE:-http://localhost:80}"
USER_="${SP_USER:-admin@streampipes.apache.org}"
PASS="${SP_PASS:-admin}"
API="$BASE/streampipes-backend/api/v2"

echo "→ waiting for backend at $API ..."
for i in $(seq 1 60); do
  code=$(curl -s -o /dev/null -w '%{http_code}' "$API/auth/login" -X POST \
    -H 'Content-Type: application/json' \
    -d "{\"username\":\"$USER_\",\"password\":\"$PASS\"}" || true)
  [ "$code" = "200" ] && break
  sleep 5
done

TOKEN=$(curl -s "$API/auth/login" -X POST -H 'Content-Type: application/json' \
  -d "{\"username\":\"$USER_\",\"password\":\"$PASS\"}" \
  | python3 -c 'import sys,json;print(json.load(sys.stdin)["accessToken"])')
[ -n "$TOKEN" ] || { echo "✗ login failed"; exit 1; }
echo "→ logged in"

# Wait for the extensions service to register its elements, then install each.
python3 - "$API" "$TOKEN" <<'PY'
import sys, json, urllib.request, time
api, token = sys.argv[1], sys.argv[2]
def req(path, method="GET", body=None):
    r = urllib.request.Request(api+path, method=method,
        headers={"Authorization":"Bearer "+token,"Content-Type":"application/json"},
        data=json.dumps(body).encode() if body is not None else None)
    with urllib.request.urlopen(r) as resp:
        return resp.status, resp.read().decode()

exts=[]
for _ in range(60):
    _, txt = req("/extensions-services")
    svcs = json.loads(txt)
    exts = svcs[0]["providedExtensions"] if svcs else []
    if exts: break
    print("  waiting for extensions service to register..."); time.sleep(5)

ok=fail=already=0
for e in exts:
    if e.get("installed"): already+=1; continue
    body={"appId":e["appId"],"serviceTagPrefix":e["serviceTagPrefix"],"publicElement":True}
    try:
        st,_=req("/extension-installation","POST",body)
        ok+=1 if 200<=st<300 else 0
        fail+=0 if 200<=st<300 else 1
    except Exception as ex:
        fail+=1
print(f"✓ installed {ok}, already {already}, failed {fail}, total {len(exts)}")
PY
echo "→ done. Reload the UI: Connect > New adapter now lists the adapters."
