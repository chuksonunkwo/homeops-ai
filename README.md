# HomeOps AI v0.4 — Consumer UX Build

**HomeOps AI** is an MCP-first home-services agent built for the 2026 Amazon Developer Hackathon. It turns a request such as **“My AC isn't cooling. Handle it.”** into a governed workflow covering provider sourcing, recommendation, explicit approval, scheduling, completion, final-bill review and cost-overrun control.

## Hackathon positioning

- **Primary track:** Alexa+
- **Mini challenge:** Open Source
- **Optional later mini challenge:** AWS Builder
- **Submission path:** real MCP server + simulated Alexa+ conversational experience
- **License:** MIT

The browser experience and MCP tools use the same deterministic `HomeOpsEngine`. Amazon Bedrock remains optional; the core demo works without AWS credentials.

## What changed in v0.4

v0.4 separates the customer experience from hackathon proof.

### Home view

The default interface is designed for a non-technical homeowner:

- one clear landing question: **What needs fixing?**
- one primary action at a time
- recommendation-first provider selection
- provider comparison hidden until requested
- plain-English cost controls: **Agreed price / Final bill / Extra cost**
- guided loading, success, safety and recovery states
- responsive single-column mobile behaviour
- keyboard focus, skip link, reduced-motion support and non-colour status labels

### Demo / Judge view

Technical evidence is still available behind **View demo details**:

- three repeatable hackathon scenarios
- MCP runtime status
- 12-tool catalog evidence
- deterministic policy outcome
- optional Bedrock evidence
- recent audit trail
- architecture flow

This keeps the product simple without hiding the implementation from judges.

## Golden demo

1. User enters: `My AC isn't cooling. Handle it.`
2. HomeOps checks for safety issues and sources three synthetic providers.
3. `KlimaPro` is recommended at **$95**.
4. User approves KlimaPro and the visit is scheduled.
5. Work is marked complete.
6. A **$135** final bill is reviewed.
7. HomeOps identifies a **$40 / 42.1%** unapproved increase.
8. The customer sees: **The final bill is $40 higher than agreed**.
9. Primary action: **Ask provider to explain**.
10. Payment remains on hold unless the customer explicitly approves the extra cost.

## Architecture

```text
Alexa+ / consumer web experience
             |
             v
     Streamable HTTP MCP
             |
             v
      Conversation router
             |
             v
        HomeOps Engine
        /           \
 SQLite/Postgres   Amazon Bedrock (optional explanation layer)
             |
             v
          Audit log
```

Safety and commercial approvals are deterministic. Bedrock, when enabled, can explain an already-determined control result but cannot change approval status.

## MCP tools

1. `create_service_request`
2. `diagnose_service_request`
3. `search_providers`
4. `request_quotes`
5. `compare_quotes`
6. `approve_provider`
7. `schedule_service`
8. `get_service_job`
9. `record_service_completion`
10. `submit_and_review_invoice`
11. `challenge_invoice_variance`
12. `close_service_job`

When the MCP package is installed, the transport endpoint is `/mcp`.

## Local setup — Python 3.12

```powershell
py -3.12 -m venv .venv
.venv\Scripts\activate
python --version
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
python run.py
```

Open:

```text
http://127.0.0.1:8000
```

Health:

```text
http://127.0.0.1:8000/health
```

MCP transport:

```text
http://127.0.0.1:8000/mcp
```

Do not judge `/mcp` by opening it directly in a browser; it is an MCP transport endpoint and expects MCP session semantics.

## Automated validation

Run:

```powershell
pytest -v
```

Current suite: **28 tests** covering the engine, conversation, API, optional Bedrock behaviour, MCP catalog, and v0.4 UX contract.

Backend demo:

```powershell
python -m scripts.demo_flow
```

Expected control outcome:

```text
RECOMMENDATION KlimaPro
INVOICE_DECISION HOLD_FOR_APPROVAL
VARIANCE 40.0
```

## Optional AWS Builder path

AWS is not required for the core app. Keep:

```env
BEDROCK_ENABLED=false
```

until a real AWS account is deliberately configured. See `docs/AWS_BEDROCK_SETUP.md`.

## Deployment

`Dockerfile` and `render.yaml` are included. For a remote MCP deployment, update:

```env
MCP_ALLOWED_HOSTS=your-domain.example,your-domain.example:*
MCP_ALLOWED_ORIGINS=https://your-domain.example
HOMEOPS_PUBLIC_BASE_URL=https://your-domain.example
```

## Repository structure

```text
app/
  bedrock.py       Optional Bedrock explanation layer
  config.py        Runtime configuration
  conversation.py  Stateful, plain-English conversation router
  engine.py        Domain workflow and deterministic controls
  main.py          Web API + MCP tool registration
  models.py        Data models
  store.py         SQLite persistence and audit trail
static/
  index.html       Consumer-first interface + hidden Judge View
  app.js           Guided state and contextual actions
  styles.css       Responsive accessible design system
scripts/
  demo_flow.py
  test_bedrock.py
tests/
  test_api.py
  test_bedrock.py
  test_conversation.py
  test_engine.py
  test_ui_contract.py
docs/
  UX_V0.4.md
  DEMO_SCRIPT.md
  TEST_MATRIX.md
  UPGRADE_v0.4.md
```

## Demo-data notice

Provider names, prices, ratings and appointment windows are **synthetic demo data**. They are not live provider listings or real-world offers.

## License

MIT.
