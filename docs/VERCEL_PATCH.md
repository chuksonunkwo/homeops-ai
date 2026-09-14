# v0.4.1 Vercel hardening

- Pins Python to the 3.12 line (`~=3.12.0`).
- Adds a recognized ASGI entrypoint (`asgi.py`).
- Uses MCP Streamable HTTP with `stateless_http=True` and `json_response=True` for serverless compatibility.
- Adds PostgreSQL/Neon persistence through `DATABASE_URL` while retaining SQLite locally.
- Automatically includes Vercel system hostnames in MCP host/origin allowlists when system environment variables are exposed.
- Reports the active persistence backend on `/health`.
