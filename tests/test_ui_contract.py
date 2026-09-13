from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
CSS = (ROOT / "static" / "styles.css").read_text(encoding="utf-8")
JS = (ROOT / "static" / "app.js").read_text(encoding="utf-8")


def test_consumer_landing_has_one_clear_primary_request():
    assert "What needs fixing?" in INDEX
    assert "Get help" in INDEX
    assert 'id="start-form"' in INDEX
    assert 'placeholder="e.g. My AC isn\'t cooling"' in INDEX


def test_developer_evidence_is_hidden_behind_judge_view():
    assert 'id="judge-view" class="judge-view" hidden' in INDEX
    assert "View demo details" in INDEX
    assert "Control Tower" not in INDEX
    assert "Voice Simulator" not in INDEX
    assert "Commercial Evaluation" not in INDEX


def test_invoice_exception_copy_is_plain_language():
    assert "Ask provider to explain" in JS
    assert "higher than agreed" in JS
    assert "Extra cost" in JS
    assert "variance" not in INDEX.lower()


def test_accessibility_and_mobile_guards_exist():
    assert ":focus-visible" in CSS
    assert "prefers-reduced-motion" in CSS
    assert "@media (max-width: 720px)" in CSS
    assert 'class="skip-link"' in INDEX
    assert 'aria-live="polite"' in INDEX
