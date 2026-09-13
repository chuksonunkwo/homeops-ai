# HomeOps AI v0.3 Upgrade

This upgrade is designed to be copied over an existing v0.2 installation.

## Preserved local files

The upgrade package intentionally excludes:

- `.env`
- `.venv/`
- `data/`
- local SQLite databases

## Upgrade steps on Windows

1. Stop the running app with `Ctrl+C`.
2. Extract the v0.3 upgrade ZIP over your existing HomeOps folder.
3. Choose **Replace files** when prompted.
4. Activate your Python 3.12 environment:

```powershell
.venv\Scripts\activate
python --version
```

5. Refresh editable installation:

```powershell
python -m pip install -e ".[dev]"
```

6. Run validation:

```powershell
pytest -v
python -m scripts.demo_flow
```

7. Start:

```powershell
python run.py
```

Open `http://127.0.0.1:8000`.

## Expected validation

- `24 passed`
- `RECOMMENDATION KlimaPro`
- `INVOICE_DECISION HOLD_FOR_APPROVAL`
- `VARIANCE 40.0`

## New v0.3 capabilities

- judge-mode UI
- HVAC / plumbing / safety-stop scenarios
- stateful conversation router
- cheapest / fastest / recommended selection intents
- rescheduling
- dynamic suggestions
- invoice challenge and explicit variance override
- 12 MCP tools
- expanded 24-test suite
