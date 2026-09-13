# Devpost Submission Draft — v0.4

## Project name

HomeOps AI

## Tagline

Home repairs, handled — from request to provider, appointment and final-bill control.

## Primary track

Alexa+

## Mini challenges

- **Open Source:** planned
- **AWS Builder:** enter only if a real AWS integration is enabled and validated before submission

## What it does

HomeOps AI is a consumer-first conversational home-services agent. A user describes a problem in natural language and HomeOps converts it into an auditable workflow: it creates the service request, checks for emergency language, sources synthetic demo providers, compares normalized quotes, records explicit provider approval, schedules the visit, records completion and checks the final bill against the price the customer agreed.

The signature demo begins with: **“My AC isn't cooling. Handle it.”** HomeOps receives three comparable quotes and recommends KlimaPro at $95 using a transparent score based on price, rating and response speed. After the service is completed, a $135 invoice is submitted. HomeOps identifies the $40 / 42.1% increase, places payment on hold and tells the customer in plain English that the bill is $40 higher than agreed, with **Ask provider to explain** as the primary action.

v0.4 also demonstrates budget-aware plumbing, safety-stop routing for emergency language, natural “cheapest / fastest / recommended” selection, rescheduling, persistent status, provider-explanation challenge, and an explicit human override before a held invoice can close.


## UX approach

The normal customer view deliberately hides MCP status, scoring internals, audit events and architecture. A first-time user sees one question — **What needs fixing?** — and one primary action. HomeOps then reveals only the next meaningful decision. Technical proof remains available behind **View demo details**, allowing judges to inspect MCP status, tool count, audit history and policy evidence without forcing ordinary users to understand developer concepts.

## How it works

The project is MCP-first. The backend registers its operational capabilities as MCP tools using the Python MCP SDK and Streamable HTTP. The simulated Alexa+ web experience invokes the same HomeOps domain engine used by those tools, so the browser demonstration and submitted integration logic share one governed workflow layer.

A deterministic conversation router converts user intent into domain operations. Commercial approvals and emergency decisions do not depend on a language model. Workflow state and an audit trail are persisted locally for the MVP.

Amazon Bedrock is implemented as an optional explanation layer. If enabled and validated, it receives already-determined commercial-control facts and generates a concise rationale. It is not allowed to change the approval decision.

## Why Alexa+

The value is not a single answer; it is multi-step orchestration that persists across the household service lifecycle. HomeOps lets a customer move naturally from intent (“handle my AC”) to sourcing, comparison, approval, scheduling, completion and invoice control without manually coordinating several disconnected systems.

## Open Source contribution

The complete HomeOps AI repository is released under the MIT License. It provides a reusable MCP-first reference architecture for governed service-procurement agents with persistent state, auditable transitions and deterministic commercial controls.

## Optional AWS Builder integration

The repository includes an Amazon Bedrock Runtime integration through the Converse API. The submission will claim AWS Builder participation only if a real Bedrock invocation is configured, tested and evidenced before final submission.

## What was built during the hackathon window

HomeOps AI was created as a new project during the 2026 Amazon Developer Hackathon window. The workflow engine, MCP tool surface, conversational simulator, persistent state, deterministic commercial controls, optional Bedrock adapter, test suite and documentation were developed for this submission.

## Technical highlights

- Streamable HTTP MCP architecture
- **12 operational MCP tools**
- stateful conversational intent routing
- persistent service-job state
- deterministic provider comparison
- budget-aware sourcing
- cheapest / fastest / recommended selection intents
- explicit user approval before award
- scheduling and rescheduling
- emergency-language safety stop
- invoice-vs-quote variance control
- supplier-justification challenge
- explicit variance override before closure
- audit event history
- optional Amazon Bedrock explanation layer
- consumer-first responsive UI with a separate Judge View
- **28 automated tests**

## Important demo-data disclosure

All provider identities, ratings, prices and appointment windows shown in the demo are synthetic. HomeOps AI does not claim to be connected to live providers in the current MVP.
