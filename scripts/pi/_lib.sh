# Shared helpers for scripts/pi/*.sh (source from entry scripts only).
#
# Example missions (create yourself with `ada mission init` — not created by these scripts):
#   my-site-matrix  — RSS / triage / graph / matrix entity publish track
#   my-site-kw      — GSC → keyword-select → publish_keyword_v1 (see scripts/ada_keyword_track.sh)
#
# Override checkout path: export ADA_REPO_ROOT=/path/to/ADA

ada_pi_resolve_root() {
  local _here
  _here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  export ROOT="${ADA_REPO_ROOT:-$(cd "${_here}/../.." && pwd)}"
}

ada_pi_load_dotenv() {
  if [[ -f "${ROOT}/.env" ]]; then
    set -a
    # shellcheck source=/dev/null
    source "${ROOT}/.env"
    set +a
  fi
}

ada_pi_maybe_venv() {
  if [[ -f "${ROOT}/.venv/bin/activate" ]]; then
    # shellcheck source=/dev/null
    source "${ROOT}/.venv/bin/activate"
  fi
}

ada_pi_require_ada() {
  if ! command -v ada >/dev/null 2>&1; then
    echo "ada not found in PATH. Create .venv, activate, and pip install the package (see README §10)." >&2
    exit 1
  fi
}

# Full bootstrap for scripts that invoke ada: root, .env, venv, ada on PATH.
ada_pi_bootstrap_cli() {
  cd "$ROOT"
  ada_pi_load_dotenv
  ada_pi_maybe_venv
  ada_pi_require_ada
}
