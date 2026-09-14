from __future__ import annotations

import importlib


def test_blank_vercel_port_falls_back(monkeypatch):
    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.setenv("PORT", "")
    monkeypatch.setenv("HOMEOPS_PORT", "8000")

    import app.config as config

    reloaded = importlib.reload(config)
    assert reloaded.APP_PORT == 8000
