# HomeOps AI v0.2 — Bedrock upgrade

## What changed

- Added robust Amazon Bedrock Runtime `Converse` integration.
- Added recommended Amazon Nova 2 Lite configuration.
- Added explicit `/api/bedrock/test` live connectivity test.
- Added `/api/bedrock/status` configuration status.
- Added **Test Bedrock** button and truthful UI states: off → configured → live/error.
- Added AWS request ID, model ID, latency and token-usage evidence to invoice reviews.
- Added automatic SQLite migration for existing local databases.
- Added graceful fallback so an AWS outage can never bypass or change deterministic commercial controls.
- Expanded automated tests from 5 to 9.

## Safe upgrade from v0.1

Your existing `.env` and `data/homeops.db` can be retained. The application will add the new invoice evidence columns automatically on startup.

After replacing the code files, activate the existing virtual environment and run:

```powershell
python -m pip install -e ".[dev]"
pytest -v
```

Then configure Bedrock according to `docs/AWS_BEDROCK_SETUP.md`.
