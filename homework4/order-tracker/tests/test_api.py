import pytest
from fastapi.testclient import TestClient

from app import main


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "DB_PATH", tmp_path / "orders.db")
    with TestClient(main.app) as test_client:
        yield test_client


def test_health_and_seeded_orders(client):
    assert client.get("/healthz").json() == {"status": "ok"}
    orders = client.get("/api/orders").json()
    assert len(orders) == 3
    assert {order["priority"] for order in orders} == {"standard", "express"}


def test_create_and_update_order(client):
    response = client.post(
        "/api/orders",
        json={"customer": "Taylor", "item": "Mug", "priority": "standard"},
    )
    assert response.status_code == 201
    order_id = response.json()["id"]
    assert client.get(f"/api/orders/{order_id}").json()["status"] == "received"
    updated = client.patch(f"/api/orders/{order_id}", json={"status": "shipped"})
    assert updated.status_code == 200
    assert updated.json()["status"] == "shipped"


def test_missing_order(client):
    assert client.get("/api/orders/missing").status_code == 404


def test_incident_responder_webhook(client):
    # Verify the initial status of the seeded express order is 'preparing'
    express_order = client.get("/api/orders/express-1002").json()
    assert express_order["status"] == "preparing"
    assert express_order["priority"] == "express"

    # Call the incident responder webhook
    response = client.post("/api/webhook/alerts", json={"status": "firing"})
    assert response.status_code == 200
    
    # Check that the webhook returned the resolved order list
    data = response.json()
    assert data["status"] == "resolved"
    assert len(data["resolved_orders"]) >= 1
    
    # Verify the express order is now 'shipped'
    updated_order = client.get("/api/orders/express-1002").json()
    assert updated_order["status"] == "shipped"


def test_delayed_express_orders_metric(client):
    from opentelemetry.metrics import Observation
    # Initially, the seeded express-1002 order is from previous month (far older than 1 minute).
    # So the count of delayed express orders should be 1.
    observations = main.get_delayed_orders_count(None)
    assert len(observations) == 1
    assert isinstance(observations[0], Observation)
    assert observations[0].value == 1

    # Call the webhook to self-heal
    client.post("/api/webhook/alerts", json={"status": "firing"})

    # Now the count of delayed express orders should be 0, as it got updated to 'shipped'
    observations_after = main.get_delayed_orders_count(None)
    assert len(observations_after) == 1
    assert observations_after[0].value == 0


def test_order_lookup_telemetry(client, monkeypatch):
    recorded_metrics = []
    def mock_add(amount, attributes=None):
        recorded_metrics.append((amount, attributes))
    
    monkeypatch.setattr(main.order_lookup_requests_counter, "add", mock_add)
    
    # Successful lookup
    response = client.get("/api/orders/express-1002")
    assert response.status_code == 200
    assert len(recorded_metrics) == 1
    assert recorded_metrics[0] == (1, {"route": "/api/orders/{order_id}", "http.status_code": "200"})
    
    # Failed lookup
    response = client.get("/api/orders/non-existent")
    assert response.status_code == 404
    assert len(recorded_metrics) == 2
    assert recorded_metrics[1] == (1, {"route": "/api/orders/{order_id}", "http.status_code": "404"})



