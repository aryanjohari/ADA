# M28 — HUD smoke: cv-draft-1 paste-JD (smoke hunt root)

**Date:** 2026-09-20  
**Parent:** [`M28_WORK_LOOP_CASE_STUDIES.md`](../modules/M28_WORK_LOOP_CASE_STUDIES.md) §B.1  
**Host:** `ada-pi5` · branch `rewrite/v1-body`  
**HUNT_ROOT:** `/mnt/ada-data/hunt/nz-cv-job-hunt-smoke` (FACT `memory/facts/work_hunt.yaml`)  
**Prod:** `/mnt/ada-data/hunt/nz-cv-job-hunt` — **READ-ONLY** this slice (no CSV / pack writes)

Automated: `pytest tests/test_m28_cv_draft_paste_smoke.py -q`

---

## Preconditions

1. Restart HUD after pull so tools load:

```bash
pid=$(ss -ltnp 'sport = :8787' | sed -n 's/.*pid=\([0-9]*\).*/\1/p' | head -1)
[ -n "$pid" ] && kill "$pid"
ada hud serve --host 127.0.0.1 --port 8787
```

2. Confirm FACT points at smoke:

```bash
grep hunt_root /mnt/ada-data/memory/facts/work_hunt.yaml
# expect: .../nz-cv-job-hunt-smoke
```

3. Optional override: `export ADA_HUNT_ROOT=/mnt/ada-data/hunt/nz-cv-job-hunt-smoke`

---

## Live HUD checklist

| # | Mode | Say / do | Pass |
|---|------|----------|------|
| 1 | Agent | “Ensure cv-draft-1 and load hunt guidelines” | `hunt_ensure_campaign` + `hunt_guidelines_load`; campaign id `cv-draft-1` |
| 2 | Agent | Paste a **full** JD body; ask to store as pack `2026-09-smoke-acme-se` (company/role named) | `hunt_paste_jd` → `applications/_inbox/…/jd.md` under **smoke** only |
| 3 | Agent | Score `role_fit` + `expect`; propose **apply** | `hunt_triage_record` decision=apply; no pack yet |
| 4 | Plan | Short plan: “Accept apply → tailored pack → you send” | Plan card with steps |
| 5 | — | **Accept** with `campaign_id=cv-draft-1` | Todos + `plan_id` pinned on campaign |
| 6 | Agent | “Write the tailored pack (accepted)” | `hunt_write_pack(accepted=true)` → `applications/<id>/{cv,cover,jd}.tex`; STATUS=`waiting_on_aryan`; stage=`you_send` |
| 7 | — | Restart HUD / new session; ask “where is cv-draft-1?” | STATUS + `plan_id` + pack path from disk (F-M28-8) |
| 8 | Agent + Confirm | Type `sent to Acme via careers on 2026-09-20`; upsert campaign `done` | Confirm + operator-typed receipt (F-M28-7); **never** auto-Applied |

### Negative checks

| # | Do | Pass |
|---|----|------|
| N1 | Triage `skip` or `hold`, then try pack write | Denied; no `applications/<id>/` (F-M28-11) |
| N2 | Pack write with `accepted=false` or before Accept | Denied |
| N3 | Inspect prod `nz-cv-job-hunt/applications/index.csv` | Unchanged line count / mtime |

---

## Stop before

Fetch-from-URL product · prod CSV helpers · latexmk gate · guideline edits · portfolio-post · LinkedIn/Seek scrape · M29 · life packs · main S3/ISR.
