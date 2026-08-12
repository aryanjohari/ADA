#!/usr/bin/env bash
# Manual acceptance driver for M00 body sense (subset of body §10 / M00 §9.2).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "== import version =="
python -c "import ada; print(ada.__version__)"

SMOKE_ROOT="${ADA_DATA_ROOT:-}"
if [[ -z "${SMOKE_ROOT}" ]]; then
  # Prefer a disposable sandbox unless operator exports ADA_DATA_ROOT.
  SMOKE_ROOT="$(mktemp -d /tmp/ada-smoke-XXXXXX)"
  export ADA_DATA_ROOT="$SMOKE_ROOT"
  echo "Using sandbox ADA_DATA_ROOT=$ADA_DATA_ROOT"
  CLEANUP=1
else
  echo "Using ADA_DATA_ROOT=$ADA_DATA_ROOT"
  CLEANUP=0
fi

echo "== doctor =="
ada body doctor || true

echo "== vitals --json (temp/disk spot-check manually vs vcgencmd/df) =="
ada body vitals --json | head -c 800 || true
echo

echo "== birth twice (born_at must stick) =="
ada body birth
ada body birth
ada body whoami

echo "== wake + story =="
ada body wake
ada body story -n 10

echo "== refuse writes when root missing =="
MISSING="$(mktemp -u /tmp/ada-missing-XXXXXX)"
if ADA_DATA_ROOT="$MISSING" ada body birth; then
  echo "FAIL: birth succeeded without mount" >&2
  exit 1
else
  echo "OK: birth refused without mount"
fi

echo "== package files under data root =="
ls -la "$ADA_DATA_ROOT/memory/facts/identity.yaml"
ls -la "$ADA_DATA_ROOT/memory/lifecycle.jsonl"
echo "SMOKE OK"

if [[ "$CLEANUP" -eq 1 ]]; then
  rm -rf "$SMOKE_ROOT"
fi
