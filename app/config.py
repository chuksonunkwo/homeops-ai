from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
try:
    from dotenv import load_dotenv

    load_dotenv(BASE_DIR / ".env")
except ImportError:
    pass

DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
IS_VERCEL = bool(os.getenv("VERCEL"))

# Vercel's deployed filesystem is read-only except /tmp. A configured
# DATABASE_URL is the durable production path; /tmp is only a safe fallback
# for health checks or short-lived preview experiments.
if DATABASE_URL:
    DATA_DIR = Path(os.getenv("HOMEOPS_DATA_DIR", "/tmp/homeops" if IS_VERCEL else BASE_DIR / "data"))
elif IS_VERCEL:
    DATA_DIR = Path(os.getenv("HOMEOPS_DATA_DIR", "/tmp/homeops"))
else:
    DATA_DIR = Path(os.getenv("HOMEOPS_DATA_DIR", BASE_DIR / "data"))

DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = Path(os.getenv("HOMEOPS_DB_PATH", DATA_DIR / "homeops.db"))

def _env_int(name: str, default: int) -> int:
    """Read an integer env var, treating missing or blank values as default."""
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    return int(raw.strip())


APP_HOST = os.getenv("HOMEOPS_HOST", "127.0.0.1")
# Vercel can expose PORT as an empty string in serverless functions.
# Fall back to HOMEOPS_PORT, then 8000, instead of crashing at import time.
_port_raw = os.getenv("PORT")
if _port_raw is None or not _port_raw.strip():
    APP_PORT = _env_int("HOMEOPS_PORT", 8000)
else:
    APP_PORT = int(_port_raw.strip())

vercel_url = os.getenv("VERCEL_URL", "").strip()
production_url = os.getenv("VERCEL_PROJECT_PRODUCTION_URL", "").strip()
default_public_url = f"https://{production_url or vercel_url}" if (production_url or vercel_url) else "http://127.0.0.1:8000"
PUBLIC_BASE_URL = os.getenv("HOMEOPS_PUBLIC_BASE_URL", default_public_url)

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
AWS_PROFILE = os.getenv("AWS_PROFILE", "")
BEDROCK_ENABLED = os.getenv("BEDROCK_ENABLED", "false").lower() == "true"
BEDROCK_MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "")
BEDROCK_MAX_TOKENS = _env_int("BEDROCK_MAX_TOKENS", 120)
BEDROCK_READ_TIMEOUT_SECONDS = _env_int("BEDROCK_READ_TIMEOUT_SECONDS", 90)

vercel_hosts = [x for x in {vercel_url, production_url} if x]
vercel_origins = [f"https://{x}" for x in vercel_hosts]

_default_hosts = ["127.0.0.1", "127.0.0.1:*", "localhost", "localhost:*", *vercel_hosts]
_default_origins = ["http://127.0.0.1:8000", "http://localhost:8000", *vercel_origins]

MCP_ALLOWED_HOSTS = [
    x.strip()
    for x in os.getenv("MCP_ALLOWED_HOSTS", ",".join(_default_hosts)).split(",")
    if x.strip()
]
MCP_ALLOWED_ORIGINS = [
    x.strip()
    for x in os.getenv("MCP_ALLOWED_ORIGINS", ",".join(_default_origins)).split(",")
    if x.strip()
]
