from fastapi.testclient import TestClient


def test_health_returns_200(client: TestClient):
    resp = client.get("/health")
    assert resp.status_code == 200


def test_health_response_shape(client: TestClient):
    data = client.get("/health").json()
    assert "status" in data
    assert "version" in data
    assert "services" in data


def test_root_returns_app_info(client: TestClient):
    data = client.get("/").json()
    assert "name" in data
    assert "version" in data