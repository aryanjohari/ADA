# M19c — Multi-face surfaces (pages over one Pi; chat ≠ base)

**Status:** **v1.6 research + implement fence** (2026-09-23) — life meal-draft still PHONE re-smoke OPEN. The Mac hunt panel and CV face are **removed**.  
**Date:** 2026-09-23  
**Host:** `ada-pi5` (Raspberry Pi 5, 8 GiB) · windows: phone / Mac / later display via **Tailscale Serve** (not Funnel)  
**Branch:** `rewrite/v1-body`  
**Kind:** Tier B **surface evolution** card — sibling of [`M19b_DAILY_SURFACE_VOICE.md`](./M19b_DAILY_SURFACE_VOICE.md); child of [`M19_TIER_B_LIFE_ADMIN.md`](./M19_TIER_B_LIFE_ADMIN.md)  
**Depends on:** [`M17_SURFACE_DESIGN.md`](./M17_SURFACE_DESIGN.md) (taste; **product-base SUPERSEDED** below) · [`M19b_DAILY_SURFACE_VOICE.md`](./M19b_DAILY_SURFACE_VOICE.md) (organism/organ/ingress/**face** ontology, device registry, `view_open`, Confirm-on-ingress — **cite, do not fork**) · [`M20b_PHONE_FACE.md`](./M20b_PHONE_FACE.md) / [`M20c_MAC_DISPLAY_FACE.md`](./M20c_MAC_DISPLAY_FACE.md) (chrome maps for shared HUD) · [`M15_INTENT_WORK_LOOP.md`](./M15_INTENT_WORK_LOOP.md) (Confirm Integrity) · [`M19a_P0_LIFE_CAPTURE.md`](./M19a_P0_LIFE_CAPTURE.md) + [`M26_DOMAIN_KNOWLEDGE.md`](./M26_DOMAIN_KNOWLEDGE.md) (life organs) · [`M26_FOOD_DOMAIN.md`](./M26_FOOD_DOMAIN.md) (meal draft / presets / barcode — live miss-path) · [`M28_WORK_LOOP_CASE_STUDIES.md`](./M28_WORK_LOOP_CASE_STUDIES.md) (hunt = Study B; **do not mix**) · [`../02_CONSTITUTION.md`](../02_CONSTITUTION.md) · [`../00_ASSISTANT_RESEARCH.md`](../00_ASSISTANT_RESEARCH.md) §8  

**Feeds:** thinner life **ingress chrome** (meal draft first — **#1 METAL pytest**) → phone capture face discipline → one organ **page** demo → later radar/diary lens. Does **not** reorder M20 1→5 package. Does **not** start wake-word, public DNS for PII, native apps, or Funnel. The hunt face is removed.

**Why a sibling (`M19c`), not an M19b v-bump / not M29 / not stuffed into M28·M26:**

| Option | Verdict |
|--------|---------|
| **M19b addendum** | M19b already owns voice wedge + face CSS on **chat-home**. It locks “chat owns viewport” (M17/M19b POLICY). This card **SUPERSEDES** chat-as-product-base. Burying that under a 1.2k-line voice card forces every implement chat to re-merge. |
| **M19b’s old reject of `M19c_FACES`** | That reject was about splitting **ontology** (device registry) from the skeleton. This card is a **different slice**: multi-*route* / multi-*window* product IA — pages as destinations, chat as fallback harness. |
| **Stuff into M20b/c** | Those lock **chrome** for one shared `index.html`. They do not own organ→page map, ingress-vs-chat model, or ephemeral access POLICY. |
| **Stuff into M26 / M28** | Life domains and hunt cases stay organs. Surfaces **point at** them; they do not become surface cards. |
| **Invent M29 for work** | **Refuse.** Hunt panel is a face over M28 metal — not a new work module. |

**Name stays `M19c_MULTI_FACE_SURFACES.md`:** the research object is **many faces over one Pi organism**, with chat demoted from product base to smoke/fallback. Not “more voice.” Not “dashboard home.”

### Changelog

| Ver | Date | Delta |
|-----|------|-------|
| **v1.6** | 2026-09-23 | **Work #4 Intake propose:** `POST /api/hunt/triage-propose` + face Propose→Confirm→CSV; FIT prod read; smoke write only. Card: the CV hunt face card (removed) v1.2. F-CV-face-7. No prod CSV / Next. |
| **v1.5** | 2026-09-23 | **Work #4 face IA METAL:** `/hunt` view tabs (Intake/Index/Watchlist/Pack/To apply/Applied); triage→CSV glue; Make pack Accept; Applied Confirm; piles on `/api/hunt/status`. Card: the CV hunt face card (removed) v1.1. Smoke: the hunt panel smoke (removed). No prod CSV / Next. |
| **v1.4** | 2026-09-23 | **Docs only:** CV hunt face IA — the CV hunt face card (removed) (Intake→Index→Watchlist→Pack→To apply→Applied; one smoke index; Accept + Applied Confirm). Stub chrome superseded by views; keep `hunt_*`. |
| **v1.3** | 2026-09-23 | **Work #4 METAL:** Mac hunt panel stub — `GET /hunt` + `/api/hunt/*` over M28 `hunt_*` (paste/fetch/triage/Accept/write_pack/csv/download/Applied Confirm). Smoke: the hunt panel smoke (removed). Life #1 phone re-smoke still OPEN. No latexmk / prod CSV / Next. |
| **v1.2** | 2026-09-23 | **Operator pack-up (docs only):** organs = software (own face I/O); chat = **launcher** (“open job hunt / log food”) + **thin chat-on-face** to roll the organ — not the place that owns every structured field. Life = personal research art; work/hunt/gateway = **demo / portfolio** track. Domain: Tailscale+session for PII; optional **public demo slice** only for non-PII agentic workflow (never diary/CV packs). Stop more CV metal until Mac hunt panel. OPEN inventory stamped. |
| **v1.1** | 2026-09-22 | **Implement-next #1 METAL:** stickiness + divert + start doors + null-energy refuse (v1.28) + **Confirm null-energy pick remap** (v1.29, cite phone `d99da535…` oats miss). Smoke: [`../reviews/M19c_MEAL_DRAFT_INGRESS_SMOKE.md`](../reviews/M19c_MEAL_DRAFT_INGRESS_SMOKE.md). **Remaining #1:** phone re-smoke until oats land in draft. **Found OPEN bound:** milk→oat milk; preset typo. Pointer: [`M26_FOOD_DOMAIN.md`](./M26_FOOD_DOMAIN.md) v1.29. |
| **v1.0** | 2026-09-21 | Operator lock pass: chat/HUD Agent = smoke harness, not destination; face matrix; ingress-first; organ→page map; Tailscale/session ephemeral access; character/radar later without schema fork; OPEN≤5; F-M19c-*; ordered implement-next. Docs only. |

---

## Core research question

**(Locked — v1.0. Do not replace.)**

How should ADA expose **many faces / windows** over **one Pi organism** so **life capture**, **organ pages** (food / gym / time / habits / people / dues), and **optional chat** work from phone and Mac — without treating chat as the product base, without dashboard soup, without a second cortex, and without mixing life (Study A) into hunt (Study B)?

Secondary (same card — defaults locked):

| Sub-question | Default until locked |
|--------------|----------------------|
| What is chat? | **Launcher + stuck-path harness + optional chat-on-face** — not the owner of every structured field |
| Where do organs live? | Each organ is **software-shaped**: own face (tabs/fields/buttons), own I/O contract, same gateway/tools underneath |
| Phone job? | **Life capture-first** (chips, presets, draft, barcode-as-option, timers); chat only when stuck / “open food” |
| Mac job? | **Heavier faces** — life week/simple + **hunt control panel** (M28) with fields + download + Applied |
| Access? | **Tailscale Serve + HUD session + device face registry** for personal organs. Optional **public demo subdomain** only for non-PII agentic workflow demos — never diary/CV packs |
| Life vs portfolio? | **Life = personal research art** (daily use, join later). **Work/hunt/gateway = demo track** (portfolio / agentic workflow show). Do not force life into a public product |
| Character / Assassin–polymath radar? | **Later lens** on honest logs — anti-Funnel / anti-XP-guilt. No schema fork |
| Wake-word → open a Mac face *set*? | **PARK** — not this card’s implement gate |

---

## §8 gate ([`00_ASSISTANT_RESEARCH.md`](../00_ASSISTANT_RESEARCH.md))

| Field | Answer |
|-------|--------|
| **Question / capability** | Multi-face product IA: pages + capture chrome over one Pi; chat demoted |
| **Lens tags** | **EVIDENCE** (personal informatics stages; multi-device continuity; PWA install; CARE dual-panel; Consent Integrity; Tailscale Serve≠Funnel) · **FEASIBLE** (extend ASGI routes + static templates; reuse packs/`view_open`/device registry) · **FANFICTION** (wake-word face-set; Iron Man multi-monitor OS; native apps as gate; public gamify site) · **POLICY** (no Funnel for PII; Confirm on ingress; life≠hunt; no second cortex; no LLM-authored HTML) · **METAL** (M19b faces/registry; M17 tokens; M15 Confirm; M26 organs; M28 paste-smoke) |
| **Citations** | ≥8 tagged rows in §Citations |
| **Pi 5 8GB** | **Yes** for thin HTML routes + receipt-bound templates + existing Gemini cortex. **No** as Next/React multi-app farm, native shells, or public Funnel diary |
| **Learning objective** | After this card: name face jobs per device; know chat is fallback not home; map each organ to receipt/`view_open` vs thin route; refuse Funnel/XP/schema fork; order implement-next without re-brainstorm |
| **Harder-but-correct** | **Extend** M19b registry + M17 static ASGI + Verb→Pack + Confirm. Pages bind receipts. **Shortcut rejected:** “chat better”; second cortex; dashboard soup; public subdomain; Funnel XP; LLM-drawn UI; life↔hunt join |
| **Won’t-chase (this slice)** | Wake-word · public DNS / Funnel diary · gamify UI · portfolio-post · Seek scrape · native apps · Next on Pi · life↔work join · camera barcode as gate · Assassin radar as gate |
| **Acceptance falsifiers** | F-M19c-* |
| **Egress** | **Control:** Tailscale Serve + HUD session (unchanged rings). **Cortex:** only when chat/Agent path used. **Organ pages:** prefer local receipt/API JSON — no new trust ring. Secrets never-to-cloud. **Public Funnel for diary/CV = fail** |

---

## Operator locks (encode — do not redesign organs)

1. Chat/HUD Agent was a **smoke harness**, not the final UX. **Pages / faces are the destination.**
2. **One Pi body**; many faces/windows. Windows are ephemeral; durable logs stay under `/mnt/ada-data`.
3. **Phone = life capture-first** (simple ingress); chat only when stuck on the go.
4. **Mac = different heavier faces** (life week/simple + later character radar; hunt control panel).
5. Organs surface as **simple web pages/demos** over existing tools/logs — **not a second brain.**
6. **Life ≠ work:** do not mix meal/gym into CV; hunt stays Study B ([`M28`](./M28_WORK_LOOP_CASE_STUDIES.md)); life stays M19a/M26.
7. **Privacy:** Tailscale / session first; **no naked public subdomain** for diary / CV packs.
8. **Gamify / character** (Assassin / polymath radar) = later **lens** on honest logs — anti-Funnel / anti-XP-guilt.
9. **Wake-word → open a Mac face set** = PARK later idea — **not** this card’s implement gate.
10. **Live audit (2026-09-21):** gym / time / habits feel strong; **meal draft / compose is buggy** — simpler life ingress must fix **draft / presets / barcode-as-option**, not “chat better.”
11. **v1.2 — Organ = software:** each organ has its own face (tabs/fields/buttons matching tool args). Structured input lives on the **face**, not guessed out of transcript prose.
12. **v1.2 — Chat roles (three only):** (a) **launcher** (“Ada, open job hunt / help me log food”) → opens the organ face; (b) **stuck-path / novel ask** on global harness; (c) **thin chat-on-face** to roll that organ while looking at its fields — still same `run_turn` / packs / Confirm.
13. **v1.2 — Two tracks:** **Life** = personal daily research (portfolio value optional / private). **Work** (hunt, gateway, CV workflow) = agentic demo / business portfolio track. Do not delay hunt face waiting to “finish life.”
14. **v1.2 — Apply unblock:** more CV metal (`latexmk`, critic-agent, prod CSV) **waits** until Mac hunt panel can enter JD, show pack, download `.tex`, mark Applied. Overleaf OK for PDF meanwhile.
15. **v1.2 — Public demo:** subdomain/page may demo **non-PII** agentic workflow (e.g. hunt *shape* with fake data). Personal life + real CV packs stay Tailscale+session (F-M19c-3/9).

**Map to metal (prefer extend/pointer):** M19b faces + device registry · M17 surface taste · M15 Confirm · M19a Verb→Pack · M26 domains · M28 hunt paste-smoke. **Do not fork** hunt/life organs in this slice.

---

## Ontology (keep M19b terms; add product-base)

| Term | Meaning here |
|------|----------------|
| **Organism** | Pi body: cortex + gateway + packs + logs under `/mnt/ada-data` |
| **Organ** | Life/work capability (food, gym, hunt, …) — truth in tools + disk; **behaves like software** (own face, I/O, stages) |
| **Face / window** | Device-shaped **view** into the organism (phone capture, Mac desk, organ page, hunt panel) |
| **Ingress** | Low-friction controls that write via packs (chips, presets, draft save, timers, barcode option, **form fields on organ face**) |
| **Chat harness** | Observe/Plan/Agent stream — **launcher + fallback**; optional **composer on organ face** |
| **Page** | Thin route or `view_open` panel bound to **receipt / API JSON** — not LLM HTML |
| **Ephemeral** | Browser tabs / PWA windows die; **logs + FACTS + campaigns** endure |

**SUPERSEDE (product base only):** M17 / M19b “chat owns the viewport / chat-home is the product.”  
**HOLD:** Confirm Integrity; one Gemini cortex; one Serve URL family; device registry; numbers never from model; taste tokens (M17 §10); life≠hunt.

```text
  BEFORE (smoke era)                 AFTER (this card)
  ┌─────────────────────┐            ┌──────────────────────────────┐
  │  Chat = home        │            │  Faces / pages = destinations│
  │  Panels = side slot │     →      │  Ingress = daily verbs       │
  │  Body = depth       │            │  Chat = launch + roll face   │
  └─────────────────────┘            └──────────────────────────────┘
         same Pi · same packs · same Confirm · same receipts
```

---

## A0 — Organ as software (v1.2 lock)

Laptop software has a window, menus, fields, and sometimes a helper chat. ADA organs should feel the same — **not** “everything is a chat message.”

| Layer | Owns | Does not own |
|-------|------|--------------|
| **Organ face** | Tabs / fields / buttons matching backend tool args (qty, pack_id, JD paste, Applied Confirm) | A second cortex or reimplemented pack logic |
| **Chat launcher** | “Open life / open job hunt / help me log food” → navigates to face | Filling every structured field from prose forever |
| **Chat-on-face** | Roll *this* organ while seeing its state (“bump expect”, “rewrite cover more junior”) | Becoming a parallel product home |
| **Harness underneath** | One `run_turn` · Verb→Pack · gateway · Confirm · receipts · campaign STATUS | Per-organ agent runtimes |

**Failure mode we are leaving:** stuffing every organ’s I/O back into one transcript → ambiguous routing, endless Confirm guesses, no download/apply path for CV.

**Life vs work tracks (parallel, not sequenced):**

| Track | Purpose | Demo / portfolio? | Face priority |
|-------|---------|-------------------|---------------|
| **Life (Study A)** | Personal capture + later join research | Private / research art — not required as public product | Phone meal-draft ingress → capture chrome → food page |
| **Work (Study B)** | Campaign loop / later portfolio post | Private until a non-PII demo exists | Not the hunt organ — that case is removed |

---

## A — Face matrix

| Face | Primary job | Chrome budget | OUT on this face |
|------|-------------|---------------|------------------|
| **Phone — capture** | Log meal / gym set / time block / habit tick in ≤ few taps | Sticky ingress; Confirm cards; one-line ack; optional mic→composer | Plan cards; Body theater; week boards; hunt panel; dashboard soup; chat-as-home |
| **Phone — stuck chat** | Clarify / multi-intent / recover when chips fail | Thin stream + Confirm; Ask/Agent only (M20b) | Becoming the daily open; tool-card NOC |
| **Mac — life desk** | Week/simple glance + Body depth + capture when at desk | Stream **available**; one panel/page slot; Body 1 click | Ops NOC; orb-only hide Confirm |
| **Mac — radar (later)** | Character / polymath lens on **honest** logs | Read-only overlays; no XP guilt meters | Schema fork; Funnel public scoreboard; inventing stats without receipts |
| **Display (later)** | Panels-first glance (M20c) | Slot owns height; no composer | Ingress; Confirm-by-speech; chat home |
| **Organ page (any device)** | One organ as software: read + write affordances + optional composer | Hairline chrome; receipt-bound numbers | Second cortex; LLM layout; mixing domains on one page |

**Rule:** each face has **one job**. Chat may **launch** or **roll** it; chat must not **replace** its structured I/O.

---

## B — Ingress model (face fields + chat roles)

| Mode | When | Mechanism | Fail closed |
|------|------|-----------|-------------|
| **Primary ingress** | Daily / hunt verbs known | Face fields · chips · presets · draft · barcode option · timers · habit ticks · Applied Confirm | No write without pack receipt / Confirm when required |
| **Chat launcher** | “Open X” / “help me log food” / “open job hunt” | Navigate / `view_open` / face route — then operator uses face fields | Launcher that never opens a face (stays stuck in transcript) |
| **Chat-on-face** | Rolling the open organ (rewrite cover, bump score, ask “what’s waiting”) | Same `run_turn` scoped to organ context + visible state | Replacing face fields with prose-only I/O |
| **Chat fallback** | Stuck, multi-intent, novel ask, recover | Global harness → Verb→Pack → Confirm | Chat claim without receipt = fail (F-M19c-1) |
| **Voice** | Transport only (M19b / M20a) | STT fills composer → operator Send | Auto-send; ear-only Confirm |

**Live miss-path lock (operator #10):** meal **draft / compose** is the first *life* coding target. Fix the **ingress surface** that drives `meal_draft_*` / presets / barcode-option — do **not** “make Agent chat better at meals.”

The hunt face and CV backend are removed.

**Personal-informatics (EVIDENCE):** collection-stage friction kills later reflection ([Li, Dey, Forlizzi — stage model](https://doi.org/10.1145/1753326.1753409)). Winners ship **one capture verb → durable row → glance → drill-down**, not conversation as the log.

---

## C — Organ → page map

Prefer **reuse** receipt + `view_open` / existing APIs. Add **thin routes** only when a face needs a bookmarkable destination without opening chat-home.

| Organ | Truth (METAL pointer) | Surface now | Target face / page | Reuse vs new |
|-------|----------------------|-------------|--------------------|--------------|
| **Food / nutrition** | M26 food · `life_meal_*` · `meal_draft.py` · `nutrition_day` | Chat + chips + `view_open` `nutrition_day` | Phone capture chrome; Mac panel; later `/life/food` thin page | **Reuse** receipt/`GET /api/life/day`; **extend** ingress UI; thin route only after ingress smoke |
| **Gym** | M26 gym · strong capture | Chat / status packs | Phone sets ingress; Mac `gym_day` panel | **Reuse** receipt pattern (`gym_day` registry — M19b design) |
| **Time** | M26 time · closed capture | Chat / status | Phone timer chips; Mac glance | **Reuse** `time_status` |
| **Habits** | M26 habits · closed | Chat / ticks | Phone tick chips; Mac sheet | **Reuse** habit receipts |
| **People** | M26 people · phone jsonl next | Chat | Phone note ingress; Mac card | **Reuse** packs; no CRM board home |
| **Dues** | M26 dues · closed | Today strip / chat | Mac/phone due chip → Confirm | **Reuse** Today + Confirm |
| **Life radar (later)** | Honest logs + FACTS | ABSENT as UI | Mac read-only lens | **No schema fork** — aggregate existing rows |
| **Chat harness** | M14/M15 HUD | `/` `index.html` | All devices as **fallback** | **Keep** one HTML; demote as default open where face registry allows |

**Stack lock:** Python ASGI + static (M14). `routes_pages.py` = **`GET /`** — further organ routes stay **additive**, not a framework rewrite.

**Receipt bind (POLICY):** every panel/page number must appear in receipt JSON or documented API payload. Model does not emit HTML/CSS (M19b F-M19b-8/11 family → F-M19c-6).

---

## D — Ephemeral access model (“from anywhere”)

| Layer | Role | Not |
|-------|------|-----|
| **Tailscale Serve** | Control-plane reach to Pi HUD from Aryan devices; identity headers available | **Funnel** / public `*.ts.net` for diary or CV packs |
| **HUD session** | Plan/Agent writes; Confirm path | Collapsing ACL + password + device name into one “login” |
| **Device face registry** | `ada_hud_device` + `facts/hud_devices.yaml` + `data-face` / `?face=` (M19b METAL) | Permission ladder; analytics of which device “wins” |
| **PWA / bookmark** | Installable window per face (manifest already `display: standalone`) | Native App Store shell as gate |
| **Durable substrate** | `/mnt/ada-data` logs, FACTS, campaigns, hunt tree | Browser localStorage as SoT |

**“From anywhere” means:** any **tailnet-enrolled** phone/Mac with session can open a face. It does **not** mean public internet for diary/CV.

**Public demo carve-out (v1.2):** a **subdomain / marketing page** may host a **sanitized agentic workflow demo** (fake JD, fake receipts, no real CV/life PII). Real organs stay Serve+session. Funnel diary / real packs = fail (F-M19c-3).

**Privacy (POLICY + EVIDENCE):** Serve keeps identity headers; Funnel does not ([Tailscale Serve](https://tailscale.com/docs/features/tailscale-serve) vs [Funnel](https://tailscale.com/docs/features/tailscale-funnel)). Intimate assistant data + high permission → minimize accidental exposure ([Agents That Know Too Much](https://arxiv.org/html/2606.26627)).

---

## E — Character / radar + diary notes (later — no schema fork)

| Later idea | How it plugs in | Forbidden |
|------------|-----------------|-----------|
| **Assassin / polymath radar** | Read-only **lens** aggregating existing gym/time/habit/food/work receipts into a Mac face | XP guilt meters; Funnel public scoreboard; inventing dimensions without logs |
| **Diary notes** | Same life note / people note packs + optional free-text log rows already in domain design | Parallel “journal cortex”; mixing into hunt packs |
| **Wake-word → Mac face set** | PARK — local wake opens bookmarks / Serve URLs later | Implement gate on this card |

**Schema rule:** new faces may add **templates and routes**. They do **not** add a second memory dialect, a second campaign schema, or a Funnel-facing gamify store.

---

## Honest METAL vs ABSENT (2026-09-21)

| Piece | Truth | Tag |
|-------|--------|-----|
| One ASGI HUD `GET /` + `data-face=phone\|mac\|display` | **METAL** — M19b / M20b / M20c | **METAL** |
| Device cookie + `hud_devices.yaml` + provenance stamp | **METAL** | **METAL** |
| `view_open` + `nutrition_day` template | **METAL** | **METAL** |
| Confirm gateway-rendered args | **METAL** — M15 | **METAL** |
| Life packs (food/gym/time/habits/dues) | **METAL** — M26 (people still open phone jsonl) | **METAL** |
| Meal draft / presets / barcode chip path | **In-tree**; operator live: **compose/draft buggy**; barcode write still OPEN (M26) | **METAL** + **ABSENT** polish |
| Chat as product home | **METAL** default open — **POLICY SUPERSEDED** as destination | **SUPERSEDE** |
| Thin organ routes (`/life/food`, …) | **ABSENT** — `routes_pages.py` = `/` + `/hunt` (food page still ABSENT) | **ABSENT** (food) / **METAL** (hunt) |
| Mac life desk | Chat + panels | **METAL** pattern |
| Character radar UI | **ABSENT** | **ABSENT** |
| Wake-word face-set | **ABSENT** / PARK | **FANFICTION** this slice |
| Public Funnel diary | **Must stay ABSENT** | **POLICY** |

---

## OPEN inventory (pack-up 2026-09-23 — not a coding queue)

| Track | OPEN now | Default / note |
|-------|----------|----------------|
| **Life — food** | PHONE re-smoke compose→preset after v1.28/v1.29; #5 barcode write; #6 estimate; vocative #4 | Don’t reopen ranking; meal-draft face first (F-M19c-1/10) |
| **Life — people** | Phone jsonl after food re-smoke | Organ not CLOSED |
| **Life — join** | Later | Not a face gate |
| **Surfaces** | Thin food organ route ABSENT; chat still default open | Capture chrome → food page |
| **Hunt / CV** | Face IA **METAL** (Intake→…→Applied); latexmk later; prod CSV refuse; cover edit-on-face | Views shipped; more CV metal still waits (lock #14) |
| **Demo** | Public non-PII workflow page ABSENT | Optional later; not diary/CV |

## OPEN (≤5) with defaults

| # | Question | Default until overturned |
|---|----------|--------------------------|
| 1 | First thin organ **route** vs deepen `view_open` only? | **Ingress chrome first**; first bookmarkable route = **one** organ page after meal-draft ingress smoke (food), still receipt-bound |
| 2 | Phone default open = capture chrome or shared chat URL + CSS? | **Capture-first chrome** on `data-face=phone` (extend M20b); chat remains one tap away — not removed |
| 3 | Hunt panel = slot inside Mac desk or separate `?face=` / path? | **Separate Mac face or path** (`hunt` / `?face=hunt`) so life desk stays clean (F-M19c-5) |
| 4 | Parallel tracks: finish life before hunt face? | **No** — life + hunt faces proceed in parallel; hunt panel unblocks apply (lock #13–14) |
| 5 | Public subdomain for ADA demos? | **Non-PII workflow demo only**; personal life + real CV packs stay Tailscale+session |

---

## Falsifiers

| ID | Fail if… |
|----|----------|
| **F-M19c-1** | Daily meal (or gym set) **requires chat prose** as the only working path when chips/draft/preset should suffice |
| **F-M19c-2** | A **second cortex** / parallel agent runtime appears for “page brain” |
| **F-M19c-3** | **Funnel** or naked public subdomain serves diary / CV packs / life PII |
| **F-M19c-4** | **XP / streak-guilt / public gamify** becomes the motivation layer |
| **F-M19c-5** | Life meal/gym UI and hunt CV UI **share one mixed home** or one write path |
| **F-M19c-6** | Panel/page shows numbers **not** in receipt / API JSON (LLM-hallucinated UI) |
| **F-M19c-7** | Organ page **reimplements** pack logic instead of calling existing tools |
| **F-M19c-8** | Wake-word or native app becomes a **gate** for capture or hunt panel |
| **F-M19c-9** | “From anywhere” is implemented as **public DNS** instead of Tailscale + session |
| **F-M19c-10** | Implement chat “fixes meals” by **prompting Agent harder** instead of draft/preset/barcode ingress |
| **F-M19c-11** | Organ structured I/O stays **transcript-only** when a face with fields should exist (esp. hunt apply path) |
| **F-M19c-12** | Life PII or real CV packs shipped on a **public** subdomain “for portfolio” |

---

## Locks

| Lock | Source |
|------|--------|
| Pages/faces = destination; chat = harness/fallback | **v1.0** operator |
| One Pi organism; ephemeral windows; durable `/mnt/ada-data` | **v1.0** |
| Phone = capture-first; Mac = heavier + hunt panel | **v1.0** |
| Extend M19b/M17/M15/M26/M28 — no organ fork | **v1.0** |
| Life ≠ hunt (Study A / B) | M28 · **v1.0** |
| Tailscale Serve + session; no Funnel PII | **POLICY** · **v1.0** |
| Confirm on ingress window; receipt-bound UI | M15 · M19b · **v1.0** |
| Character/radar later; no schema fork; anti-XP | **v1.0** |
| Wake-word PARK | **v1.0** |
| Meal-draft ingress before organ-page tourism | **v1.0** (#10) |
| No M29; no stuffing into M28/M26 | **v1.0** |
| Organ = software face; chat = launch + roll | **v1.2** |
| Life research ∥ work demo tracks; hunt panel before more CV metal | **v1.2** |
| Public demo = non-PII only | **v1.2** |

---

## Ordered implement-next (thin — stop early)

Docs pack-up this chat. Coding chats follow this order:

### Life track
1. **Meal-draft ingress fix** — compose / draft save / presets / barcode-as-option on phone capture chrome (M26 paths; F-M19c-1/10). **METAL pytest 2026-09-22** · **PHONE re-smoke OPEN** (checklist [`../reviews/M19c_MEAL_DRAFT_INGRESS_SMOKE.md`](../reviews/M19c_MEAL_DRAFT_INGRESS_SMOKE.md)).
2. **Phone capture chrome discipline** — capture-first layout; chat one gesture away (extend M20b; do not native-app).
3. **One organ page** — bookmarkable thin route or hardened `view_open` for **food day** (receipt-bound; F-M19c-6/7).

### Work / demo track
The CV hunt panel is removed. A public non-PII workflow demo is optional and later. It is not a CV pack.

### Stop before
Wake-word · Funnel diary · gamify/radar UI · portfolio-post · life↔work join · Next/React · native shells · camera-barcode-as-gate.

---

## Won’t-chase

Wake-word face-set · public gamify site · Assassin radar as v1 · Funnel diary · portfolio-post · Seek/LinkedIn scrape · native iOS/Mac apps · Next on Pi · second cortex · dashboard-home soup · life↔hunt join · XP/streak guilt · LLM HTML layout · reinstall-to-add-a-face.

---

## Citations (≥8) + internal METAL

| # | Citation | Relevance | Tag |
|---|----------|-----------|-----|
| 1 | [Li, Dey, Forlizzi — Personal informatics stages (CHI 2010)](https://doi.org/10.1145/1753326.1753409) | Collection friction cascades; design capture before reflection theater | **EVIDENCE** |
| 2 | [Consent Integrity / LITL (Weng 2026)](https://arxiv.org/html/2606.02668v1) | Confirm shows gateway args; pages must not paraphrase risk away | **EVIDENCE** / **POLICY** |
| 3 | [Agents That Know Too Much (2026)](https://arxiv.org/html/2606.26627) | Intimate logs + high permission → Tailscale/session, not public | **EVIDENCE** |
| 4 | [CARE: Collaborative UI (2024)](https://arxiv.org/html/2410.24032) | Chat for stuck input; structured panel for output — maps to harness vs page | **EVIDENCE** |
| 5 | [Horizon Gap survey (2026)](https://arxiv.org/html/2608.06663) | Externalize state in logs/FACTS — pages read disk, not chat hope | **EVIDENCE** |
| 6 | [Long-Horizon Task Mirage (2026)](https://arxiv.org/html/2604.11978v1) | “Logged” without receipt = mirage — falsify panels against tool rows | **EVIDENCE** |
| 7 | [Tailscale Serve](https://tailscale.com/docs/features/tailscale-serve) · [Funnel](https://tailscale.com/docs/features/tailscale-funnel) | Serve = tailnet + identity headers; Funnel = public, no identity — diary must not Funnel | **EVIDENCE** / **POLICY** |
| 8 | [PWA 2026 guide — manifest / install / offline honesty](https://www.digitalapplied.com/blog/progressive-web-apps-2026-complete-development-guide) | Installable faces OK; start_url/icons later; not a native-app gate | **EVIDENCE** / **FEASIBLE** |
| 9 | Cross-platform continuity (same data, different interaction density) — e.g. [Fuselab multi-device UX](https://fuselabcreative.com/ui-ux-design-trends-2026-modern-ui-trends-ux-trends-guide/) | Phone capture ≠ Mac hunt panel; continuity of packs, not identical chrome | **EVIDENCE** |
| 10 | Progressive disclosure — [UX Tigers 2026](https://www.uxtigers.com/post/progressive-disclosure) | Outcome + Confirm at level 1; full trace in drawer — anti-dashboard soup | **EVIDENCE** |

**Internal METAL pointers:** M19b faces/registry/`view_open` · M17 tokens · M20b/c chrome · M15 Confirm · M19a Verb→Pack · M26 domain docs · M28 hunt paste-smoke · `routes_pages.py` (`/` only) · `meal_draft.py` / food spines · constitution Confirm Integrity / no Funnel.

---

## Relationship to other cards

| Card | Owns | Boundary with M19c |
|------|------|-------------------|
| **M19b** | Face ontology, voice transport, registry, `nutrition_day` | **Cite.** Product-base chat-home **SUPERSEDED** here. Voice wedge stays M19b |
| **M17** | Taste / density tokens | **Cite.** Chat-first **destination** SUPERSEDED; tokens HOLD |
| **M20b/c** | Phone/Mac/display chrome maps | **Extend** for capture-first; do not rewrite taste |
| **M26 / M19a** | Life organs | Surfaces **call** them; no domain rewrite in surface chats except miss-path ingress |
| **M28** | Hunt Study B | Hunt **panel** is a face over M28 — not M29, not life |
| **M15** | Confirm / modes | Unchanged permission gates |
| **M14** | ASGI + static shell | Thin routes additive |

---

## Implement-next seed (for coding chat)

When OPEN defaults stand:

1. **Life #1 — meal draft phone re-smoke** then capture chrome (F-M19c-1/10).
2. Do **not** in those chats: wake-word, Funnel diary, radar, portfolio-post, stuffing life onto a public subdomain. The hunt panel is removed.

---

*End M19c v1.5 — organs as software faces; CV hunt face IA METAL (views + HITL).*