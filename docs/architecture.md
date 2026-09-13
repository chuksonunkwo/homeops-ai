# HomeOps AI Architecture

## Design objective

HomeOps AI is built around one principle: **conversation may initiate a transaction, but governed domain logic controls the transaction.**

The same `HomeOpsEngine` backs the browser simulator and the MCP tools. This avoids a common hackathon anti-pattern where a polished UI is disconnected from the submitted integration code.

## Components

### 1. Conversation surfaces

- Browser-based voice-style simulator for the permitted simulated Alexa+ path.
- Alexa+ MCP client when direct onboarding is available.

### 2. Conversation router

`app/conversation.py` maps natural-language intents onto the governed domain operations. It supports stateful follow-up actions such as cheapest/fastest selection, rescheduling, status, invoice review, supplier challenge and explicit variance override.

The router is deterministic so safety and commercial authorization never depend on an LLM interpretation.

### 3. MCP server

`app/main.py` registers the HomeOps operations using the official MCP Python SDK.

Transport: Streamable HTTP.

The MCP server is mounted into the Starlette application so `/health`, `/api/*`, static UI assets and `/mcp` can be served from one process.

### 4. Domain engine

`app/engine.py` contains the authoritative workflow logic:

```text
OPEN
 -> QUOTING
 -> QUOTES_READY
 -> AWARDED
 -> SCHEDULED
 -> COMPLETED
 -> INVOICE_REVIEW
 -> CLOSED
```

Every transition creates an audit event.

### 5. Commercial controls

Quote recommendation uses a transparent weighted score:

- 50% price
- 30% provider rating
- 20% response speed

Invoice control is deterministic:

```text
invoice <= approved quote
    -> APPROVE

invoice > approved quote
    -> HOLD_FOR_APPROVAL
    -> REQUEST_JUSTIFICATION
```

Bedrock cannot override this decision.

### 6. Persistence

The MVP uses SQLite to keep the repository self-contained. The storage boundary is isolated in `Store`, so Postgres can replace SQLite without changing MCP tool contracts.

Stored entities:

- service jobs
- quotes
- invoices
- audit events

### 7. Amazon Bedrock

`app/bedrock.py` calls the Bedrock Runtime Converse API only when enabled. Its purpose is explanation and user-facing commercial reasoning, not transaction authorization.

If Bedrock is unavailable, the deterministic fallback explanation is returned and the workflow remains operational.

## Zero-trust controls

- Emergency-language detection interrupts normal sourcing.
- No provider can be scheduled before explicit approval.
- Approved quote amount becomes the commercial baseline.
- Invoice line items must mathematically reconcile to the invoice total.
- Positive invoice variance is held, not silently accepted.
- A challenged variance remains on hold and creates a dedicated audit event.
- Job closure requires either a clean invoice or explicit variance override.
- Synthetic provider data is clearly labelled as demo data.

## Production gaps intentionally not hidden

This is a hackathon MVP, not a production home-services marketplace. A production release would still require:

- real provider API / marketplace integration
- identity and account linking
- production OAuth 2.1/PKCE configuration for Alexa+ onboarding
- database migration to managed Postgres
- secrets management
- rate limiting and abuse controls
- idempotency keys for transactional MCP tools
- payment-provider integration
- real appointment calendar integration
- provider verification and insurance/licensing controls
- jurisdiction-specific consumer-protection terms
