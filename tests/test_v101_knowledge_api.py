import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_v101_endpoints():
    # Login as admin
    res_login = client.post("/api/auth/login", json={"username": "admin", "password": "YemenAI2026!"})
    assert res_login.status_code == 200
    token = res_login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. GET /api/knowledge/domains
    res = client.get("/api/knowledge/domains", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "personal_domains" in data

    # 2. GET /api/knowledge/stats
    res_stats = client.get("/api/knowledge/stats", headers=headers)
    assert res_stats.status_code == 200

    # 3. GET /api/personal-context/status
    res_pc = client.get("/api/personal-context/status", headers=headers)
    assert res_pc.status_code == 200
    assert res_pc.json()["status"] in ["imported", "awaiting_source"]
