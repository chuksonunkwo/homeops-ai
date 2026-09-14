# Vercel blank PORT startup fix

Vercel runtime logs showed `PORT` present as an empty string. The previous code called `int("")` during import, causing `asgi.py` startup to fail before `/health` could respond.

The fix treats missing or blank integer environment variables as defaults. `APP_PORT` now falls back to `HOMEOPS_PORT`, then `8000`.
