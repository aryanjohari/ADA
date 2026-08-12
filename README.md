# ADA (M00–M04)

Body sense, Gemini chat harness, Tailscale Serve control-plane HUD, and dual-store memory + Dream seal on the Pi.

## Install

```bash
cd /mnt/ada-data/ADA
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Data root defaults to `/mnt/ada-data`. Override for tests/sandboxes:

```bash
export ADA_DATA_ROOT=/tmp/ada-sandbox
```

## CLI — body

```bash
ada body birth          # write identity.yaml once + lifecycle birth
ada body status         # vitals + born_at + last wake/fault
ada body status --json
ada body vitals --json
ada body whoami
ada body wake           # append wake (optional: --ensure-birth)
ada body sleep
ada body fault --summary "test"
ada body story -n 20    # plain autobiography from ledger only
ada body doctor         # mount + probes; exit 3 if ada-data missing
```

## CLI — chat

```bash
ada chat                # REPL (observe default)
ada chat -q "how is the body?"
ada chat --mode agent
```

Requires `GEMINI_API_KEY` or `/mnt/ada-data/secrets/gemini.env`.

## CLI — HUD (M03)

Localhost-only control plane (five panes). Expose with **Tailscale Serve** — **Funnel NO**.

```bash
# secrets for Agent mode (mode 0600; never commit)
# /mnt/ada-data/secrets/hud.env
#   ADA_HUD_SESSION_SECRET=...
#   ADA_HUD_PASSWORD=...

ada hud serve --host 127.0.0.1 --port 8787

# on the Pi (tailnet HTTPS / MagicDNS enabled):
tailscale serve --bg 8787
tailscale serve status          # expect proxy → 127.0.0.1; Funnel off
```

- Bind defaults to `127.0.0.1`; non-loopback hosts are refused.
- Observe chat works with mesh presence via Serve; Agent/Plan need session login.
- Vitals panes call the same organs as `ada body doctor`.
- Chat uses the same `harness.run_turn` / `runs/` JSONL as `ada chat` (one interactive writer at a time).

## CLI — memory / Dream (M04)

Dual-store FACTS (YAML) + WORLDVIEW (MD). No embeddings. Dream push is stubbed.

```bash
ada memory append --key prefs.brief_time --value 05:30
ada memory get prefs.brief_time
ada memory search brief_time
ada memory loops

ada dream run                 # delta → seal → capped manage → merge → push=skipped
ada dream run --skip-manage   # local seal only (still dream_ok)
ada dream status
```

Optional timer pointer (not a gate): `deploy/systemd/ada-dream.timer` (~03:30 NZST).
Quiet hours **23:00–05:30 NZST**; default `brief_time` **05:30**.

Voice exemplars: `docs/VOICE_EXEMPLARS.md` (boot-loaded with §14 + anti-fluff).

Equivalent without the Typer wrapper:

```bash
uvicorn ada.hud.app:create_app --factory --host 127.0.0.1 --port 8787
```

## Tests

```bash
pytest -q
pytest -q tests/test_hud_*.py
```
