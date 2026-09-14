# HomeOps AI - Vercel deployment

## Production architecture

- Vercel Python/ASGI function
- Python 3.12 pinned in `pyproject.toml`
- MCP Streamable HTTP in stateless JSON-response mode
- Neon PostgreSQL via `DATABASE_URL`
- SQLite retained for local development/tests only

## Why PostgreSQL is required

Vercel Functions do not provide a shared persistent filesystem. HomeOps therefore uses SQLite locally and automatically switches to PostgreSQL when `DATABASE_URL` is present.

## Vercel settings

Import the GitHub repository into Vercel. Enable **Automatically expose System Environment Variables** so HomeOps can trust the generated Vercel host/origin automatically.

Add this Environment Variable for Production and Preview:

```text
DATABASE_URL=<Neon pooled PostgreSQL connection string>
```

Optional:

```text
BEDROCK_ENABLED=false
```

No AWS credentials are required for the Alexa+ / Open Source submission path.

## Validation after deployment

Open:

```text
https://<your-project>.vercel.app/
https://<your-project>.vercel.app/health
```

`/health` should include:

```json
{
  "status": "ok",
  "version": "0.4.1",
  "storage_backend": "postgres",
  "mcp_available": true,
  "mcp_endpoint": "/mcp"
}
```

Do not test `/mcp` by opening it as a normal browser page. Validate it with an MCP client/Inspector.
