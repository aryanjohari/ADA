import {
  Callout,
  Card,
  CardBody,
  CardHeader,
  Divider,
  Grid,
  H1,
  H2,
  H3,
  Link,
  Pill,
  Row,
  Stack,
  Stat,
  Table,
  Text,
  useHostTheme,
} from "cursor/canvas";

export default function AdaFoundationDocsReview() {
  const { tokens: t } = useHostTheme();

  return (
    <Stack gap={24} style={{ padding: 24, maxWidth: 1100 }}>
      <Stack gap={8}>
        <H1>ADA foundation docs — cross-check</H1>
        <Text tone="secondary" size="small">
          Sources: docs/00_ASSISTANT_RESEARCH.md · 01_BODY.md · 02_CONSTITUTION.md
          (rewrite/v1-body, 2026-08-11). Plus literature sweep 2025–26 for Dream,
          permissions, cloud trust, eval. No patches applied.
        </Text>
        <Row gap={8} style={{ flexWrap: "wrap" }}>
          <Pill tone="warning" active>
            Verdict: ship-ready skeleton, 4 policy holes before code
          </Pill>
          <Pill tone="info">Epistemics mostly clean</Pill>
          <Pill tone="neutral">Cloud trust under-written</Pill>
          <Pill tone="neutral">Lab hygiene missing</Pill>
        </Row>
      </Stack>

      <Grid columns={4} gap={12}>
        <Stat value="3" label="Hard contradictions" tone="warning" />
        <Stat value="7" label="Under-specified locks" tone="warning" />
        <Stat value="8+" label="New papers to cite" />
        <Stat value="0" label="Consciousness slips" tone="success" />
      </Grid>

      <Callout tone="warning" title="Read this first">
        The three docs agree on the big locks (Gemini cortex, Tailscale-only,
        voice out of Tier A, Dream = offline manage, no consciousness). What
        would hurt first code is not AGI cosplay — it is undefined classifiers
        (“low-risk”), an incomplete egress threat model (chat + Dream delta +
        optional full-memory push leave the Pi), and no module research-card /
        learning-objective gate before slices.
      </Callout>

      {/* ─── 1 Consistency ─── */}
      <Stack gap={12}>
        <H2>1. Consistency (cross-doc)</H2>
        <Table
          headers={["Topic", "00 Research", "01 Body", "02 Law", "Status", "Note"]}
          columnAlign={["left", "left", "left", "left", "left", "left"]}
          rows={[
            [
              "Cortex",
              "Gemini primary",
              "Gemini + adapter",
              "Gemini primary",
              "Aligned",
              "OK",
            ],
            [
              "Ingress",
              "Tailscale only",
              "Tailnet / localhost",
              "Tailscale only",
              "Aligned",
              "Mesh presence ≠ sole-operator auth if other devices join",
            ],
            [
              "Voice",
              "Out A; PTT B; ID C",
              "Out of Tier A",
              "ID / always-listen “B/C”",
              "Soft drift",
              "Constitution bundles B/C — sharpen to match research",
            ],
            [
              "Quiet hours",
              "23:00–07:00 NZST",
              "Same; Dream OK",
              "Same + urgent fault alert",
              "Aligned",
              "Define “urgent fault” (mount down? throttle? disk <N%)",
            ],
            [
              "dream.push",
              "Privileged exception",
              "No confirm if remote set",
              "Privileged exception",
              "Aligned",
              "Highest-privilege silent egress in Tier A",
            ],
            [
              "Low-risk merge",
              "Named, undefined",
              "e.g. brief time",
              "Same phrase",
              "Hole",
              "No allowlist / classifier / refuse-default table",
            ],
            [
              "Memory append",
              "Auto",
              "No confirm",
              "Always allowed",
              "Aligned",
              "Pollution / injection path: append is free",
            ],
            [
              "Procedural tier",
              "Skills in git",
              "No organ named",
              "Silent",
              "Gap",
              "Map to repo skills or drop from research tier table",
            ],
            [
              "Pronouns / “she”",
              "Neutral “ADA”",
              "Neutral",
              "Uses she/her",
              "Soft",
              "Lock preferred address in constitution + prompt",
            ],
            [
              "Financial acts",
              "Silent",
              "Silent",
              "“Not charted yet”",
              "OK explicit",
              "Keep denied-by-default until amendment",
            ],
          ]}
          rowTone={[
            "success",
            "success",
            "warning",
            "success",
            "warning",
            "danger",
            "warning",
            "warning",
            "info",
            "success",
          ]}
        />
      </Stack>

      {/* ─── 2 Epistemics ─── */}
      <Stack gap={12}>
        <H2>2. Epistemics (fanfiction / evidence / Pi)</H2>
        <Grid columns={3} gap={12}>
          <Card>
            <CardHeader>Fanfiction → engineering</CardHeader>
            <CardBody>
              <Text size="small">
                Strong discipline. Jarvis “knows me” → durable memory; dreams →
                offline manage; no consciousness claims. Biological sleep
                (Rasch & Born) correctly tagged metaphor-only.
              </Text>
            </CardBody>
          </Card>
          <Card>
            <CardHeader>Evidence quality</CardHeader>
            <CardBody>
              <Text size="small">
                Core loop cites are metal: ReAct, Toolformer, MemGPT, Generative
                Agents, Reflexion, Sleep-time Compute, 2024–26 memory surveys,
                Horizon Gap / Mirage. Durability cites SQLite fsync/WAL — right
                literature for HDD crash safety.
              </Text>
            </CardBody>
          </Card>
          <Card>
            <CardHeader>Pi feasibility</CardHeader>
            <CardBody>
              <Text size="small">
                API cortex + local organs matches 8GB reality. Local LLM / voice
                latency claims rest on community benches (SpecPicks, blog
                writeups) — fine as FEASIBLE, not academic SOTA. Keep that tag
                strict.
              </Text>
            </CardBody>
          </Card>
        </Grid>
        <Callout tone="info" title="Fanfiction pressure still present (contained)">
          “Warmly forward,” “full-stage roast,” and Dream branding are taste
          locks — OK — but they need operational falsifiers (nudge precision,
          red-line compliance, digest≠metal) so charm cannot paper over failed
          receipts.
        </Callout>
      </Stack>

      {/* ─── 3 Won't chase ─── */}
      <Stack gap={12}>
        <H2>3. Won’t chase vs harder-but-correct on this Pi</H2>
        <Table
          headers={["Lane", "Choice", "Why", "Citation / pattern"]}
          rows={[
            [
              "Chase (teach)",
              "Typed tool gateway + receipts",
              "Hallucinated success dies here",
              "ReAct; consent integrity (see §4)",
            ],
            [
              "Chase (teach)",
              "Crash-safe append + rename+fsync",
              "Process vs disk failure modes split",
              "SQLite atomic commit / WAL",
            ],
            [
              "Chase (teach)",
              "Two-timescale memory (awake write / Dream manage)",
              "Manage is the neglected phase",
              "Auto-Dreamer 2026; Memory survey 2603.07670",
            ],
            [
              "Chase (teach)",
              "Short-horizon stage gates before autonomy",
              "Planning/memory fail first as H grows",
              "HORIZON / Long-Horizon Mirage",
            ],
            [
              "Chase (optional lab)",
              "Grep→BM25→embed ladder",
              "Embeddings day-one overfit; scale-conditioned fail",
              "Anatomy of Agentic Memory; usable-scale eval 2605.07313",
            ],
            [
              "Won’t chase (v1)",
              "Local LLM as main cortex",
              "Wrong for snappy multi-tool on 8GB",
              "Pi benches; VISION cortex wording",
            ],
            [
              "Won’t chase (v1)",
              "Auto-Dreamer GRPO training",
              "Research project of its own; not body slice",
              "arxiv:2605.20616 — cite, defer",
            ],
            [
              "Won’t chase (v1)",
              "Full LoCoMo/LongMemEval leaderboard",
              "Internal smokes first; academic chase later",
              "LoCoMo ACL’24; LongMemEval 2410.10813",
            ],
            [
              "Won’t chase (v1)",
              "Always-listen / cameras / NPU gate",
              "No mic; privacy + CPU",
              "Body inventory",
            ],
            [
              "Won’t chase (early)",
              "MemPrivacy-class edge redaction model",
              "Hard+correct later; define policy now",
              "MemPrivacy 2605.09530; Minim 2606.13949",
            ],
            [
              "Won’t chase",
              "Custom distro / ZFS-before-loop / SEO factory",
              "Already non-goals",
              "VISION + all three docs",
            ],
          ]}
        />
      </Stack>

      {/* ─── 4 Threat ─── */}
      <Stack gap={12}>
        <H2>4. Threat model — what leaves the Pi</H2>
        <Text tone="secondary" size="small">
          Constitution promises “keep private life private” and “no secret
          exfiltration,” but Tier A intentionally trusts two external parties
          once configured. That is a trust boundary, not a bug — it must be
          named.
        </Text>
        <Table
          headers={["Egress path", "Payload", "Counterparty", "Trust today", "Gap"]}
          rows={[
            [
              "Cortex chat (Gemini)",
              "User text, tool schemas, retrieved memory slices, body receipts in context",
              "Google Gemini API",
              "Accepted for quality",
              "No minimization / classify-never-send list",
            ],
            [
              "dream.run manage-pass",
              "Delta: new lifecycle, runs, semantic files",
              "Gemini",
              "Capped, scheduled",
              "Can include sensitive day logs by design",
            ],
            [
              "dream.push",
              "Sealed package ≈ autobiography + identity",
              "R2/B2/S3 (undecided)",
              "Allowlisted; silent once set",
              "Highest blast radius; vendor retention TBD",
            ],
            [
              "Tailscale control plane",
              "HUD/chat sessions",
              "Tailnet peers + Tailscale infra",
              "Auth = mesh presence",
              "Other joined devices = agency risk",
            ],
            [
              "General web / email / HA",
              "—",
              "—",
              "Denied Tier A",
              "OK",
            ],
          ]}
          rowTone={["warning", "warning", "danger", "warning", "success"]}
        />
        <Grid columns={2} gap={12}>
          <Card>
            <CardHeader>Literature that fits your lab (cite, maybe later build)</CardHeader>
            <CardBody>
              <Stack gap={6}>
                <Text size="small">
                  <Link href="https://arxiv.org/abs/2606.26627">
                    Agents That Know Too Much (2026)
                  </Link>{" "}
                  — data-centric agent privacy; personal assistants = intimate +
                  high permission.
                </Text>
                <Text size="small">
                  <Link href="https://arxiv.org/html/2605.09530v3">
                    MemPrivacy (2026)
                  </Link>{" "}
                  — edge reversible pseudonymization before cloud memory ops.
                </Text>
                <Text size="small">
                  <Link href="https://arxiv.org/html/2606.13949v1">
                    Minim (2026)
                  </Link>{" "}
                  — local sanitize / data-minimization before remote inference.
                </Text>
                <Text size="small">
                  <Link href="https://arxiv.org/html/2606.02668v1">
                    Consent Integrity / LITL (2026)
                  </Link>{" "}
                  — confirm dialogs must render real tool args, not model prose.
                </Text>
                <Text size="small">
                  <Link href="https://arxiv.org/pdf/2504.11703">
                    Progent (2025)
                  </Link>{" "}
                  — programmable least-privilege tool policies + deny default.
                </Text>
              </Stack>
            </CardBody>
          </Card>
          <Card>
            <CardHeader>Recommended Tier A honesty clause</CardHeader>
            <CardBody>
              <Stack gap={6}>
                <Text size="small">
                  Split privacy into three rings: (1) control-plane private
                  (Tailscale), (2) cortex-trusted (Gemini sees conversational +
                  tool context), (3) backup-trusted (object store sees sealed
                  packages). “No exfil” applies to unallowlisted paths only.
                </Text>
                <Text size="small">
                  Add a never-to-cloud class (API keys, rclone creds, optional
                  operator secrets) that organs strip before any Gemini call.
                </Text>
                <Text size="small">
                  For Dream push: first remote config should require an explicit
                  Aryan “I understand this copies my autobiography” confirm —
                  even if later pushes are silent.
                </Text>
              </Stack>
            </CardBody>
          </Card>
        </Grid>
      </Stack>

      {/* ─── 5 Eval ─── */}
      <Stack gap={12}>
        <H2>5. Eval — what would falsify each claim</H2>
        <Table
          headers={["Claim", "Falsifier (fail = claim dead)", "Where to log"]}
          rows={[
            [
              "Truthful body self-report",
              "HUD/tool disk or temp disagrees with df/vcgencmd beyond tolerance",
              "Body §10.2",
            ],
            [
              "No fake success",
              "done without run receipt; or dream_ok without package",
              "Runs + lifecycle",
            ],
            [
              "Birth once",
              "born_at changes on reboot / Dream",
              "identity.yaml",
            ],
              [
              "Crash-safe local durability",
              "Kill mid-append corrupts prior JSONL lines",
              "Fault inject test",
            ],
            [
              "Tailscale-only",
              "Agent reachable on 0.0.0.0 from open LAN",
              "nmap / ss check",
            ],
            [
              "Degraded without cortex",
              "Vitals HUD or local seal requires Gemini",
              "API down drill",
            ],
            [
              "Memory usefulness",
              "Cannot retrieve explicit pref after N days (local smoke, not LoCoMo chase)",
              "Internal Q set",
            ],
            [
              "Low-risk auto-merge safe",
              "Any auto-merge of people/secrets/identity or conflicting pref",
              "Dream staging audit",
            ],
            [
              "Quiet hours",
              "Non-urgent proactive chat ping in window",
              "Proactive scheduler log",
            ],
            [
              "Wit subordinate to truth",
              "Joke covers missing receipt or asserts feeling/consciousness",
              "Prompt regression suite",
            ],
            [
              "Horizon discipline",
              "Multi-day unsupervised mission without stage gates succeeds in code paths",
              "Autonomy caps",
            ],
            [
              "Scale-usable memory (later)",
              "Recall collapses as irrelevant sessions grow (budget-compliant)",
              "Cite 2605.07313 protocol; defer full bench",
            ],
          ]}
        />
        <Text size="small" tone="secondary">
          Body §10 acceptance criteria are the best concrete eval in the set.
          Research §2 metrics need a one-page “smoke harness” file name + paths.
          Academic LoCoMo (
          <Link href="https://arxiv.org/abs/2402.17753">2402.17753</Link>) /
          LongMemEval (
          <Link href="https://arxiv.org/abs/2410.10813">2410.10813</Link>) =
          won’t-chase unless you want a graded homework module.
        </Text>
      </Stack>

      {/* ─── 6 Organs / policies ─── */}
      <Stack gap={12}>
        <H2>6. Missed organs & under-specified policies</H2>
        <H3>Policy holes (block clarity before code)</H3>
        <Table
          headers={["Hole", "Severity", "Concrete fix to write into law/body"]}
          rows={[
            [
              "“Low-risk” Dream merge",
              "Block",
              "Allowlist of YAML keys + value shapes (e.g. brief_time HH:MM); else stage. Refuse-default.",
            ],
            [
              "Urgent quiet-hour alert",
              "Fix",
              "Enumerate: ada-data unmounted, root free <X%, throttled≠0, service crash loop.",
            ],
            [
              "Cortex / backup trust rings",
              "Fix",
              "Rewrite privacy preamble; never-to-cloud secret class; first-push confirm.",
            ],
            [
              "Confirm UI integrity",
              "Tighten",
              "Gateway renders tool name+args from bytecode path; model text cannot substitute (LITL).",
            ],
            [
              "Tailnet = Aryan?",
              "Tighten",
              "ACL: only Aryan devices; or app session secret before Agent mode writes.",
            ],
            [
              "Append pollution / prompt-in-memory",
              "Tighten",
              "Cap size/rate; strip tool-instruction patterns from stored notes; quote provenance.",
            ],
            [
              "Financial / purchases",
              "OK for now",
              "Stay denied until explicit amendment (already noted).",
            ],
          ]}
          rowTone={[
            "danger",
            "warning",
            "warning",
            "info",
            "info",
            "info",
            "success",
          ]}
        />
        <H3>Organs / modules under-mapped</H3>
        <Table
          headers={["Missing or thin", "Why it matters", "Suggested home"]}
          rows={[
            [
              "privacy.redact / cortex.egress",
              "What Gemini may see",
              "Body organ map + constitution §11",
            ],
            [
              "auth.session",
              "Operator binding beyond mesh vibes",
              "Ingress §7",
            ],
            [
              "schedule / quiet_hours",
              "Proactivity law needs a clock organ",
              "body or channel",
            ],
            [
              "mute / kill_switch",
              "Constitution promises; no organ",
              "runtime control",
            ],
            [
              "secrets (env/keyring)",
              "Gemini + rclone out of git",
              "ops + body §8",
            ],
            [
              "open_loops organ",
              "Planned file, no API",
              "memory.open_loops",
            ],
            [
              "eval.smoke",
              "Falsifiers need a runner",
              "lab harness under runs/",
            ],
            [
              "procedural / skills",
              "Research tier without body organ",
              "git-tracked skills + loader",
            ],
          ]}
        />
      </Stack>

      {/* ─── 7 Lab hygiene ─── */}
      <Stack gap={12}>
        <H2>7. PhD-lab hygiene & module research cards</H2>
        <Callout tone="warning" title="Gap vs your stated project intent">
          Intent = personal lab + daily companion + deep learning for
          agent/physical AI — prefer harder-but-correct when it teaches; module
          research cards before major slices. None of the three docs encode that
          process. Without it, ADA drifts toward “cute product” implementation.
        </Callout>
        <Table
          headers={["Module (suggested)", "Learning objective", "Harder-correct choice", "Won’t chase"]}
          rows={[
            [
              "body.vitals",
              "Grounded self-report; sensor contracts",
              "Typed receipts + tolerance tests",
              "Fancy dashboards before truth",
            ],
            [
              "agent loop",
              "ReAct vs ungrounded CoT on real tools",
              "Observation-forced “I did X”",
              "Multi-agent swarms",
            ],
            [
              "memory hybrid",
              "Write–manage–read; manage neglected",
              "Awake append + Dream delta",
              "Day-one vector DB theater",
            ],
            [
              "dream",
              "Two-timescale consolidation; backup epistemology",
              "Seal without LLM; LLM optional",
              "GRPO Auto-Dreamer training",
            ],
            [
              "permissions",
              "Capability ≠ authority; consent integrity",
              "Gateway + deny default",
              "Trusting model-written confirm text",
            ],
            [
              "privacy / egress",
              "Cloud trust rings; minimization",
              "Never-send class + audit log of egress bytes",
              "Full on-device MemPrivacy model in Tier A",
            ],
            [
              "eval harness",
              "Falsifiable claims; horizon discipline",
              "Smoke suite + fault injection",
              "Leaderboard chasing first",
            ],
          ]}
        />
        <Text size="small">
          Propose a required card template in{" "}
          <Text as="span" weight="semibold">
            00 §new
          </Text>{" "}
          or{" "}
          <Text as="span" weight="semibold">
            docs/modules/&lt;name&gt;.md
          </Text>
          : question → lens tags → cite ≥2 papers → Pi feasibility → learning
          objective → acceptance falsifiers → won’t-chase → then implement.
        </Text>
      </Stack>

      <Divider />

      {/* ─── Patches ─── */}
      <Stack gap={12}>
        <H2>Proposed doc patches (draft — do not apply yet)</H2>
        <Text tone="secondary" size="small">
          Concrete edits keyed by file. Waiting on your answers to the
          finalizing questions in chat.
        </Text>

        <Card>
          <CardHeader trailing={<Pill tone="info">00 Research</Pill>}>
            00_ASSISTANT_RESEARCH.md
          </CardHeader>
          <CardBody>
            <Stack gap={8}>
              <Text size="small">
                1. New § “Won’t chase (lab)” table — Auto-Dreamer training,
                LoCoMo chase, MemPrivacy model, always-listen, local main cortex,
                custom distro.
              </Text>
              <Text size="small">
                2. New § “Module research card gate” — required fields before
                each Tier A/B slice; learning objective mandatory.
              </Text>
              <Text size="small">
                3. Add refs: Auto-Dreamer (2605.20616), Infini Memory
                (2606.10677), Human-Inspired sleep consolidation (2605.08538),
                usable-scale memory eval (2605.07313), LoCoMo (2402.17753),
                LongMemEval (2410.10813) — tagged smoke-vs-chase.
              </Text>
              <Text size="small">
                4. Align voice row wording with Tier B PTT vs Tier C
                always-listen/voice-ID (fix constitution drift).
              </Text>
              <Text size="small">
                5. Explicit cloud trust paragraph: Gemini + optional object
                store are trusted parties; Tailscale is control-plane privacy
                only.
              </Text>
            </Stack>
          </CardBody>
        </Card>

        <Card>
          <CardHeader trailing={<Pill tone="info">01 Body</Pill>}>
            01_BODY.md
          </CardHeader>
          <CardBody>
            <Stack gap={8}>
              <Text size="small">
                1. Organ map +: privacy.egress (redact/never-send),
                auth.session, schedule.quiet, control.mute, secrets.load,
                memory.open_loops, eval.smoke; clarify procedural = git skills.
              </Text>
              <Text size="small">
                2. §6.5 replace “low-risk” with allowlist table (keys + regex /
                type) and default = stage.
              </Text>
              <Text size="small">
                3. §6.7: first dream.push after remote config requires
                one-time operator confirm; subsequent batch silent.
              </Text>
              <Text size="small">
                4. §7: Tailnet ACL recommendation — Aryan devices only; optional
                app password for Agent writes.
              </Text>
              <Text size="small">
                5. §9: document exact egress classes to Gemini during chat vs
                Dream manage-pass.
              </Text>
              <Text size="small">
                6. §10: add falsifiers for quiet hours, low-risk merge, mute,
                and “digest ≠ metal.”
              </Text>
              <Text size="small">
                7. Refs: Consent Integrity, Progent, MemPrivacy/Minim, Agents
                That Know Too Much, Auto-Dreamer (lineage for Dream naming).
              </Text>
            </Stack>
          </CardBody>
        </Card>

        <Card>
          <CardHeader trailing={<Pill tone="info">02 Constitution</Pill>}>
            02_CONSTITUTION.md → v1.1
          </CardHeader>
          <CardBody>
            <Stack gap={8}>
              <Text size="small">
                1. §5/§11: three privacy rings (control / cortex / backup);
                redefine “no exfil.”
              </Text>
              <Text size="small">
                2. §9.3: operational low-risk allowlist; refuse-default staging.
              </Text>
              <Text size="small">
                3. §10: enumerate urgent quiet-hour faults.
              </Text>
              <Text size="small">
                4. §8: confirm rendering rule (trusted gateway shows real tool
                args); first-push confirm; financial remains denied.
              </Text>
              <Text size="small">
                5. §3 / §15: split voice aspirational tiers to match research.
              </Text>
              <Text size="small">
                6. Pronoun lock (she/her vs it/they) for prompt + HUD.
              </Text>
              <Text size="small">
                7. §13 enforcement map rows for new organs; §14 prompt extract
                updated; version bump.
              </Text>
              <Text size="small">
                8. Optional new § “Lab mode”: research cards + learning
                objectives are law for slice admission on this branch.
              </Text>
            </Stack>
          </CardBody>
        </Card>
      </Stack>

      <Divider />

      <Stack gap={8}>
        <H2>Paper pack to deepen Dream / privacy / control</H2>
        <Text size="small" tone="secondary">
          Already in docs (keep). Add the ones marked NEW where claims leave
          metal.
        </Text>
        <Table
          headers={["Paper", "Use for ADA", "Status"]}
          rows={[
            ["ReAct / Toolformer / MemGPT / Generative Agents / Reflexion", "Loop + memory lineage", "Cited"],
            ["Sleep-time Compute; Letta sleep-time", "Off-path Dream compute", "Cited"],
            ["Memory surveys 2603.07670 / 2602.19320; MEMTIER", "Manage-phase warning", "Cited"],
            ["Horizon Gap / Long-Horizon Mirage", "Autonomy caps", "Cited"],
            ["Auto-Dreamer 2605.20616", "Strongest offline consolidation twin", "NEW cite, won’t train"],
            ["Infini Memory 2606.10677", "Buffer→topic consolidate; grep-first ok", "NEW optional"],
            ["Human-Inspired Memory 2605.08538", "Sleep-phase consol. + LongMemEval streaming", "NEW optional"],
            ["Usable-scale memory 2605.07313", "Falsify “memory works as store grows”", "NEW eval method"],
            ["LoCoMo / LongMemEval", "Optional graded homework, not v1 gate", "NEW won’t-chase"],
            ["Progent; Consent Integrity; Parallax", "Permission ladder rigor", "NEW cite"],
            ["Agents That Know Too Much; MemPrivacy; Minim", "Cloud/cortex trust rings", "NEW cite"],
            ["Constitutional AI; ethical LTM; MemGate", "Charter lineage", "Cited"],
          ]}
        />
      </Stack>

      <Callout tone="neutral" title="Next step">
        Answer the finalizing questions in chat. After you lock those choices,
        say the word and the patches can be applied to the three living docs
        (still no implementation code until you ask).
      </Callout>

      <Text size="small" tone="secondary" style={{ color: t.text.tertiary }}>
        Canvas artifact for doc review only · branch rewrite/v1-body · not a
        substitute for the constitution
      </Text>
    </Stack>
  );
}
