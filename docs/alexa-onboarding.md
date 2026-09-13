# Alexa+ Onboarding Notes

## Current project mode

HomeOps AI is deliberately built so the hackathon demo does not depend on privileged Alexa+ onboarding access.

The repository already contains:

- an MCP-native tool implementation
- the official Python SDK integration point
- Streamable HTTP transport
- a web-based simulated Alexa+ experience using the same backend logic

## Verified Amazon requirements relevant to this project

Amazon's Alexa+ documentation currently states that MCP servers must use **Streamable HTTP**. It also documents OAuth 2.1/account-linking requirements for direct onboarding, including PKCE for authorization-code flows.

Amazon's documentation also states that MCP Toolkit availability can be restricted to select partners. The hackathon rules provide a simulated-experience route for Alexa+ entrants, so the project can remain eligible and demonstrable even without direct toolkit access.

## Direct-onboarding path when access is available

Amazon's documented CLI flow begins with:

```bash
alexa-ai configure
```

Then scaffold an MCP add-on against the deployed server URL:

```bash
alexa-ai new mcp --name "HomeOps AI" --locale en-US --mcp-server-url "https://YOUR-HOST/mcp"
```

The generated add-on package should then be completed with the descriptions, example phrases, privacy/terms URLs and media assets required by the CLI schema before deployment.

Deploy using:

```bash
alexa-ai deploy
```

Do not hand-invent the final `addon.json` schema in advance; use the current Alexa AI CLI so the package matches Amazon's then-current schema.

## Authentication gap

The current hackathon MVP does **not** claim production Alexa+ account-linking compliance. Before direct Alexa+ onboarding, implement and test the authorization server requirements in the current Amazon documentation, including:

- protected resource metadata
- OAuth authorization-server metadata
- OAuth 2.1 authorization code with PKCE S256
- resource parameter validation
- bearer-token validation on MCP requests
- service-level client-credentials support if required by the chosen onboarding path

This is intentionally documented rather than hidden.
