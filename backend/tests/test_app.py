from fastapi.testclient import TestClient
from app.main import create_app
from app.core.config import Settings, get_settings

def test_startup_health():
    with TestClient(create_app()) as client:
        response = client.get('/api/v1/health')
        assert response.status_code == 200
        assert response.json() == {'status': 'ok', 'service': 'crossborder-ai-agent'}
        assert client.get('/docs').status_code == 200

def test_production(monkeypatch):
    monkeypatch.setenv('ENVIRONMENT', 'production')
    get_settings.cache_clear()
    try:
        with TestClient(create_app()) as client:
            assert client.get('/docs').status_code == 404
            assert client.get('/openapi.json').status_code == 404
    finally:
        get_settings.cache_clear()

def test_config(monkeypatch):
    monkeypatch.setenv('DATABASE_URL', 'sqlite:///:memory:')
    assert Settings().database_url == 'sqlite:///:memory:'
