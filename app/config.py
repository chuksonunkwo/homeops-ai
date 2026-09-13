from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
try:
    from dotenv import load_dotenv

    load_dotenv(BASE_DIR / ".env")
except ImportError:
    pass

DATA_DIR = Path(os.getenv("HOMEOPS_DATA_DIR", BASE_DIR / "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = Path(os.getenv("HOMEOPS_DB_PATH", DATA_DIR / "homeops.db"))

APP_HOST = os.getenv("HOMEOPS_HOST", "127.0.0.1")
APP_PORT = int(os.getenv("PORT", os.getenv("HOMEOPS_PORT", "8000")))
PUBLIC_BASE_URL = os.getenv("HOMEOPS_PUBLIC_BASE_URL", "http://127.0.0.1:8000")

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
AWS_PROFILE = os.getenv("AWS_PROFILE", "")
BEDROCK_ENABLED = os.getenv("BEDROCK_ENABLED", "false").lower() == "true"
BEDROCK_MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "")
BEDROCK_MAX_TOKENS = int(os.getenv("BEDROCK_MAX_TOKENS", "120"))
BEDROCK_READ_TIMEOUT_SECONDS = int(os.getenv("BEDROCK_READ_TIMEOUT_SECONDS", "90"))

# Comma-separated values used by the MCP transport security layer when deployed.
MCP_ALLOWED_HOSTS = [
    x.strip()
    for x in os.getenv(
        "MCP_ALLOWED_HOSTS",
        "127.0.0.1,127.0.0.1:*,localhost,localhost:*",
    ).split(",")
    if x.strip()
]
MCP_ALLOWED_ORIGINS = [
    x.strip()
    for x in os.getenv(
        "MCP_ALLOWED_ORIGINS",
        "http://127.0.0.1:8000,http://localhost:8000",
    ).split(",")
    if x.strip()
]
