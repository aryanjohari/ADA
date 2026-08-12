# ADA (M00 — Body Sense)

Vitals, identity (birth once), and crash-safe lifecycle on the Pi. No Gemini, Dream, or HUD in this slice.

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

## CLI

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

## Tests

```bash
pytest -q
# optional manual smoke (uses a temp ADA_DATA_ROOT unless you export one)
bash scripts/smoke_body.sh
```

After a real birth on the HDD substrate you should see:

- `/mnt/ada-data/memory/facts/identity.yaml`
- `/mnt/ada-data/memory/lifecycle.jsonl`
