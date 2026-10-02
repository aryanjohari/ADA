# ADA

ADA is the operator's agent on the Pi. It keeps a body ledger, talks through Gemini, and serves a localhost HUD over Tailscale. Memory is two stores: facts in YAML and worldview in markdown. Life capture covers food, gym, time, habits, and people. A separate chain publishes one portfolio page at a time from research cards already on disk.

The live program is this repo on `main`. Module cards under `docs/modules/` are the design record. Research cards under `docs/research/` are the evidence the portfolio chain may use. The NZ business cards in `docs/research/_archive/` are a frozen library, not the live program.

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

# on the Pi (tailnet HTTPS / MagicDNS enabled) — one-time; persists --bg:
tailscale serve --bg 8787
tailscale serve status          # expect proxy → 127.0.0.1; Funnel off
```

- Bind defaults to `127.0.0.1`; non-loopback hosts are refused.
- Observe chat works with mesh presence via Serve; Agent/Plan need session login.
- Vitals panes call the same organs as `ada body doctor`.
- Chat uses the same `harness.run_turn` / `runs/` JSONL as `ada chat` (one interactive writer at a time).

### Always-on HUD (ops)

Cursor/SSH foreground `ada hud serve` dies when the Mac sleeps or the session ends — **dev only**. Daily phone life capture needs the Pi process supervised:

```bash
sudo cp deploy/systemd/ada-hud.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now ada-hud.service
systemctl status ada-hud.service
```

- Unit pointer: `deploy/systemd/ada-hud.service` (same stack: `.venv`, `ADA_DATA_ROOT=/mnt/ada-data`, bind `127.0.0.1:8787`). Body historically named this `ada-agent.service` — **use `ada-hud`**; do not install both.
- After code pull / mouth changes: `sudo systemctl restart ada-hud.service` (stale process won’t load the new tree).
- Foreground debug: `sudo systemctl stop ada-hud.service` first (avoid two listeners on 8787).
- Logs: `journalctl -u ada-hud.service -f`
- Tailscale Serve is **not** inside the unit (already persists `--bg`).

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

## Portfolio chain

One run publishes one page on `github.com/aryanjohari/aryan-portfolio`. The operator file is `portfolio_chain.yaml` under the data root (`memory/facts/`). It stores the business once: site, audience, aim, places, offer, proof, contact, and actions. It also names the card folders. For this site those folders are `docs/research` and `docs/modules`. The operator does not write the title and does not keep a list of facts for the agent to refill.

The plan lists the markdown cards in those folders, skips a card already recorded in `published_pages.yaml`, and chooses one remaining card that has a passage. It opens at most three notes that teach that page, stores the passages, and writes the search title from those passages. Twelve stages run in order: bind site, understand aim, plan, external fetch, gather, gate, draft, librarian, diagram, critic, deliver, push. The HUD control is **Publish one page**. The chain does not search the web and does not append a fact.

## Tests

```bash
pytest -q
pytest -q tests/test_hud_*.py
ada tier-a check          # M18 Tier A kernel gate (+ receipt)
pytest -m tier_a -q       # same suite
```
