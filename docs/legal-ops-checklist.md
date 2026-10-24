# Legal / ops checklist (operators)

**Disclaimer:** This is **operator guidance** for running Ada and adjacent web properties. It is **not legal advice**. Engage qualified counsel for your jurisdiction, industry, and data-processing agreements.

## Ranking and demand

- Treat **early traffic** as **exploration / waitlist** phase: minimal forms, clear expectations (“we’ll follow up”), no implied guarantees of outcomes or rankings.
- **Lead definition:** Decide later what counts as a qualified lead (e.g. booked call vs form fill). Keep product copy aligned with what you actually measure and hand off to humans.

## Retention and data minimization

- Store only what you need for operations and analytics; document **retention periods** for logs, SQLite exports, and any CRM handoffs.
- Separate **production keys** and **personal data** from marketing experiments; rotate credentials if they ever touched shared channels.

## What must **never** enter LLM context

Do **not** paste or pipe into **`ada chat`**, **`ada daemon`** goals, workflow prompts, or knowledge items:

- **Secrets:** API keys, OAuth tokens, private keys, connection strings, admin passwords.
- **PII / sensitive personal data:** government IDs, full payment card numbers, health records, passwords of end users, private communications unrelated to the published site narrative.
- **Raw inbound user submissions** (forms, emails, support tickets) unless you have an explicit, reviewed process to redact and a lawful basis to use them in content generation.

Use **aggregated or synthetic examples** in prompts and runbooks. If a tool or ingest path could pull user data, **keep it off** or **gate it** until policy and technical controls match.

## Publishing and advertising

- Disclose **sponsored** or **affiliate** relationships where required.
- Keep **privacy policy** and **contact** paths accurate for the live site (ISR / Next app is out of repo but must match real behavior).

## Incident posture

- If sensitive data was accidentally sent to a model provider, follow your **vendor incident** and **breach** procedures; do not rely on this checklist alone.
