# Tier A close — manual smoke checklist + sign-off (M18 §5.3)

**Automated gate (required):** `ada tier-a check` or `pytest -m tier_a`  
**This file:** operator signs after ≤15 min HUD/manual smokes. Do **not** stamp CLOSED until both automated + this checklist PASS.

| Field | Value |
|-------|-------|
| Date | |
| Operator | |
| Host / HUD | |
| Automated gate | PASS / FAIL |
| Manual checklist | PASS / FAIL / PARTIAL |
| Overall | (blank until signed) |
| Notes | |

---

## Manual smoke (≤15 min, Mac over Tailscale)

| # | Step | Pass |
|---|------|------|
| 1 | Open HUD via Serve / `ada-open-mac` | Chat-home, not Funnel URL |
| 2 | Observe: ask Pi temp/RAM | Numbers from tool; no invent |
| 3 | Plan: multi-step ask → Plan card → Accept | Todos appear; no silent FACT overwrite |
| 4 | Agent: trigger Confirm (e.g. notify enable or FACT overwrite) | Card shows real `{tool,args}` |
| 5 | Deny Confirm once | No side effect |
| 6 | Allowlisted fetch → cite → `artifact_write` | Path + Shelf list |
| 7 | Upsert todo with `next_wake_at` | Error / fail-closed |
| 8 | Upsert `remind_at` | OK |
| 9 | Body drawer → vitals + shelf | 1 click |
| 10 | Mute / quiet honored if notify tested | Skip or honest skip receipt |

Mark each row ✓ / ✗ / skip when run. HUD Confirm/Plan Accept browser E2E remains manual (no Playwright in gate).

## Sign-off

```text
I ran the automated tier_a gate and the manual rows above on the date listed.
Automated: ____   Manual: ____   Overall (CLOSE / STAY_A): ____
Signature / initials: ____________
```

After **PASS**: freeze Tier A surface; open M19 Tier B research. Habit seeding / live ntfy arming are **not** required.
