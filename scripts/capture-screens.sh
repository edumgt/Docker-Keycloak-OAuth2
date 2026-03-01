#!/usr/bin/env bash
set -euo pipefail

mkdir -p captures

docker compose run --rm --no-deps capture " \
  mkdir -p captures && \
  npx -y playwright@1.58.2 screenshot --device='Desktop Chrome' \
    http://backend:8000/docs captures/backend-swagger.png && \
  npx -y playwright@1.58.2 screenshot --device='Desktop Chrome' \
    'http://keycloak:8080/realms/integrated-id/protocol/openid-connect/auth?client_id=be-client&redirect_uri=http%3A%2F%2Flocalhost%3A8000%2Fdocs&response_type=code&scope=openid%20profile%20email' \
    captures/keycloak-login.png && \
  cd /tmp && \
  npm init -y >/dev/null 2>&1 && \
  npm install playwright@1.58.2 >/dev/null 2>&1 && \
  NODE_PATH=/tmp/node_modules node /work/scripts/capture-fe-login-success.js \
"

echo "Screenshots saved under captures/."
