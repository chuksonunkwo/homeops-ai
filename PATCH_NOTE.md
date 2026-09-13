# HomeOps AI v0.3 API Test Lifespan Fix

## Symptom

`pytest -v` reports three failures with:

`RuntimeError: StreamableHTTPSessionManager.run() can only be called once`

while the application itself runs normally.

## Root cause

`tests/test_api.py` created a separate Starlette `TestClient` context in each
API test. Each context re-entered the application lifespan. HomeOps has one MCP
Streamable HTTP session manager attached to the application instance, and that
manager is intentionally single-run.

## Fix

The API test module now uses one module-scoped `TestClient` fixture. This keeps
one ASGI lifespan for all API tests while each test still resets HomeOps domain
state when isolation is required.

## Apply

Copy `tests/test_api.py` over the existing file, then run:

```powershell
pytest -v
```

No application code, `.env`, database, or virtual environment is changed by
this patch.
