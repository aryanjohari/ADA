# M01 — Network & Access (Tailscale Tier A)

**Status:** module research card + practical access plan (**doc-only** — no agent code)  
**Date:** 2026-08-12  
**Host:** `ada-pi5` (Raspberry Pi 5, Debian trixie)  
**Branch:** `rewrite/v1-body`  
**Depends on:** [`../01_BODY.md`](../01_BODY.md) §7 & §10.8, [`../02_CONSTITUTION.md`](../02_CONSTITUTION.md) §11 & §16, [`../00_ASSISTANT_RESEARCH.md`](../00_ASSISTANT_RESEARCH.md) §8  

**Slice rule:** this card admits **Tailscale access setup + verification**. It does **not** admit agent HTTP servers, HUD code, or M0 vitals organs.

---

## 1. Question / goal

**Question.** How does Aryan reach `ada-pi5` **reliably and privately** — from phone/laptop at home and away — without depending on a fragile LAN DHCP address, and without opening ADA to the public internet?

**Goal (Tier A access).**

1. Install and join a **personal Tailscale tailnet** on `ada-pi5` + Aryan’s phone + laptop (first-time account).  
2. Use a **stable Tailscale identity** (MagicDNS name / `100.x` address) as the control-plane address.  
3. Leave agent / HUD **unimplemented** for now — but design access so future HUD binds `localhost` and is reachable only via **Tailscale (Serve OK)**.  
4. Explicitly **reject Funnel** (public internet exposure).

**METAL snapshot (2026-08-12 inspect):**

| Fact | Value |
|------|--------|
| Hostname | `ada-pi5` |
| `wlan0` | UP; IPv4 `192.168.7.134/22` (**DHCP**, `dynamic`) |
| Default route / DNS | via `192.168.4.1` |
| `eth0` | DOWN (per body inventory) |
| Tailscale | **not installed yet** |

---

## 2. Lens tags

| Tag | What it means here |
|-----|--------------------|
| **METAL** | Observed on this Pi (Wi‑Fi DHCP address, Tailscale absent, power incidents) |
| **EVIDENCE** | Tailscale / WireGuard / home-DHCP docs and established networking practice |
| **FEASIBLE** | Free personal Tailscale; Pi 5 has RAM/CPU to spare for the daemon |
| **POLICY** | Tailscale-only control plane; Serve OK; Funnel NO; Aryan-device ACLs later; session auth later |
| **FANFICTION** | “Always reachable like Jarvis from anywhere” — true *only* as private mesh reachability, not public omnipresence |

---

## 3. How home networking works here

### 3.1 Picture in one paragraph

Your home router (gateway `192.168.4.1` from this LAN) runs **Wi‑Fi** and a **DHCP lease pool**. When `ada-pi5` joins Wi‑Fi, it asks DHCP for an address. The router picks something like `192.168.7.134` from the pool and says “use this for a while.” That address is **local-only**: useful on the home Wi‑Fi, useless from cellular / another house, and **not a promise** across reboots or lease renewals.

```text
[phone/laptop] --Wi‑Fi--> [home router 192.168.4.1]
                              |
                              +-- DHCP --> ada-pi5 gets 192.168.7.x (changes)
                              +-- LAN traffic stays inside the house
```

### 3.2 Why the LAN IP changed (your reboot incident)

**METAL.** After the outlet/power event, DHCP re-leased a **different** `192.168.x` address. That is normal DHCP behavior:

- Leases expire or are forgotten when the client (or router) restarts.  
- The pool is shared with every phone, laptop, and IoT blob on the network.  
- “What I typed yesterday” (`ssh ari@192.168.7.???`) is a sticky note, not an identity.

So: **do not treat `192.168.x` as ADA’s phone number.**

### 3.3 Power path hygiene (same incident, different organ)

**METAL incident (operator report):** a fan / power-strip switch cut power to the Pi. That is a **body availability** problem, not a Tailscale bug.

| Layer | Lesson |
|-------|--------|
| Power | Don’t put the Pi on the same switched outlet as a fan you thrash. Prefer always-on outlet + known UPS later. |
| USB-root + HDD | Dirty power cuts stress USB sticks and mechanical disks (body §1.3.1). |
| Network after reboot | Expect DHCP churn; rely on Tailscale / MagicDNS for reachability, not `192.168.x`. |

---

## 4. How Tailscale works (plain language)

### 4.1 Overlay, not replacement Wi‑Fi

Tailscale does **not** replace your home Wi‑Fi. The Pi still gets a LAN address via DHCP. Tailscale adds a second identity: a **virtual IP in `100.x.y.z`** (CGNAT range `100.64.0.0/10`) that is **stable across LAN renumbers and coffee shops**.

```text
Control plane (tiny):  each device <-> Tailscale coordination (keys, who is online, ACLs)
Data plane (the actual bits):  phone <-> WireGuard tunnel <-> ada-pi5
                               (direct if possible; DERP relay if NATs fight)
```

**EVIDENCE.** Tailscale sits on WireGuard: each node keeps a private key locally; peers exchange public keys via a coordination server; **user is end-to-end encrypted between devices** — the coordinator is not meant to sit in your chat stream ([How Tailscale works](https://tailscale.com/blog/how-tailscale-works)).

### 4.2 MagicDNS

Every node also gets a **name**, e.g. `ada-pi5.<your-tailnet>.ts.net` (exact suffix shown in the admin DNS page). On each device, MagicDNS answers via a local resolver at `100.100.100.100`, so `ssh ada-pi5` / browser URLs stay human while `192.168.x` thrash underneath ([MagicDNS](https://tailscale.com/docs/features/magicdns)).

### 4.3 Peer vs relay (DERP)

Ideal path: **direct peer-to-peer** WireGuard after NAT hole-punching. Fallback: encrypted packets bounce through Tailscale **DERP** relays. You still get connectivity; latency may rise. For a home Pi + phone, direct often works on the same Wi‑Fi or with ordinary consumer NAT.

### 4.4 Auth & ACLs (what “only Aryan” means)

1. **Login:** devices join only after authenticating to *your* Tailscale account (OAuth / identity provider).  
2. **ACL / grants (later harden):** policy file says which identities may talk to which ports on which nodes ([tailnet policy file](https://tailscale.com/docs/features/tailnet-policy-file)).  
3. **App session (later, when HUD exists):** constitution requires **extra** auth for Agent writes — Tailnet presence alone is not enough ([`02_CONSTITUTION.md`](../02_CONSTITUTION.md) §11).

Default personal tailnets are often wide-open among *your* devices. That is OK for first join; **tighten before HUD Agent mode**.

### 4.5 Serve vs Funnel (memorize this)

| Feature | Who can reach the service? | ADA policy |
|---------|----------------------------|------------|
| **Serve** | Only devices on **your tailnet** | **OK** when HUD exists ([Serve](https://tailscale.com/docs/features/tailscale-serve)) |
| **Funnel** | **Anyone on the public internet** via a public URL | **NO — won’t chase; don’t enable** ([Funnel](https://tailscale.com/docs/features/tailscale-funnel)) |

Serve can reverse-proxy `http://127.0.0.1:<port>` with HTTPS on the MagicDNS name. Best practice when using Serve: **bind the app to localhost** so LAN peers cannot skip Tailscale and spoof identity headers ([Serve identity headers guidance](https://tailscale.com/docs/features/tailscale-serve)).

---

## 5. Options compared

| Option | Stable after DHCP churn? | Works off-home? | Privacy | Teaching value | Verdict |
|--------|--------------------------|-----------------|---------|----------------|---------|
| Raw LAN IP (`192.168.7.134`) | No | No | LAN-trusted only | Teaches why DHCP hurts | **Tactical only** (same-room debug) |
| DHCP reservation (router binds MAC → IP) | Better on *one* router | No | LAN | Good home-lab hygiene | **Optional nicety** — not control plane |
| Static IP on Pi | Yes on *that* LAN | No | LAN | Useful to learn Interface config | Won’t-chase as primary |
| Port-forward router → Pi | Sort of | Yes (and scary) | Public attack surface | Teaches why not to | **Won’t-chase** |
| Dynamic DNS + open ports | Sort of | Yes | Public | Same | **Won’t-chase** |
| Vanilla WireGuard DIY | Yes if you manage keys | Yes | Excellent if done right | High — but ops tax | Won’t-chase *before* learning Tailscale |
| **Tailscale mesh** | **Yes (`100.x` + MagicDNS)** | **Yes (if client online)** | Private tailnet | High, low ceremony | **Chosen base** |
| **Tailscale Serve** | Same | Tailnet-only HTTPS URL | Private | Perfect match for HUD later | **Chosen for future HUD** |
| **Tailscale Funnel** | Same | World | Public by design | Teaches exposure risk | **Forbidden for ADA control plane** |

**Harder-but-correct vs shortcut**

| Shortcut | Harder-correct (chosen) |
|----------|-------------------------|
| Bookmark today’s `192.168.x` | Identity = Tailscale name / `100.x` |
| “Just open port 80 on the router” | Private mesh; no WAN expose |
| Funnel for “easy phone access without installing Tailscale” | Install Tailscale on the phone; keep Serve private |

**Won’t-chase this slice:** router deep-dives beyond “optional reservation,” Cloudflare Tunnel as primary control plane, self-hosted Headscale, IPv6-only mazes, enterprise IdP SSO, Funnel demos, agent HTTP implementation.

---

## 6. Chosen architecture (ADA Tier A access)

```text
                    ┌─────────────────────────────┐
                    │  Aryan phone / laptop       │
                    │  Tailscale client ON        │
                    └─────────────┬───────────────┘
                                  │ WireGuard (direct or DERP)
                                  ▼
┌─────────────────────────────────────────────────────────────┐
│ ada-pi5                                                     │
│  wlan0: DHCP 192.168.x  (incidental; may change)            │
│  tailscale0: stable 100.x + MagicDNS ada-pi5.<tailnet>      │
│                                                             │
│  NOW:   SSH / admin via Tailscale IP or name                │
│  LATER: HUD binds 127.0.0.1 → `tailscale serve` (private)   │
│  NEVER: funnel; bind 0.0.0.0 for control UI; WAN portfwd    │
└─────────────────────────────────────────────────────────────┘
```

**POLICY alignment**

| Doc rule | How M01 satisfies it |
|----------|----------------------|
| Body §7 Tailscale-only control plane | Ingress design assumes mesh; no public Funnel |
| Constitution §11 Ring 1 | Control plane = Tailscale/localhost |
| Constitution §16 M01 before code | This card |
| Body §10.8 acceptance (later) | UI not on open LAN/WAN — enforced when agent binds |

**Egress impact (trust rings):** joining Tailscale uses the **control plane** ring (keys + presence metadata with Tailscale Inc.). It is **not** Gemini cortex and **not** Dream backup. No autobiography leaves the Pi because of Tailscale alone.

**Pi 5 feasibility:** Tailscale `userspace`/`wireguard-go` path is light relative to an 8GB agent+LLM stack. **FEASIBLE** as always-on daemon.

---

## 7. Threat model + harden steps

### 7.1 Surfaces (think in rings)

| Surface | Who is scary? | What they could do | ADA stance |
|---------|---------------|--------------------|------------|
| **Public internet** | Everyone | Scan / exploit any open service | **No Funnel; no router port-forward of agent** |
| **Home LAN** | Guest Wi‑Fi, compromised IoT, roommate curiosity | Hit anything listening on `0.0.0.0` / LAN IP | Later: bind HUD to **localhost**; Tailscale or SSH only |
| **Tailnet** | Stolen laptop still logged into Tailscale; oversharing devices into the tailnet | Reach `ada-pi5` services allowed by ACL | Start personal-only; **ACL Aryan devices**; revoke lost devices |
| **App / Agent** | Any tailnet peer treated as sovereign | Irreversible memory / tools | Constitution: **session auth** for Agent writes (later) |

### 7.2 Harden ladder (now → soon → with HUD)

**Now (this slice):**

1. Create **personal** Tailscale account (Aryan only).  
2. Install Tailscale on Pi + phone + laptop; approve devices in admin console.  
3. Enable **MagicDNS** (+ HTTPS certificates when Serve is near — can wait until HUD).  
4. Prefer `ada-pi5` / MagicDNS FQDN over `192.168.x`.  
5. Do **not** run `tailscale funnel`. Do **not** add Funnel `nodeAttrs` unless you intend public expose (you don’t).  
6. Note admin URL for device revoke (lost phone drill).

**Soon (still pre-HUD, optional but good learning):**

7. Tighten ACL / grants: only Aryan user (or device tags) → `ada-pi5:22` / needed ports. Default “everyone can talk to everyone” is fine for a 1-person lab of 3 devices; still read the policy file once.  
8. Optional: router **DHCP reservation** for quieter LAN debugging — never as sole plan.  
9. Power-strip hygiene; consider documenting outlet map.

**When HUD / agent land (out of scope for code here):**

10. Bind agent HTTP to `127.0.0.1` (or Tailscale interface only) — **not** `0.0.0.0`.  
11. `tailscale serve` → localhost port.  
12. Confirm `funnel` status is off.  
13. Implement `auth.session` for Agent writes (constitution).  
14. Confirm deny of public reach (body §10.8).

---

## 8. Learning objectives

After completing setup + checklist, Aryan should be able to explain **out loud**:

1. Why a **DHCP LAN IP** is not a durable identity (and what happened after the outlet reboot).  
2. The difference between **Wi‑Fi LAN** and a **Tailscale overlay** (`100.x` / MagicDNS).  
3. What Tailscale’s **coordination server** does vs what **WireGuard** does with traffic.  
4. **Serve vs Funnel** — and why ADA forbids Funnel.  
5. Why future HUD should bind **localhost** and still be reachable from the phone.  
6. How **privacy rings** separate Tailscale control vs Gemini cortex vs Dream backup.  
7. What to do if the phone is stolen (revoke device) vs if the Pi loses power (power path + wait for mesh to return).  

**Falsifier:** if after setup you still SSH only by memorized `192.168.x` and cannot sketch Serve≠Funnel, the slice is not done.

---

## 9. Acceptance / proof checklist

Run on **Pi** unless noted. Replace placeholders with values from `tailscale status`.

### 9.1 Install & identity

- [ ] `which tailscale` succeeds on `ada-pi5`.  
- [ ] `sudo tailscale status` shows Pi **online** and lists phone + laptop (once enrolled).  
- [ ] `sudo tailscale ip -4` prints a stable `100.x.y.z`.  
- [ ] MagicDNS resolves from a **client**: `tailscale ping ada-pi5` (or FQDN from admin DNS page).  

### 9.2 Independence from LAN DHCP

- [ ] From phone/laptop **on home Wi‑Fi**: `ping` / SSH using **Tailscale name or `100.x`**, not only `192.168.x`.  
- [ ] Mental proof: if DHCP gave a new `192.168.x` tomorrow, Tailscale IP/name still works (re-check after any reboot).  

### 9.3 Off-LAN (when feasible)

- [ ] From phone on **cellular** (Wi‑Fi off): Tailscale shows Pi online; `tailscale ping ada-pi5` works (may use DERP).  

### 9.4 Privacy / non-goals

- [ ] `sudo tailscale serve status` — no surprise public funnel config (or command reports nothing enabled).  
- [ ] Confirm you did **not** enable Funnel in admin / never ran `tailscale funnel`.  
- [ ] No router port-forward rules created for ADA agent ports.  

### 9.5 Doc / lab gate

- [ ] This card exists under `docs/modules/`.  
- [ ] No agent Python HTTP server was added in this slice.  

---

## 10. Step-by-step setup (THIS Pi + first-time account)

Assume: **new personal Tailscale account**, operator is networking-new, host is `ada-pi5` on Debian via Wi‑Fi.

### 10.0 Before you start

1. Fix power: Pi on an **always-on** outlet (not the fan switch strip if possible).  
2. Have a second device (phone or laptop) ready for the auth browser flow.  
3. Keep this file open for the proof checklist.

### 10.1 Create the Tailscale account (laptop or phone browser)

1. Open [https://login.tailscale.com/start](https://login.tailscale.com/start).  
2. Sign up with an identity you control long-term (Google / Microsoft / GitHub / Apple — pick one you’ll keep).  
3. Create a **personal** tailnet (default free tier is enough for a lab of a few devices).  
4. Leave admin console open: [https://login.tailscale.com/admin/machines](https://login.tailscale.com/admin/machines).

### 10.2 Install Tailscale on `ada-pi5`

On the Pi (LAN SSH for now is fine — chicken/egg: you still have local Wi‑Fi):

```bash
# Official install script (Debian / Raspberry Pi OS family)
curl -fsSL https://tailscale.com/install.sh | sh

# Bring the node up (opens a login URL)
sudo tailscale up
```

1. Copy the printed URL into a browser already logged into Tailscale (or complete auth on the Pi if you have a browser).  
2. Approve the machine. Prefer naming it **`ada-pi5`** to match hostname.  
3. Verify:

```bash
sudo tailscale status
sudo tailscale ip -4
hostname
```

### 10.3 Enable MagicDNS

1. Admin console → **DNS**.  
2. Enable **MagicDNS**.  
3. Note your tailnet DNS name (`*.ts.net` suffix).  
4. From another enrolled device, prefer `ada-pi5` or `ada-pi5.<tailnet>.ts.net`.

HTTPS certificates (needed for Serve later) can wait until HUD; enabling HTTPS in DNS settings early is fine.

### 10.4 Install on laptop

- **Linux:** same `install.sh`, then `sudo tailscale up`.  
- **macOS / Windows:** install from [https://tailscale.com/download](https://tailscale.com/download), sign in with the **same** account.  

Proof:

```bash
tailscale ping ada-pi5
# or: ssh <user>@ada-pi5   # once MagicDNS search domains apply
```

### 10.5 Install on phone

1. Install Tailscale from App Store / Play Store.  
2. Sign in with the **same** account.  
3. Toggle Tailscale **on**.  
4. In the app, confirm `ada-pi5` appears online.  
5. Cellular test: disable Wi‑Fi; confirm still reachable via Tailscale.

### 10.6 First ACL glance (lightweight)

1. Admin → **Access controls**.  
2. Read the default policy once so the file is not scary later.  
3. For a solo lab with only Aryan’s devices enrolled: default is acceptable for **SSH reachability**.  
4. Do **not** add Funnel `nodeAttrs` “just because docs mention it.”  
5. Bookmark: how to **remove a device** if a phone is lost.

### 10.7 Optional LAN niceties (not required)

- In the home router UI: DHCP reservation for `ada-pi5` MAC → fixed `192.168.x` for local debugging only.  
- Do **not** skip Tailscale verification because reservation “feels enough.”

### 10.8 What NOT to do

- Do not run `tailscale funnel …`.  
- Do not open WAN ports to the Pi for “temporary HUD tests.”  
- Do not invite friends’ devices into this tailnet for ADA control.  
- Do not implement agent listeners in this slice.

---

## 11. Ops notes

| Topic | Practice |
|-------|----------|
| Power strip | Label the Pi outlet; never put kill-switches for fans on the Pi’s power. Unclean cut = risk to USB root + HDD autobiography (body §1.3.1 / §6). |
| Reboot recovery | After power returns: wait for Wi‑Fi + `tailscaled` online; use MagicDNS, not yesterday’s LAN IP. |
| “Is ADA down?” triage | (1) power/LED (2) `wlan0` has DHCP (3) `tailscale status` (4) only then panic about agent code. |
| Addressing habit | Store `ada-pi5` / MagicDNS FQDN in SSH config & notes; treat `192.168.x` as disposable. |
| Updates | Keep `tailscaled` packaged updates with system security updates. |
| Travel / café | Laptop Tailscale on → same `ada-pi5` name works; you are not “port forwarding home.” |
| Backup of access | If you lose all enrolled clients, use Tailscale account recovery + local console/LAN to `tailscale up` again. |

---

## 12. What this unlocks vs what waits

### Unlocks (after checklist)

- Stable private SSH / admin path to the body from Aryan’s devices.  
- Confidence that DHCP churn and “I went to another Wi‑Fi” don’t break the mental model.  
- Clear control-plane ring for upcoming HUD.  
- Shared vocabulary (Serve / Funnel / MagicDNS / ACL) for constitution enforcement.

### Waits for HUD / M0 (explicitly out of this card)

| Later work | Why not now |
|------------|-------------|
| `body.vitals` organ | M0 body organs — separate research/implementation |
| Agent process + chat loop | Cortex + tools — after body/access foundations |
| `tailscale serve` to a live port | Needs a localhost HTTP app |
| `auth.session` | Needs HUD login surface |
| Tight production ACLs / tags | More valuable once ports exist to protect |
| Gemini cortex egress | Different trust ring |
| Dream / S3 backup | Different trust ring |

---

## 13. References

### Official Tailscale (primary)

- How Tailscale works — https://tailscale.com/blog/how-tailscale-works  
- MagicDNS — https://tailscale.com/docs/features/magicdns  
- MagicDNS design notes — https://tailscale.com/blog/magicdns-why-name  
- Tailscale Serve — https://tailscale.com/docs/features/tailscale-serve  
- Tailscale Funnel — https://tailscale.com/docs/features/tailscale-funnel  
- Tailnet policy / ACLs — https://tailscale.com/docs/features/tailnet-policy-file  
- Install — https://tailscale.com/download  

### WireGuard / mesh background

- WireGuard formal protocol — https://www.wireguard.com/  
- Tailscale overview of mesh + DERP concept — see “How Tailscale works” above  

### Internal ADA docs

- [`../01_BODY.md`](../01_BODY.md) — §1.4 network metal; §7 ingress; §10.8 Tailscale-only acceptance; §11 non-goal public UI  
- [`../02_CONSTITUTION.md`](../02_CONSTITUTION.md) — §11 privacy rings; §13 enforcement; §16 lab mode / M01 pointer  
- [`../00_ASSISTANT_RESEARCH.md`](../00_ASSISTANT_RESEARCH.md) — §8 module card gate  

---

## 14. Do this next (ordered)

1. **Setup** — Create personal Tailscale account → install on `ada-pi5` → enroll laptop → enroll phone (§10).  
2. **Verify** — Complete §9 checklist (same Wi‑Fi + cellular ping; no Funnel).  
3. **Hardening pass (light)** — Revoke any accidental devices; skim ACL file; write MagicDNS name in your notes / SSH config.  
4. **Power hygiene** — Move Pi off switched fan strips; confirm clean reboot still returns via Tailscale.  
5. **Then M0 research** — Write / complete the **M0 body organs** research card (vitals / identity / lifecycle) **before** coding those organs. Do **not** start agent HUD code until M01 checklist is green.  
6. **Only after M0 organs exist** — design HUD bind + `tailscale serve` + session auth (still no Funnel).

---

*End of M01. Doc admits access setup; it does not admit public exposure or agent implementation.*
