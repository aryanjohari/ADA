#!/usr/bin/env bash
# Open ADA HUD from Mac over Tailscale Serve.
# Safari: File → Add to Dock after first open for a packaged feel.
set -euo pipefail

URL="${ADA_HUD_URL:-https://ada-pi5.tailbc896a.ts.net}"

if ! command -v tailscale >/dev/null 2>&1; then
  echo "tailscale CLI not found — install Tailscale, then retry." >&2
  exit 1
fi

if ! tailscale status >/dev/null 2>&1; then
  echo "Tailscale is off or not logged in — turn it on, then retry." >&2
  exit 1
fi

if command -v curl >/dev/null 2>&1; then
  if ! curl -sf --max-time 5 "$URL/" >/dev/null; then
    echo "HUD not reachable at $URL — is ada hud serve + Serve up on the Pi?" >&2
    exit 1
  fi
fi

if [[ "$(uname -s)" == "Darwin" ]]; then
  open "$URL"
else
  echo "Open: $URL"
  if command -v xdg-open >/dev/null 2>&1; then
    xdg-open "$URL" || true
  fi
fi
