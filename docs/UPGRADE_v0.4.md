# Upgrade HomeOps v0.3.1 to v0.4

v0.4 is primarily a UX upgrade. It preserves the existing database, environment file and virtual environment.

## Apply

1. Stop the running app with `Ctrl+C`.
2. Extract the v0.4 upgrade ZIP over the project root.
3. Choose **Replace files in the destination**.
4. Do not delete `.env`, `.venv` or `data/homeops.db`.
5. Run:

```powershell
.venv\Scripts\activate
python --version
python -m pip install -e ".[dev]"
pytest -v
python run.py
```

Expected:

```text
Python 3.12.x
28 passed
```

Open `http://127.0.0.1:8000` and press `Ctrl+F5` if the browser cached the previous UI.
