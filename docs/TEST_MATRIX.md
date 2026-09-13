# HomeOps AI v0.4 Test Matrix

## Automated suite — 28 tests

### Engine

- HVAC service request and quote flow
- deterministic best-value recommendation
- provider approval and scheduling
- invoice at/below agreed price
- unapproved final-bill increase hold
- invoice line-item arithmetic validation
- emergency routing
- supplier explanation/challenge event
- explicit extra-cost approval requirement before closure
- persistence/migration behaviour

### Conversation

- initial HVAC request
- budget extraction
- budget-aware plumbing
- recommended / lowest-price / soonest selection intents
- rescheduling
- completion intent
- amount-only bill handling after completion
- cost-explanation challenge
- explicit extra-cost approval and closure
- status continuity

### API / MCP surface

- health and golden chat flow
- scenario catalog
- 12-tool MCP catalog
- v0.4 health version
- fastest-provider + reschedule flow
- single application lifespan for MCP test client

### Bedrock

- optional/fallback behaviour
- evidence metadata behaviour

### UX contract

- clear consumer landing and primary action
- judge evidence hidden by default
- plain-English cost-exception copy
- keyboard/mobile/reduced-motion accessibility guards

## Manual release checks

- landing understood within 3 seconds
- only one dominant action above the fold
- recommendation-first provider decision
- compare-all hidden until requested
- cost exception understandable without procurement terminology
- mobile single-column flow
- focus indicators visible
- error copy avoids backend details
- Judge View exposes technical evidence without changing consumer flow
