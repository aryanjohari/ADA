# M23 Friend mouth — Implement Plan

**Status:** plan only — **not METAL**  
**Date:** 2026-08-26  
**Authority:** [`docs/modules/M23_FRIEND_MOUTH.md`](../modules/M23_FRIEND_MOUTH.md) v1.0 (design lock — do not reopen)  
**Also read:** [`M05_VOICE_PERSONALITY_CONTROL.md`](../modules/M05_VOICE_PERSONALITY_CONTROL.md) · [`M19b_DAILY_SURFACE_VOICE.md`](../modules/M19b_DAILY_SURFACE_VOICE.md) · [`M20_V1_PRODUCT.md`](../modules/M20_V1_PRODUCT.md) · [`VOICE_REGISTER.md`](../VOICE_REGISTER.md) · [`VOICE_EXEMPLARS.md`](../VOICE_EXEMPLARS.md) · phone feel [`2026-08-26_phone_c369f86f.md`](./2026-08-26_phone_c369f86f.md) · [`2026-08-26_phone_96a74984_m22.md`](./2026-08-26_phone_96a74984_m22.md)

**Naming:** `docs/reviews/M23_IMPLEMENT_PLAN.md` matches M22/M19a implement-plan pattern — gap map + ordered slices; design lock stays under `docs/modules/`.

**Not this plan:** package · soul · second cortex · M22 store features · M21 bind rewrite · STT/TTS productize · M17 taste.

---

**Status:** shipped 2026-08-27 — register + mouth + templates + smokes METAL; phone re-smoke below.

## Phone re-smoke (operator)

1. Restart HUD: `ada hud serve --host 127.0.0.1 --port 8787` (+ Tailscale Serve if needed).
2. Log meal / lift / habit → ack has **no** `receipt_id`, not a roast essay.
3. Ambiguous food → Confirm **card** + warm stream line; Yes on card only.
4. Force a fail if easy → human error, no FK/CLI dump.

---

## One-liner

Make cortex + mouth share one **friend-talking** register: life acks result-first (roast off by default), Confirm/error templates human, no spoken `receipt_id` / SQL / CLI — keep numeric fail-closed and Confirm-on-ingress.

---

## Gap map (METAL vs NEW)

| Surface | METAL today | GAP / NEW | Touch | Falsifiers |
|---------|-------------|-----------|-------|------------|
| **Register contract** | [`VOICE_REGISTER.md`](../VOICE_REGISTER.md) + `load_register_contract()`; friend-first = social/about-me | Extend friend-first to **life-ack**; roast-off default on routine task; speech denylist line | docs + charter load (no new organ) | F-M23-1, F-M23-3 |
| **Exemplars** | [`VOICE_EXEMPLARS.md`](../VOICE_EXEMPLARS.md) social/lookup/challenge/chill | **2–4** original life-ack pairs + 1 error; anti-parrot | docs only | F-M23-4 |
| **Mouth rules** | [`mouth.py`](../../src/ada/harness/mouth.py) `MOUTH_RULES` — receipt JSON, numeric, no tools | Friend result-first; denylist; roast default off | `MOUTH_RULES` string | F-M23-1, F-M23-3, F-M23-6, F-M23-7 |
| **Confirm templates** | `_CONFIRM_LINE` / `_CONFIRM_FOOD` / `_CONFIRM_SPLIT`; mouth **skips** rewrite | Human specific copy; still no chat-Yes; HUD card unchanged | `mouth.py` constants + pack/spine speak strings that emit them | F-M23-5, F-M23-8 |
| **Pack `_speak_*` fail-closed** | Harness templates (HEAD `loop.py` / current harness home) | Same friend register when mouth guard fails | harness speak helpers | F-M23-8 |
| **Charter epistemics vs speech** | “cite `receipt_id`” for task-done | Split: receipts required in **runs/**; **don’t speak** id | [`charter.py`](../../src/ada/cortex/charter.py) | F-M23-3 |
| **Error speech** | Cortex narrates FK / CLI from tool error | Prefer pack/template human error; charter denylist for SQL/CLI | charter + any error templates | F-M23-2 |
| **Humor gate on life ack** | Capacity mid-high; live density too high on acks | Enforce intent table: task life-ack roast off unless invite | register + mouth | F-M23-1 |
| **Mouth wire** | `apply_register_pass` after pack fast-path (HEAD harness) | Keep wire through any harness refactor | harness `__init__` / turn loop | feel regression if unwired |

**Already locked (reuse):** numeric guard; Confirm on ingress; code binds ids; one Gemini cortex; M05 dials; M22 stores out of scope.

---

## OPEN defaults (from M23 — locked for implement)

| # | Lock |
|---|------|
| 1 | §4 capacity ≠ duty — runtime register wins; optional constitution amend later |
| 2 | Keep Confirm **skip** rewrite; humanize templates |
| 3 | Life-ack tease only if invite + `tease_ok` + not chilled; default off |
| 4 | Errors: one human line; no CLI dump |
| 5 | 2–4 life-ack exemplars + 1 error — no novel |

---

## Ordered implement slices

### Slice 1 — Register + exemplars + charter speech split  
**Scope:** S · docs + `charter.py` prompt lines  
**Acceptance:** social still friend-first; life-ack intent line present; no spoken-`receipt_id` instruction; smokes for denylist / anti-parrot still green or extended.

### Slice 2 — `MOUTH_RULES` + Confirm/error template copy  
**Scope:** S · `mouth.py` + harness Confirm/`_speak_*` strings  
**Acceptance:** Confirm spoken line warm+specific (F-M23-8); error human (F-M23-2); numeric guard unchanged (F-M23-6); mouth still tool-less (F-M23-7).

### Slice 3 — Smokes + phone re-smoke  
**Scope:** S · tests + short phone Agent pass  
**Acceptance:** sample acks have no `receipt_id` / FK / CLI; empty-gym ack not default roast; Confirm still ingress Yes only (F-M23-5).

**Do not start:** package, soul, second model, dry→wet, M17 rewrite, STT/TTS productize.

---

## Tests to add / extend (names only)

| Test idea | Asserts |
|-----------|---------|
| `test_m23_speech_denylist` (or extend mouth/charter eval) | Rewritten or template ack rejects `receipt_id`, `FOREIGN KEY`, `ada life` |
| Confirm template smoke | Template text lacks “no silent bind” tool-voice; still `needs_confirm` path |
| Life-ack humor | Fixture empty-gym receipt → output not forced-roast class (heuristic / banned phrases) |
| Existing `test_m20_voice_wedge` mouth guards | Still pass (numeric / HTML / tools) |

---

## Won’t-chase

Same as M23 card: package · wipe · mail · retrieval · P4 · food ML · second cortex · LoRA/soul · ear Confirm · Next · STT/TTS thesis · M17 · new stores · campaigns.

---

*End M23 implement plan. Execute against M23 design lock; no research reopen.*
