import pytest
from starlette.testclient import TestClient

from app.main import app, store


@pytest.fixture(scope="module")
def client():
    """Keep one ASGI lifespan for the module.

    The MCP StreamableHTTPSessionManager is intentionally single-run per
    application instance. Re-entering the lifespan with a new TestClient for
    every test attempts to run the same MCP session manager more than once.
    """
    with TestClient(app) as test_client:
        yield test_client


def test_health_and_golden_chat_flow(client):
    store.reset()
    health = client.get('/health')
    assert health.status_code == 200
    assert health.json()['status'] == 'ok'

    first = client.post('/api/chat', json={'message': "My AC isn't cooling. Handle it.", 'job_id': None})
    assert first.status_code == 200
    payload = first.json()
    assert payload['action'] == 'QUOTES_READY'
    job_id = payload['job_id']
    assert payload['comparison']['recommended_provider'] == 'KlimaPro'

    selected = client.post('/api/chat', json={'message': 'Choose KlimaPro', 'job_id': job_id})
    assert selected.status_code == 200
    assert selected.json()['action'] == 'PROVIDER_SCHEDULED'

    completed = client.post('/api/chat', json={'message': 'The technician completed the repair', 'job_id': job_id})
    assert completed.json()['action'] == 'COMPLETED'

    invoice = client.post('/api/chat', json={'message': 'The final invoice is $135', 'job_id': job_id})
    assert invoice.status_code == 200
    data = invoice.json()
    assert data['invoice_review']['variance'] == 40.0
    assert data['invoice_review']['decision'] == 'HOLD_FOR_APPROVAL'


def test_demo_scenarios_and_mcp_tool_catalog(client):
    store.reset()
    scenarios = client.get('/api/demo/scenarios')
    assert scenarios.status_code == 200
    assert len(scenarios.json()['scenarios']) == 3
    assert scenarios.json()['scenarios'][2]['id'] == 'emergency'

    tools = client.get('/api/tools')
    assert tools.status_code == 200
    names = tools.json()['tools']
    assert len(names) == 12
    assert 'challenge_invoice_variance' in names


def test_health_reports_v04(client):
    data = client.get('/health').json()
    assert data['version'] == '0.4.1'


def test_api_supports_fastest_selection_and_reschedule(client):
    store.reset()
    first = client.post('/api/chat', json={'message': "My AC isn't cooling. Handle it."}).json()
    job_id = first['job_id']

    selected = client.post('/api/chat', json={'message': 'Choose the fastest', 'job_id': job_id}).json()
    assert selected['job']['selected_provider_id'] == 'coolair'

    moved = client.post('/api/chat', json={'message': 'Reschedule to Friday 2-4 PM', 'job_id': job_id}).json()
    assert moved['action'] == 'SERVICE_RESCHEDULED'
    assert moved['job']['appointment_window'] == 'Friday 2-4 PM'
