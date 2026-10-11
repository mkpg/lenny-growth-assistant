from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "env": "development"}

from unittest.mock import patch

@patch("sqlalchemy.orm.Session.execute", side_effect=Exception("DB Error"))
def test_ready_check_no_db(mock_execute):
    # Since DB is not configured by default in tests without .env, it should return 503
    response = client.get("/ready")
    assert response.status_code == 503
    assert "Database" in response.json().get("detail", response.text)

def test_invalid_provider_model():
    response = client.post("/api/v1/chat", json={
        "question": "test",
        "provider": "google",
        "model": "gemini-3.5-pro"
    })
    assert response.status_code == 400
    assert "Unsupported model" in response.json().get("detail", "")

from unittest.mock import patch
from app.agent import PiAgentError

def test_provider_authentication_error():
    with patch('app.main.call_pi_agent', side_effect=PiAgentError('No API key found for google')):
        response = client.post('/api/v1/chat', json={
            'question': 'test',
            'provider': 'google',
            'model': 'gemini-3.8-flash'
        })
        assert response.status_code == 500
        assert 'Provider authentication failed' in response.json().get('detail', '')

def test_provider_model_not_found_error():
    with patch('app.main.call_pi_agent', side_effect=PiAgentError('models/gemini-1.5-flash is not found or is no longer available')):
        response = client.post('/api/v1/chat', json={
            'question': 'test',
            'provider': 'google',
            'model': 'gemini-3.8-flash'
        })
        assert response.status_code == 502
        assert 'currently unavailable' in response.json().get('detail', '')

def test_provider_timeout_error():
    with patch('app.main.call_pi_agent', side_effect=PiAgentError('timeout reached')):
        response = client.post('/api/v1/chat', json={
            'question': 'test',
            'provider': 'google',
            'model': 'gemini-3.8-flash'
        })
        assert response.status_code == 504
        assert 'took too long' in response.json().get('detail', '')
