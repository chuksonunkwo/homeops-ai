import json
from pathlib import Path


def test_vercel_bundle_includes_static_and_entrypoint_is_explicit():
    root = Path(__file__).resolve().parents[1]
    cfg = json.loads((root / 'vercel.json').read_text())
    assert cfg['functions']['asgi.py']['includeFiles'] == 'static/**'
    pyproject = (root / 'pyproject.toml').read_text()
    assert '[tool.vercel]' in pyproject
    assert 'entrypoint = "asgi:app"' in pyproject
