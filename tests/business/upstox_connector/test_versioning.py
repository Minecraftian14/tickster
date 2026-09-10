from fastapi.testclient import TestClient

from upstox_connector.__main__ import app

client = TestClient(app)


def test_latest_redirects_to_v3():
    response = client.get("/latest/hello", follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"] == "/v3/hello"


def test_stable_redirects_to_v2():
    response = client.get("/stable/hello", follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"] == "/v1/hello"


def test_v3_uses_its_own_endpoint():
    response = client.get("/v3/hello")
    assert response.status_code == 200
    assert response.json() == {
        "api_version": "v3",
        "message": "Hello from API v3",
    }


def test_v3_falls_back_through_v2_to_v1():
    response = client.get("/v3/ping")
    assert response.status_code == 200
    assert response.json() == {
        "message": "pong",
        "api_version": "v1",
    }


def test_v2_falls_back_to_v1():
    response = client.get("/v2/ping")
    assert response.status_code == 200
    assert response.json() == {
        "message": "pong",
        "api_version": "v1",
    }


def test_resource_404_does_not_trigger_fallback_logic():
    response = client.get("/v3/echo/missing")
    assert response.status_code == 404
    assert response.json()["detail"] == "Value not found"