from fastapi.testclient import TestClient

from tickster.__main__ import app

client = TestClient(app)


def test_add_api_version():
    payload = {
        "event": "test",
        "data": {"message": "hello"}
    }
    response = client.post("/stable/upstox/postback", json=payload)
    assert response.status_code == 200
    assert response.json() == {"status": "ok", 'api_version': 'v1'}
