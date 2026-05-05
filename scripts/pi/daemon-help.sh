#!/usr/bin/env bash
# Print copy-paste notes for systemd (do not run ada daemon from cron).
#
# Does not invoke ada; resolves ROOT only (optional .venv path in snippet).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/_lib.sh"

ada_pi_resolve_root
ada_pi_load_dotenv

USER_NAME="${ADA_PI_SYSTEMD_USER:-$(id -un)}"
GROUP_NAME="${ADA_PI_SYSTEMD_GROUP:-$(id -gn)}"
ADA_BIN="${ROOT}/.venv/bin/ada"
SERVICE_NAME="${ADA_PI_SYSTEMD_SERVICE_NAME:-ada-daemon.service}"

cat <<EOF
Pi / Linux: continuous worker (exactly ONE ada daemon per profile)

1) Logs directory (adjust if you use ADA_DATA_DIR elsewhere):
   mkdir -p ${ROOT}/data/logs

2) systemd unit (${SERVICE_NAME}), as root — replace paths if your checkout differs:

---8<---
[Unit]
Description=ADA goal and workflow daemon
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=${USER_NAME}
Group=${GROUP_NAME}
WorkingDirectory=${ROOT}
EnvironmentFile=${ROOT}/.env
ExecStart=${ADA_BIN} daemon
Restart=on-failure
RestartSec=5
StandardOutput=append:${ROOT}/data/logs/ada-daemon.log
StandardError=append:${ROOT}/data/logs/ada-daemon.log

[Install]
WantedBy=multi-user.target
---8<---

Place at e.g. /etc/systemd/system/${SERVICE_NAME} then:

  sudo systemctl daemon-reload
  sudo systemctl enable --now ${SERVICE_NAME}

3) Sanity checks:

  sudo systemctl status ${SERVICE_NAME}
  journalctl -u ${SERVICE_NAME} -n 200 --no-pager

Canonical narrative: docs/operator-runbook-raspberry-pi.md and ops/schedule.md §4.
EOF
