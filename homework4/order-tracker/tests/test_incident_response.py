import sys
import json
import sqlite3
import pytest
from pathlib import Path
import importlib.util
from fastapi.testclient import TestClient

# Add the incident-response directory to sys.path and load it dynamically
incident_response_dir = Path(__file__).parent.parent / "incident-response"
sys.path.insert(0, str(incident_response_dir))

# Import main dynamically
spec = importlib.util.spec_from_file_location("main", incident_response_dir / "main.py")
main = importlib.util.module_from_spec(spec)
sys.modules["main"] = main
spec.loader.exec_module(main)


@pytest.fixture
def test_client(tmp_path, monkeypatch):
    test_db = tmp_path / "incidents.db"
    monkeypatch.setattr(main, "DB_PATH", str(test_db))
    main.init_db()
    with TestClient(main.app) as client:
        yield client


def test_healthz(test_client):
    assert test_client.get("/healthz").json() == {"status": "ok"}


def test_receive_alert_and_fetch_telemetry(test_client, monkeypatch):
    # Mock Loki and Tempo requests
    async def mock_fetch_loki_logs(endpoint_filter=None):
        return {"data": {"result": [{"stream": {"exporter": "OTLP"}, "values": [["123456789", "mock log line"]]}]}}

    async def mock_fetch_tempo_traces(endpoint_filter=None):
        return [{"traceID": "mock-trace-123"}]

    monkeypatch.setattr(main, "fetch_loki_logs", mock_fetch_loki_logs)
    monkeypatch.setattr(main, "fetch_tempo_traces", mock_fetch_tempo_traces)

    # Mock alert payload from Grafana
    alert_payload = {
        "receiver": "webhook",
        "status": "firing",
        "alerts": [
            {
                "status": "firing",
                "labels": {
                    "alertname": "High Error Rate",
                    "route": "/api/orders/{order_id}"
                },
                "annotations": {
                    "summary": "Alert summary for order detail",
                    "description": "Error rate is high on route /api/orders/{order_id}"
                },
                "fingerprint": "alert-fp-123"
            }
        ]
    }

    response = test_client.post("/alerts", json=alert_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "processed"
    assert data["processed_count"] == 1
    assert data["incidents"][0]["incident_id"] == "alert-fp-123"
    assert data["incidents"][0]["affected_endpoint"] == "/api/orders/{order_id}"

    # Verify storage in DB / incidents list endpoint
    incidents_list = test_client.get("/incidents").json()
    assert len(incidents_list) == 1
    assert incidents_list[0]["id"] == "alert-fp-123"
    assert incidents_list[0]["alert_name"] == "High Error Rate"
    assert incidents_list[0]["affected_endpoint"] == "/api/orders/{order_id}"

    # Verify single incident detail retrieval
    detail = test_client.get("/incidents/alert-fp-123").json()
    assert detail["id"] == "alert-fp-123"
    assert detail["alert_payload"]["status"] == "firing"
    assert detail["logs"] == {"data": {"result": [{"stream": {"exporter": "OTLP"}, "values": [["123456789", "mock log line"]]}]}}
    assert detail["traces"] == [{"traceID": "mock-trace-123"}]
