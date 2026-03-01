#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
ARTIFACT_DIR="${ROOT_DIR}/artifacts"
mkdir -p "${ARTIFACT_DIR}"

USERS=(
  "demo-user:demo1234:demo-user@example.com:Demo:User"
  "demo-user2:demo2234:demo-user2@example.com:Demo:User2"
  "demo-user3:demo3234:demo-user3@example.com:Demo:User3"
)

echo "[1/4] Ensure services are running"
docker compose up -d keycloak backend >/dev/null

echo "[2/4] Login Keycloak admin"
docker compose exec -T keycloak /opt/keycloak/bin/kcadm.sh config credentials \
  --server http://localhost:8080 \
  --realm master \
  --user admin \
  --password admin1234 >/dev/null

echo "[3/4] Provision 3 login accounts"
for entry in "${USERS[@]}"; do
  IFS=":" read -r username password email first_name last_name <<< "${entry}"

  if docker compose exec -T keycloak /opt/keycloak/bin/kcadm.sh create users \
    -r integrated-id \
    -s "username=${username}" \
    -s "enabled=true" \
    -s "emailVerified=true" \
    -s "email=${email}" \
    -s "firstName=${first_name}" \
    -s "lastName=${last_name}" >/dev/null 2>&1; then
    echo "  - created: ${username}"
  else
    echo "  - exists:  ${username}"
  fi

  docker compose exec -T keycloak /opt/keycloak/bin/kcadm.sh set-password \
    -r integrated-id \
    --username "${username}" \
    --new-password "${password}" >/dev/null
done

echo "[4/4] Generate JWT x3 and validate logins"
docker compose exec -T backend python - <<'PY' > "${ARTIFACT_DIR}/jwt-tokens.json"
import json
from datetime import datetime, timezone
import httpx

accounts = [
    {"username": "demo-user", "password": "demo1234"},
    {"username": "demo-user2", "password": "demo2234"},
    {"username": "demo-user3", "password": "demo3234"},
]

base = "http://127.0.0.1:8000/api/v1"
result = {
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "realm": "integrated-id",
    "client_id": "be-client",
    "tokens": [],
}

with httpx.Client(timeout=20.0) as client:
    for account in accounts:
        token_res = client.post(f"{base}/auth/token", json=account)
        token_res.raise_for_status()
        token = token_res.json()

        userinfo_res = client.get(
            f"{base}/auth/userinfo",
            headers={"Authorization": f"Bearer {token['access_token']}"},
        )
        userinfo_res.raise_for_status()
        userinfo = userinfo_res.json().get("payload", {})

        result["tokens"].append(
            {
                "username": account["username"],
                "password": account["password"],
                "token_type": token.get("token_type"),
                "expires_in": token.get("expires_in"),
                "scope": token.get("scope"),
                "access_token": token.get("access_token"),
                "refresh_token": token.get("refresh_token"),
                "userinfo": userinfo,
                "login_test_passed": True,
            }
        )

print(json.dumps(result, indent=2, ensure_ascii=False))
PY

docker compose exec -T backend python - <<'PY' > "${ARTIFACT_DIR}/login-test-results.json"
import json
from datetime import datetime, timezone
import httpx

accounts = [
    {"username": "demo-user", "password": "demo1234"},
    {"username": "demo-user2", "password": "demo2234"},
    {"username": "demo-user3", "password": "demo3234"},
]

base = "http://127.0.0.1:8000/api/v1"
results = []
overall_passed = True

with httpx.Client(timeout=20.0) as client:
    for account in accounts:
        username = account["username"]
        item = {"username": username, "token_status": None, "userinfo_status": None, "passed": False}
        try:
            token_res = client.post(f"{base}/auth/token", json=account)
            item["token_status"] = token_res.status_code
            token_res.raise_for_status()
            token = token_res.json()

            userinfo_res = client.get(
                f"{base}/auth/userinfo",
                headers={"Authorization": f"Bearer {token['access_token']}"},
            )
            item["userinfo_status"] = userinfo_res.status_code
            userinfo_res.raise_for_status()
            item["passed"] = True
        except Exception as exc:
            item["error"] = str(exc)
            overall_passed = False
        results.append(item)

payload = {
    "tested_at": datetime.now(timezone.utc).isoformat(),
    "overall_passed": overall_passed,
    "results": results,
}
print(json.dumps(payload, indent=2, ensure_ascii=False))
PY

echo "Saved: ${ARTIFACT_DIR}/jwt-tokens.json"
echo "Saved: ${ARTIFACT_DIR}/login-test-results.json"

