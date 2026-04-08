#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

PYTHON="python3"
if ! command -v "$PYTHON" >/dev/null 2>&1; then
  PYTHON="python"
fi

if [[ -f ".venv/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source ".venv/bin/activate"
fi

echo "==> Installing backend requirements"
"$PYTHON" -m pip install -r "backend/requirements.txt"

echo "==> Installing Playwright"
"$PYTHON" -m pip install playwright requests
"$PYTHON" -m playwright install chromium

echo "==> Starting BentoML service on :3000"
mkdir -p ".logs"
bentoml serve backend.main:svc --host 0.0.0.0 --port 3000 > ".logs/bentoml.log" 2>&1 &
BENTO_PID="$!"

cleanup() {
  if kill -0 "$BENTO_PID" >/dev/null 2>&1; then
    kill "$BENTO_PID" >/dev/null 2>&1 || true
    wait "$BENTO_PID" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

echo "==> Waiting for backend to accept connections"
"$PYTHON" - <<'PY'
import socket, time

deadline = time.time() + 60
last_err = None
while time.time() < deadline:
    try:
        with socket.create_connection(("127.0.0.1", 3000), timeout=1):
            print("Backend is up.")
            raise SystemExit(0)
    except OSError as e:
        last_err = e
        time.sleep(0.5)
print(f"Timed out waiting for backend on :3000. Last error: {last_err}")
raise SystemExit(1)
PY

echo "==> Running browser agent"
"$PYTHON" "browser-agent/main.py"

