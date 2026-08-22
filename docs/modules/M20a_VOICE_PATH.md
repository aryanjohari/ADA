# M20a — Voice path (research · pick)

**Status:** design lock only — **no implement this card**  
**Date:** 2026-08-20 (v1.1)  
**Host:** `ada-pi5` (Raspberry Pi 5, 8 GiB) · windows: Mac / phone via Tailscale Serve  
**Branch:** `rewrite/v1-body`  
**Kind:** M20 phase-1 **child** — cheap STT/TTS path pick. Not a taste rewrite. Not a second cortex. Not a voice-vendor thesis that ends in “just call Deepgram.”  
**Depends on:** [`M20_V1_PRODUCT.md`](./M20_V1_PRODUCT.md) (sequence; this card **is** phase 1) · [`M19b_DAILY_SURFACE_VOICE.md`](./M19b_DAILY_SURFACE_VOICE.md) **v1.6 / v1.6.1** (wedge UX: PTT preview-then-Send; register-pass mouth; faces) · [`M14_AGENT_SURFACE.md`](./M14_AGENT_SURFACE.md) (B-voice; stack lock) · [`M05_VOICE_PERSONALITY_CONTROL.md`](./M05_VOICE_PERSONALITY_CONTROL.md) (register, not soul) · [`../02_CONSTITUTION.md`](../02_CONSTITUTION.md) · [`../00_ASSISTANT_RESEARCH.md`](../00_ASSISTANT_RESEARCH.md) §8 / §4 (local LLM **ancillary**, not main cortex) · [`../19_JARVIS_JUSTINE_AGENT_RESEARCH.md`](../19_JARVIS_JUSTINE_AGENT_RESEARCH.md) (voice = channel, not omniscience)

**Name stays `M20a_VOICE_PATH.md`:** M19b already owns faces / preview-Send / mouth POLICY. M05 already owns register. This card only answers M20 OPEN #1 — **which STT/TTS path**, on this metal, without making ADA a list of Pi scripts that call another vendor.

**Supersedes:** M20’s *default until research* of “cloud STT + cloud TTS.” M19b OPEN “TTS = cloud; STT = Mac browser first.” M14’s “Pi stays text API; Mac hosts STT/TTS CPU.” **Does not supersede:** M20’s PARK of **local full-loop STT+LLM+TTS**; PTT simplex; preview-then-Send; Gemini-as-cortex; register-pass mouth; Confirm on screen.

### Changelog

| Ver | Date | Delta |
|-----|------|-------|
| **v1.1** | 2026-08-20 | Pointer: HUD **gesture** is M20b — phone **tap-to-toggle**, Mac hold. Path unchanged (MediaRecorder blob → Pi STT). Phone may send `audio/mp4`. |
| **v1.0** | 2026-08-19 | Domain map + SOTA + market + option matrix. **Pick:** Pi-owned cascade organs (local STT + local TTS) + existing Gemini cortex. No extra speech vendor. No trained proprietary speech model. No Gemini Live. |

---

## One-liner

Voice is an **ADA organ**, not a subscription. Mic and speaker stay on the window (Mac/phone). **STT and TTS run on the Pi** from open weights ADA hosts. **Gemini stays the cortex** (and the register-pass mouth). A later tiny **local router** can sit in front of Gemini for cheap intent — that is the proprietary piece, not a from-scratch speech model, and not a second cloud brain.

---

## Core research question

On a Pi 5 8GB organism whose cortex is already Gemini, how do we add Tier-B PTT so ADA is **not** “HUD scripts calling another API,” without (a) a second speech vendor, (b) a local full LLM loop that is too slow, or (c) Gemini Live as a parallel brain that bypasses `run_turn` / Confirm / receipts?

Secondary lenses:

| Sub-question | Where answered |
|--------------|----------------|
| What even exists in the 2025–26 voice domain? | §A domain map |
| What are the SOTA papers actually arguing? | §B |
| What unique pipelines shipped? | §C |
| What do market tools sell, and who are they for? | §D |
| Options on *this* metal + code | §E |
| Train a model vs own a pipeline | §F |
| The pick, and why | §G / exec summary |

---

## Scope fence

| IN (this card) | OUT (explicit) |
|----------------|----------------|
| Pick **one** STT/TTS path for M20 phase 2 wedge | Building PTT / mic UI / register-pass code |
| Honest Pi 5 8GB RAM/latency | Treating 8–25s **STT+local-LLM+TTS** benches as the STT+TTS number |
| Cascade vs speech-to-speech vs vendor Live | GPT-Live / Gemini Live duplex as v1 |
| Open-weight models ADA **hosts** vs extra cloud speech APIs | Fine-tune Whisper / Piper / LoRA-as-soul |
| Later local **router** (ancillary) vs Gemini analysis | Replacing Gemini cortex with Phi/Gemma on Pi |
| Audio trust-ring honesty | Always-listen, wake-word product, speaker-ID authority (Tier C) |

**Stack lock (reaffirm):** Python ASGI + static HUD. Voice endpoints are extra FastAPI routes on the same HUD process (or a tiny sibling service ADA owns) — **not** Pipecat, **not** LiveKit, **not** Next.

---

## §8 gate fields ([`00_ASSISTANT_RESEARCH.md`](../00_ASSISTANT_RESEARCH.md))

| Field | Answer |
|-------|--------|
| **Question / capability** | Cheap, organism-owned STT/TTS path for the M19b PTT wedge on Pi 5 8GB, with Gemini remaining the only cortex |
| **Lens tags** | **EVIDENCE** (cascade vs S2S papers; Pi Whisper/Piper benches; HA Wyoming shape) · **FEASIBLE** (STT+TTS without a local LLM fits 8GB; PTT is bursty) · **FANFICTION** (train ADA’s own ASR; Moshi/GPT-Live on Pi; movie duplex) · **POLICY** (one cortex; audio must not tool; Confirm on screen; no extra speech vendor as default) · **METAL** (no mic/STT/TTS today; `input=typed`; `_speak_*` templates; Gemini `2.5-flash`) |
| **Citations** | §B ≥8; market §D; Pi benches in §E |
| **Pi 5 8GB feasibility** | **Local STT + local TTS, Gemini still cloud:** **yes** — this is the 4GB-class subset of community stacks (STT+TTS, no local LLM). **Local STT+LLM+TTS as daily driver:** **no** (8–25s E2E; contends with HUD; weak tools). **Gemini Live / GPT-Live on Pi:** **no** (wrong architecture, not a RAM issue) |
| **Learning objective** | After this card, operator can order the phase-2 implement chat (PTT → Pi STT → composer → Send → `run_turn` → register pass → Pi TTS) **without re-opening** cloud-vendor vs local, or “should we train a voice model” |
| **Harder-but-correct vs shortcut** | **Correct:** ADA hosts Whisper-class STT + Piper TTS as organs; same `run_turn`; transcript is composer text. **Shortcut rejected:** Deepgram+ElevenLabs “because it’s easy”; Gemini Live “because cortex is already Google”; browser-only STT that ADA does not own |
| **Won’t-chase (this slice)** | Train/fine-tune ASR or TTS · Moshi/Qwen-Omni on Pi · Pipecat/LiveKit transplant · Vapi/Retell · Kokoro as default (too slow on Pi CPU) · WebRTC duplex · wake-word as product · iOS Speech as the organ |
| **Acceptance falsifiers** | F-M20a-* in §H |
| **Egress impact** | **Control plane:** audio blob Mac/phone → Pi over Tailscale (already the HUD ring). **New cloud speech ring: none.** **Cortex ring:** unchanged — Gemini still sees **text** (transcript + register-pass JSON), never the wav. Backup ring untouched |

---

## Executive summary — the pick

**Do this:** **Pi-owned cascade.**

```text
window (Mac / phone)
  MediaRecorder (PTT)  ──audio blob──►  Pi STT organ (faster-whisper tiny.en / base.en)
  composer preview     ◄──transcript──  operator READS, then Send
  POST /api/chat { message, input: stt, face, device_id }
                         │
                         ▼
                   existing run_turn
                   fast-path tools · Confirm on screen
                   Gemini register-pass mouth (receipt JSON only)
                         │
  Web Audio playback   ◄──wav/opus──  Pi TTS organ (Piper lessac-medium)
```

| Keep | Drop |
|------|------|
| Gemini as **only** cortex | Extra STT/TTS vendor (Deepgram, Whisper API, ElevenLabs, Cartesia, Gemini Live) |
| M19b preview-then-Send, simplex, Confirm on screen | Auto-send, ear-only Confirm, duplex |
| Fast-path tools + fail-closed `_speak_*` | Local Phi/Gemma as the voice brain |
| Open weights ADA **hosts** (Whisper-class + Piper) | Training a proprietary speech model for v1 |
| Later: tiny **local router** in front of Gemini | Replacing Gemini for analysis / mouth |

**Why this is the organism move:** cortex is already one cloud ring (Gemini). Adding a speech vendor makes ADA *more* of an API collage. Hosting STT/TTS on the Pi makes voice an **organ** the same way packs, FACTS, and the gateway are organs. The 8–25s horror number in M19b/doc-00 is **STT + local LLM + TTS**. Once Gemini stays the LLM, community Pi 5 numbers collapse to ~1–3s STT + ~0.3–0.8s TTS **on top of the chat turn you already pay**. PTT preview-then-Send hides most of that: the operator is reading the transcript anyway.

**What “proprietary” means here (honest):** ADA’s proprietary piece is the **pipeline + packs + later local router**, not a from-scratch ASR checkpoint. Open-weight models you run are still *yours* in the trust-ring sense (audio never hits a speech SaaS). Training Whisper/Piper on Aryan’s kitchen is a lab hobby, not the v1 path.

---

## §A — Domain map (what voice systems actually do)

Five jobs get mushed in product marketing. Keep them split.

| Job | What it is | ADA v1 |
|-----|------------|--------|
| **ASR / STT** | Audio → text | **Need.** Fills composer. |
| **TTS** | Text → audio | **Need.** Speaks final ack. |
| **Turn-taking / VAD / duplex** | Who speaks when; barge-in | **PARK.** PTT bounds the utterance. |
| **Spoken NLU / intent** | Text (or audio) → skill | **Already metal** as fast-path packs. Later: tiny local router. |
| **Spoken LLM / S2S** | Audio tokens in, audio tokens out | **Reject** as cortex. Second brain; numbers ungrounded; bypasses `run_turn`. |

What a 2026 voice *product* can be (capability menu — not a build list):

1. **Dictation keyboard** — STT fills a text box (Apple Dictation, WhisperBox, ADA wedge).  
2. **Command cascade** — STT → deterministic intent → TTS (classic Alexa / HA Assist). ADA already has the middle (packs).  
3. **Agent cascade** — STT → LLM + tools → TTS (Pipecat, LiveKit Agents, most “voice agents”).  
4. **Full-duplex S2S** — one model always listening and speaking (Moshi, GPT-Live, Gemini Live).  
5. **Hybrid tandem** — fast S2S prefix + slow cascade for knowledge/tools (RelayS2S, KAME).  
6. **Local satellite + brain elsewhere** — Wyoming satellites, ESP32 Voice PE; mic is not the brain.  
7. **Phone-bot platform** — Vapi/Retell; PSTN in, SaaS cascade out.

ADA’s daily job is **(1)+(2) with (3) only when the pack misses** — kitchen/gym log, glance ack, Confirm on screen. It is not a call-center bot and not a movie duplex companion.

**Market synthesis (EVIDENCE):** sticky local assistants (HA Voice, Rhasspy lineage) treat STT/TTS as **swappable organs** and keep NLU/tools in the home system. Sticky cloud voice (ChatGPT Voice, Gemini Live) treat speech as **the product** and hide the transcript/tool path. ADA already chose the first family in M19b (voice = keyboard). This card only decides **who runs the organs**.

---

## §B — Papers / SOTA (≥8)

| # | Citation | What it actually says | ADA take | Tag |
|---|---------|------------------------|----------|-----|
| 1 | [Moshi (Défossez et al. 2024)](https://arxiv.org/abs/2410.00037) | Full-duplex spoken LLM; parallel user/system audio streams; ~160–200ms theoretical; Inner Monologue text tokens to keep language quality | Architecture to **cite and refuse** for v1. Needs GPU-class decode. Duplex fights PTT + Confirm. | **EVIDENCE** / **FANFICTION on Pi** |
| 2 | [Building enterprise realtime voice agents (2026)](https://arxiv.org/html/2603.05413v1) | Native S2S (Qwen2.5-Omni) ~13s TTFA, weak function calling. **Industry standard = cascaded STT→LLM→TTS** with *streaming between stages*. Realtime is pipelining, not one magic model. | Confirms cascade. ADA’s PTT is even simpler (batch utterance, not streaming ASR). Do **not** import Pipecat to get “realtime.” | **EVIDENCE** |
| 3 | [Full-Duplex-Bench-v3 (2026)](https://arxiv.org/pdf/2604.04847) | GPT-Realtime / Gemini Live vs Whisper→GPT-4o→TTS under real disfluency + **multi-step tools**. Cascade: perfect turn-take, **highest latency**. S2S: faster, worse chained tools / self-correction. | ADA is a **tool organism**. Cascade wins the job that matters (packs, Confirm, receipts). Latency is acceptable because preview-Send is not barge-in chat. | **EVIDENCE** / **POLICY** |
| 4 | [RelayS2S (2026)](https://arxiv.org/abs/2603.23346) | Fast duplex S2S drafts a prefix; slow ASR→LLM continues; verifier handoff. S2S quality lags cascade; cascade lags onset. | Clever **later**. Needs a local S2S model ADA will not host on 8GB. | **EVIDENCE** / **PARK** |
| 5 | [KAME tandem (2025)](https://arxiv.org/pdf/2510.02327) | S2S for immediacy; back-end LLM injected into the speech model for knowledge | Same family as RelayS2S. Steal the *idea* (cheap local path + Gemini for hard turns) — implement as **text router**, not audio tandem. | **EVIDENCE** |
| 6 | [Moonshine v2 (2026)](https://arxiv.org/pdf/2602.12241v1) | Streaming-encoder ASR; sliding-window attention; tiny/small/medium; claims Whisper-Large-class quality at ~6× smaller; designed for on-device TTFT | **Bench candidate** for the STT organ if ARM ONNX is actually faster than faster-whisper tiny.en on this Pi. Not a reason to skip the proven Whisper path. | **EVIDENCE** / **FEASIBLE-if-benched** |
| 7 | [Whisper on Raspberry Pi (ACM 2025/26)](https://doi.org/10.1145/3769102.3774244) | Pi 5: faster-whisper int8 **tiny.en ~1.15s**, **base.en ~2.13s**, distil-small.en ~4.90s on short Common Voice clips. tiny/base **are the deployable pair**. | This is the metal number. Distil-small is a luxury. Large-v3 is not a Pi organ. | **FEASIBLE** |
| 8 | [Distil-Whisper (Gandhi et al. 2023)](https://arxiv.org/abs/2311.00430) | English student of Whisper; ~5–6× faster, similar WER | Useful if tiny.en kitchen WER fails and base.en is still slow. Still cascade. | **EVIDENCE** |
| 9 | [GPT-Live engineering (OpenAI, 2026)](https://openai.com/index/continuous-voice-interaction-with-gpt-live/) | Dedicated media path, Go not Python, WARP/WebRTC, voice model **decoupled from frontier tools**, ~6 months | Why ADA must not pretend ChatGPT Voice. Steal only: **tools must not block the ack** (already: fast-path `token_delta`). | **EVIDENCE** / **FANFICTION on Pi** |
| 10 | Consent Integrity / LITL (2026) — already M19b | Confirm binds **gateway args**, not spoken paraphrase | Ear-only confirm stays forbidden even with perfect TTS. | **POLICY** |

**Contradiction that matters:** Moshi/GPT-Live argue cascade *feels* unnatural (latency, lost prosody, turn-taking). Enterprise + tool benchmarks argue cascade is how you **get tools and knowledge right**. ADA’s constitution already picked tools + receipts over conversational magic. PTT preview-Send **opts out** of the duplex race entirely.

**Research stretch — ideas we are not building:**

| Idea | Says | ADA |
|------|------|-----|
| End-to-end S2S as the assistant | One model is the product | **Reject** — second cortex, ungrounded kcal |
| Stream-everything cascade (Deepgram→LLM→Cartesia) | Sub-second TTFA is the game | Wrong game; we have a visible composer |
| Train personal ASR | Kitchen acoustics as a dataset | **Won’t-chase** v1; optional lab later |
| Style vectors / LoRA personality into TTS | Voice *is* the soul | M05 already refused weight-personality |

---

## §C — Unique pipelines (steal the shape, refuse the stack)

| Pipeline | How it’s wired | Why people built it | Steal | Refuse |
|----------|----------------|---------------------|-------|--------|
| **Home Assistant Wyoming** | TCP organs: Whisper STT, Piper TTS, openWakeWord; HA Assist = NLU/tools | Local, mix-and-match, satellites (Voice PE / ESP32) are not the brain | **STT/TTS as organs ADA hosts**; client is a transducer | HA as ADA; wake-word product; ESP32 fleet as v1 |
| **Classic cascade + streaming** (Pipecat, LiveKit Agents, HuggingFace speech-to-speech recipe) | Frame graph: transport → STT → LLM → TTS → transport | Phone bots, web voice widgets, sub-second TTFA | Modular STT/LLM/TTS; sentence-stream TTS later | Framework transplant; WebRTC; 68 vendors |
| **Moshi / Mini-Omni / Qwen-Omni** | Audio tokens ↔ audio tokens; optional inner text | Natural overlap, emotion, backchannel | Cite as the duplex ceiling | Hosting a 7B spoken LLM on the Pi |
| **RelayS2S / KAME** | Fast S2S prefix \|\| slow cascade | Buy onset *and* knowledge | **Text analogue:** local router \|\| Gemini | Two audio models |
| **WhisperBox (Pi 5)** | faster-whisper `base.en` → optional Gemma 1B **cleanup** → Piper; separate Gemma 4 E2B “ask” mode | Dictation keyboard + offline Q&A on one board | STT+TTS on Pi 5 is real; tiny cleanup model is a **later** router cousin | Ollama as cortex; HAT-required UI |
| **HA Voice PE + tiny-int8** (community 2026) | Wake ~0.2–0.4s, Whisper tiny ~1.0–1.5s, intent 50–100ms, Piper 0.5–0.8s → **~2s** when the brain is **not** an LLM | Local Alexa-class commands | Proof that **STT+TTS without local LLM is snappy** | Always-listen satellites |
| **Cloud Live APIs** (GPT-Realtime, Gemini Live, Grok voice) | One socket, audio in/out, tools bolted on | Product feel of a person on the line | Transcript-visible honesty (M19b already stole that) | Audio as a second Gemini path |
| **ADA text (METAL today)** | Verb → pack fast-path → `_speak_*`; Gemini for social / hard turns | Organism, not chat-parity | **This is already the tandem.** Voice should wrap it, not replace it | — |

**The pipeline ADA is closest to:** Wyoming-style organs + HA Assist’s “cheap intent, LLM only when needed” — except the intent layer is **already** `pack_router` / meal-gym-habit spines, and the LLM is Gemini with a register pass. Voice does not get to invent a new NLU.

---

## §D — Market tools (what they cater to)

Split by **buyer**, not by logo.

### Cloud speech vendors (sell APIs)

| Vendor | Offer | Built for | ADA |
|--------|-------|-----------|-----|
| **Deepgram / AssemblyAI / Gladia** | Streaming STT, diarization, endpoints | Voice agents, call centers, captions | Extra **audio** ring. Reject as default |
| **OpenAI Whisper API** | Batch STT, cheap-ish | Apps that don’t want to host Whisper | Same weights you can run locally; you pay for *not* hosting |
| **Google Cloud STT / Gemini transcription** | Cloud ASR | GCP shops; “already on Google” | Cortex is already Gemini. **Do not pile audio onto the same vendor** — that’s concentration, not simplicity |
| **ElevenLabs / Cartesia / PlayHT** | Premium streaming TTS, clones | Product voice, agents that must sound funded | Cost + vendor + latency. Overkill for 1–3 sentence acks |
| **OpenAI TTS / Gemini TTS** | Cheap cloud speak | Apps already in that cloud | Same objection: more Google/OpenAI surface for a solved edge task |

### Voice-*agent* platforms (sell the whole cascade)

| Vendor | Offer | Built for | ADA |
|--------|-------|-----------|-----|
| **Vapi / Retell / Bland** | PSTN + STT + LLM + TTS, latency SLOs | Phone agents, inbound sales | Wrong product. Would make ADA a tenant of a bot platform |
| **Pipecat / LiveKit Agents** | Open orchestration; you still pick vendors | Teams wiring WebRTC voice | Steal diagrams. **Refuse** as the HUD runtime |
| **ChatGPT Voice / GPT-Live** | Duplex product on OpenAI metal | Consumer chat | Architecture reference, not a dependency |
| **Gemini Live** | Native audio in the Gemini API | Apps that want Google to own the loop | **Reject.** Second cortex path; bypasses gateway; audio to Google; fights “don’t add a vendor” by deepening the one we already have |

### Local / on-device (sell software, not minutes)

| Project | Offer | Built for | ADA |
|---------|-------|-----------|-----|
| **faster-whisper / whisper.cpp / sherpa-onnx** | Run Whisper-class ASR on CPU | Edge, privacy, HA | **STT organ candidates** |
| **Moonshine** | Tiny streaming ASR | Phones, IoT | Bench vs tiny.en |
| **Piper** | ONNX VITS TTS, Pi-native | HA, embedded | **TTS organ default** |
| **Kokoro 82M** | Better MOS, Apache | Laptops, audiobooks | Quality win, **Pi CPU ~4.8s** vs Piper **~0.53s** on a short line ([edge_tts_comparison](https://github.com/ktomanek/edge_tts_comparison)) — **PARK** for acks |
| **Kitten / Pocket TTS** | Even smaller | Toys, IoT | Fallback if Piper RAM ever hurts (it shouldn’t) |
| **Apple Speech / Web Speech API** | OS dictation in the browser | Zero-install | **Degraded FACT**, not the organ (vendor is Apple/Google in the browser; iOS PWA isolation) |
| **openWakeWord / Porcupine** | Wake-word | Always-listen | Tier C |

**Market movement (2026), compressed:**

- **On-device ASR caught up** for short English utterances (Moonshine, Distil-Whisper, Whisper tiny/base on Pi 5). Cloud STT’s remaining edge is streaming captions, 100 languages, and dirty call-center audio — not kitchen “log meal chicken rice.”  
- **Realtime voice** money is in **phone agents** (Vapi et al.) and **duplex Live APIs**. Neither matches a personal organism with Confirm Integrity.  
- **Local home voice** converged on **Wyoming + Whisper + Piper**. That is the copyable product for ADA’s metal.  
- **S2S models** are the research/product headline and still lose on **tool chains** (FDB-v3). ADA is a tool chain.

---

## §E — Options on this metal and this code

**METAL (honest, 2026-08-19):** no mic, no STT, no TTS. Composer is textarea + chips. `ChatBody` already accepts `input: typed|stt` but HUD always sends `typed`. Mouth is `_speak_*` templates in [`loop.py`](../../src/ada/harness/loop.py); register pass **not** shipped. Cortex is [`GeminiAdapter`](../../src/ada/cortex/gemini.py) / `gemini-2.5-flash`. One ASGI HUD, one `ChatService`. RAM envelope from doc-00 inspect: ~8 GiB, idle historically ~0.8 GiB used, **no local LLM resident**. That last fact is why local STT+TTS is a different question than “local Jarvis.”

M14 allowed B-voice with **Mac CPU** so the Pi stayed a text API. That was correct when the fear was **STT+LLM+TTS on 8GB**. The fear was right for a local brain. It is **wrong** once Gemini stays the brain: then the Pi is closer to a 4GB “STT+TTS only” box, which community stacks already call feasible.

### Option matrix

| ID | Path | Latency add (typical PTT utterance) | RAM on Pi | Audio egress | Organism? | Verdict |
|----|------|-------------------------------------|-----------|--------------|-----------|---------|
| **A** | Cloud STT + cloud TTS (M20 default-until-research) | 0.5–2s + 0.3–1s + vendor RTT | ~0 | wav → speech SaaS | No — more scripts | **Reject.** Second vendor family while cortex is already Gemini |
| **B** | Gemini Live / GPT-Realtime | Product-fast if it works | ~0 | audio → frontier | No — **second brain** | **Reject.** Bypasses `run_turn`, Confirm, numeric guard. F-M20-2 waiting to happen |
| **C** | Browser STT/TTS (Whisper WASM / Kokoro WebGPU / Web Speech) | Mac: OK. iPhone PWA: flaky | ~0 | none (or Apple/Google OS) | Split brain: each window is the organ | **Reject as default.** Phone + Mac diverge; ADA doesn’t own voice; iOS Safari≠PWA storage already painful |
| **D** | **Pi STT + Pi TTS, Gemini cortex** (cascade organs) | STT 1–3s + TTS 0.3–0.8s; Gemini as today | ~0.8–1.8 GiB hot (tiny.en + Piper); bursty | none beyond Tailscale | **Yes** | **LOCK** |
| **E** | Pi STT+TTS + **local** 1–4B LLM | 8–25s E2E | 3–4 GiB+; swap risk with HUD | none | Offline demo | **PARK** (M20 full-loop). Does not overturn |
| **F** | Train / fine-tune ADA ASR+TTS | Months + data | training ≠ Pi | — | Cosplay “proprietary model” | **Won’t-chase.** Pipeline is the proprietary artifact |
| **G** | Hybrid: Pi organs default, Web Speech FACT fallback | as D / as C | as D | none / OS | Default stays D | **Allowed later** as degraded path, not v1 gate |

**Cost (honest):** Option A is cheap in *engineering hours* and expensive in *identity* (ADA becomes glue). Option D is cheap in *dollars* (zero speech API) and moderate in *engineering* (one blob endpoint, one wav endpoint, ffmpeg/wav convert, model files on HDD). HDD on `ada-data` already exists for model weights.

**Thermal / contention:** PTT is **not** always-on ASR. Load tiny.en once, infer on release, idle. Do not run Whisper and a future 1B router at full tilt together until measured. HUD + Gemini client + tiny.en + Piper is the design envelope.

### STT organ (inside D)

| Model | Pi 5 short-utterance | RAM | Notes |
|-------|----------------------|-----|-------|
| **faster-whisper `tiny.en` int8** | ~1.2s | smallest Whisper | **Default.** Kitchen English, short PTT |
| **faster-whisper `base.en` int8** | ~2.1s | still fine | If tiny drops words (WhisperBox found this) |
| Distil-Whisper small | ~5s | larger | Only if WER still fails |
| Moonshine tiny/small | **unknown on this Pi until benched** | very small | Stretch; implement chat may swap if a 20-utterance kitchen bench wins |
| Whisper large / cloud | — | no / vendor | Out |

**Lock:** English `.en` models. Operator language is English. Multilingual is not a wedge gate.

### TTS organ (inside D)

| Engine | Pi 5 (short ack) | RAM | Quality | Verdict |
|--------|------------------|-----|---------|---------|
| **Piper `en_US-lessac-medium`** | 0.3–0.8s / phrase; ~0.53s in one Pi 5 bake-off | ~100–150 MB | Assistant-grade, a bit synthetic | **Default.** M05 brevity is the quality feature |
| Piper low | faster | smaller | more robotic | Fallback if medium ever contends |
| Kokoro 82M | ~4.8s on Pi 5 CPU for a short line | ~0.4–1 GiB | nicer | **PARK.** Audiobook engine, not ack engine |
| Cloud premium TTS | vendor | 0 | best | Reject (see A) |

**Timbre:** pick **one** Piper voice and live with it. Do not shop voices per turn. Register is M05 wording, not a clone of Aryan.

---

## §F — “Proprietary model” vs proprietary **pipeline**

The ideology in the prompt is right: ADA should not be a folder of scripts that call APIs. The wrong implementation of that ideology is **training a speech net.**

| Artifact | Who owns it | v1 |
|----------|-------------|----|
| Pack router, spines, gateway, receipts | ADA | **Already metal** — this *is* the proprietary NLU |
| STT/TTS **process + weights on disk + `/api/voice/*`** | ADA | **This card** |
| Register contract + `_speak_*` + Gemini mouth | ADA + existing Gemini ring | Phase 2 (M19b/M20) |
| Tiny local **intent router** (0.5–1B or even a classifier) | ADA | **Later**, when fast-path misses need a cheap on-box guess before Gemini |
| From-scratch / LoRA ASR or TTS | Lab | **Won’t-chase** |

**Later routing (locked as direction, not this implement):**

```text
utterance text
    │
    ├─ known verb / pack fast-path     → tools, no Gemini   (METAL)
    ├─ tiny local router (future)      → pack | social | escalate
    └─ Gemini                          → analysis, social, register pass
```

That is the same split constitution already wrote: local models **ancillary** (doc-00 Tier B: “optional small local LLM for offline / intent routing”). Voice does not wait on that router. Fast-path already routes the daily verbs. Do not block the wedge on a GGUF.

---

## §G — Locked path (do not reopen as OPEN)

**Name:** Pi-owned cascade organs.  
**STT:** faster-whisper `tiny.en` int8, upgrade to `base.en` if kitchen WER fails a 20-clip smoke.  
**TTS:** Piper `en_US-lessac-medium`.  
**Placement:** blob up, wav down, **same HUD origin** (or `127.0.0.1` sibling owned by ADA). Mac/phone = MediaRecorder + Web Audio. Phone tap vs Mac hold is [`M20b_PHONE_FACE.md`](./M20b_PHONE_FACE.md) (v1.2), not a second path.  
**Cortex:** unchanged Gemini. **No** audio to Gemini.  
**UX:** M19b v1.6 preview-then-Send; simplex mute-while-TTS; TTS of **final** speak line only.  
**Secrets:** no new speech API keys. Model files live under `ADA_DATA_ROOT` (weights) — not git.

### Flow (phase 2 implement; this card does not code it)

```text
[PTT: Mac hold / phone tap-to-toggle] → MediaRecorder (webm/opus or mp4)
          → POST /api/voice/stt          ← Pi organ
          → fill composer (input=stt)    ← STOP. Operator reads.
          → Send
          → POST /api/chat  (existing)
          → SSE token_delta | tool | confirm | view_open | turn_done
          → POST /api/voice/tts { text: final ack }
          → play; mic muted
```

Falsifiers M19b-3/13 and M20-2 still bind: audio never tools; `runs/` text = composer text sent.

### What this does to prior OPEN defaults

| Prior default | This card |
|---------------|-----------|
| M20 OPEN #1 cloud STT+TTS | **SUPERSEDED** — Option D |
| M19b TTS cloud / STT Mac-browser-first | **SUPERSEDED** |
| M14 Pi stays text API | **SUPERSEDED for STT/TTS organs only.** Pi still not a second cortex. Windows still own mic/speaker |
| M20 local full-loop PARK | **Holds** |
| M19b local STT/TTS PARK | **SUPERSEDED** — that PARK bundled full-loop. Organs without local LLM are in |

---

## §H — Falsifiers

| ID | Fail if… |
|----|----------|
| **F-M20a-1** | Phase 2 ships Deepgram/Whisper-API/ElevenLabs/Gemini-TTS/Gemini-Live as the **default** path |
| **F-M20a-2** | Audio reaches Gemini (Live or file upload) as the turn, or a voice path bypasses `run_turn` |
| **F-M20a-3** | STT auto-POSTs the chat (preview-then-Send regress) |
| **F-M20a-4** | Local **LLM** is required for the wedge to speak (full-loop sneak-in) |
| **F-M20a-5** | Pi STT+TTS default path swaps the HUD or thermal-throttles into unusable chat (then drop to tiny.en / Piper-low — do not “fix” with a cloud vendor) |
| **F-M20a-6** | Implement chat trains/fine-tunes ASR or TTS as a gate to ship PTT |

M19b F-M19b-3,4,5,11,13,16 and M20 F-M20-2,3 still apply to the wedge/mouth slice.

---

## OPEN (≤5)

| # | Question | Default until a later chat locks it |
|---|----------|-------------------------------------|
| 1 | **tiny.en vs base.en** | **tiny.en**; 20-clip kitchen smoke may promote `base.en`. Not a vendor reopen |
| 2 | **Moonshine swap** | Off until a same-clip bench on `ada-pi5` beats tiny.en on WER×latency |
| 3 | **STT process shape** | Same FastAPI process first; extract Wyoming-style sibling if RAM isolation needs it — still ADA-owned |
| 4 | **Degraded STT** | None in v1. Web Speech FACT later if Pi is down — must still preview-Send |
| 5 | **Local router GGUF** | **After** wedge ships. Fast-path remains the router until then |

**Do not reopen as OPEN:** cloud speech default; Gemini Live; Pipecat; training a voice model; Kokoro-as-ack; duplex; full local LLM loop.

---

## Locks (do not reopen)

| Lock | Source |
|------|--------|
| Voice = PTT transport to same packs; preview-then-Send; simplex | M19b v1.6, M20 |
| Gemini = only cortex; register pass = mouth on receipt JSON | M19b, M05, constitution |
| STT + TTS = **Pi organs**, open weights, no extra speech SaaS | **this card** |
| Local full-loop STT+LLM+TTS = PARK | M20, this card |
| Train speech models = won’t-chase for the wedge | **this card** |
| Later local router = ancillary, in front of Gemini, not a replacement | doc-00, constitution, **this card** |
| Confirm on ingress screen; ear-only forbidden | Consent Integrity, M15, M19b |
| Python ASGI + static HUD; no Next; no Pipecat as runtime | M14, M20 |

---

## Implement-next (for the **next** chat — not this one)

This card is M20 **phase 1 done**. Phase 2 (M20 / M19b P1.5) can now be ordered without re-research:

1. **Organs:** model files on data disk; `POST /api/voice/stt` (audio → text); `POST /api/voice/tts` (text → audio); fail closed (empty audio → empty composer, no fake transcript).  
2. **Wedge UI:** composer mic states (M19b); MediaRecorder → STT → composer; Send as today with `input=stt`.  
3. **Mouth:** register pass ON + numeric guard; template `_speak_*` fallback; TTS **final** text only.  
4. **Smokes:** kitchen 20 clips WER; Pi RSS with HUD+STT+TTS hot; no audio in Gemini payloads; `runs/` text = sent composer.

**Do not start in that chat:** local Gemma/Phi cortex, Moonshine-as-blocker, Kokoro, wake-word, Live APIs, mail, duplex, training.

---

## References

- Moshi — https://arxiv.org/abs/2410.00037  
- Enterprise realtime voice agents (cascade as standard) — https://arxiv.org/html/2603.05413v1  
- Full-Duplex-Bench-v3 — https://arxiv.org/pdf/2604.04847  
- RelayS2S — https://arxiv.org/abs/2603.23346  
- KAME tandem — https://arxiv.org/pdf/2510.02327  
- Moonshine v2 — https://arxiv.org/pdf/2602.12241v1  
- Whisper on Raspberry Pi — https://doi.org/10.1145/3769102.3774244  
- Distil-Whisper — https://arxiv.org/abs/2311.00430  
- GPT-Live — https://openai.com/index/continuous-voice-interaction-with-gpt-live/  
- Pi 5 local voice (full-loop 8–25s; STT+TTS subset) — https://bmdpat.com/blog/raspberry-pi-5-local-voice-ai-2026  
- HA-class local RTT ~2s without LLM — https://smarthomeguide.blog/blog/2026/locally-hosted-voice-assistant-journey/  
- WhisperBox (Pi 5 base.en + Piper) — https://github.com/hassard0/WhisperBox  
- Piper vs Kokoro on Pi 5 — https://github.com/ktomanek/edge_tts_comparison  
- Wyoming / HA Voice shape — community HA Assist + Whisper + Piper  
- Internal: M20, M19b, M14, M05, doc-00, constitution  

---

*End M20a voice path v1.0. Design only — pick locked.*
