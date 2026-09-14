# Vercel startup fix — v0.4.2

This patch hardens HomeOps for Vercel startup.

## What changed

- `vercel.json` explicitly includes `static/**` in the Python function bundle.
- Starlette `StaticFiles` no longer aborts module import if the static directory is unavailable during early runtime inspection.
- `pyproject.toml` pins the Vercel entry point explicitly to `asgi:app`.
- Health metadata reports version `0.4.2`.

## Why

The production logs showed an import-time failure for `asgi.py`. The v0.4.1 app constructs `StaticFiles` during module import. Starlette validates the directory immediately by default, so if Vercel does not include `static/` in the function bundle, importing `asgi.py` raises before `/health` can respond.

The explicit `includeFiles` rule plus `check_dir=False` removes that startup failure mode while preserving the same local behavior.
