#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
LOG_FILE="${1:-${ROOT_DIR}/logs/app.log}"

if [ ! -e "${LOG_FILE}" ]; then
  echo "Log file ${LOG_FILE} does not exist yet. Waiting for it to be created..." >&2
  mkdir -p "$(dirname "${LOG_FILE}")"
  touch "${LOG_FILE}"
fi

exec tail -n0 -F "${LOG_FILE}" | python - <<'PY'
import json
import sys

SEPARATOR = "=" * 80
for raw_line in sys.stdin:
    raw_line = raw_line.strip()
    if not raw_line:
        continue
    try:
        record = json.loads(raw_line)
    except json.JSONDecodeError:
        continue
    if record.get("event") != "inference.phase_intermediate":
        continue

    timestamp = record.get("timestamp", "")
    session = record.get("session_id", "unknown")
    phase = record.get("phase_id", "unknown")
    workflow = record.get("workflow", "")
    response = record.get("response", "")

    header = f"[{timestamp}] Session: {session} | Phase: {phase}"
    if workflow:
        header += f" ({workflow})"

    print(SEPARATOR)
    print(header)
    print("-" * len(header))
    print(response)
    print(SEPARATOR)
    sys.stdout.flush()
PY
