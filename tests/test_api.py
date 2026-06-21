# tests/test_api.py
from fastapi.testclient import TestClient
from main import app

# Inisialisasi client simulator FastAPI
client = TestClient(app)

def test_api_health_endpoint():
    """Memastikan endpoint /health merespon dengan status 200 dan database aman."""
    response = client.get("/health")
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] == "ok"
    assert "database" in data

def test_api_chatbot_ui_endpoint():
    """Memastikan interface UI web chatbot /chat berhasil dirender dalam format HTML."""
    response = client.get("/chat")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Document Intelligence" in response.text