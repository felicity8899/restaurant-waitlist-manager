import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.store import store

client = TestClient(app)

@pytest.fixture(autouse=True)
def run_before_and_after_tests():
    # Reset store state before every test for clean isolation
    store.__init__()
    yield

def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "online"

def test_get_tables_public():
    response = client.get("/api/tables")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 7
    assert data[0]["name"] == "Table 1"
    assert data[0]["capacity"] == 2
    assert data[0]["status"] == "AVAILABLE"

def test_get_waitlist_public():
    response = client.get("/api/waitlist")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["guest_name"] == "John Doe"
    assert data[1]["guest_name"] == "Jane Smith"

def test_join_waitlist():
    payload = {
        "guest_name": "Alice Cooper",
        "party_size": 3,
        "phone_number": "555-1122"
    }
    response = client.post("/api/waitlist", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["guest_name"] == "Alice Cooper"
    assert data["party_size"] == 3
    assert data["status"] == "WAITING"
    assert data["id"] is not None

    # Check it appeared in the queue
    queue_resp = client.get("/api/waitlist")
    assert len(queue_resp.json()) == 3

def test_join_waitlist_invalid():
    # Empty name
    response = client.post("/api/waitlist", json={"guest_name": "", "party_size": 2, "phone_number": "123"})
    assert response.status_code == 422 # Pydantic min_length validation

    # Invalid party size
    response = client.post("/api/waitlist", json={"guest_name": "Bob", "party_size": 0, "phone_number": "123"})
    assert response.status_code == 422

def test_authentication_flow():
    # 1. Correct login
    response = client.post("/api/auth/token", data={"username": "admin", "password": "1234"})
    assert response.status_code == 200
    token_data = response.json()
    assert "access_token" in token_data
    assert token_data["token_type"] == "bearer"

    # 2. Incorrect login
    response = client.post("/api/auth/token", data={"username": "admin", "password": "wrongpassword"})
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect username or password"

def get_auth_headers():
    response = client.post("/api/auth/token", data={"username": "admin", "password": "1234"})
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

def test_secured_endpoints_no_auth():
    # Notify without auth
    response = client.post("/api/waitlist/1/notify")
    assert response.status_code == 401

    # Seat without auth
    response = client.post("/api/waitlist/1/seat", json={"table_id": 1})
    assert response.status_code == 401

    # Clear table without auth
    response = client.post("/api/tables/1/clear")
    assert response.status_code == 401

    # Fetch SMS logs without auth
    response = client.get("/api/sms-logs")
    assert response.status_code == 401

def test_notify_party_with_auth():
    headers = get_auth_headers()
    response = client.post("/api/waitlist/1/notify", headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "NOTIFIED"

    # Confirm SMS log generated
    sms_response = client.get("/api/sms-logs", headers=headers)
    assert sms_response.status_code == 200
    logs = sms_response.json()
    assert len(logs) == 1
    assert logs[0]["phone_number"] == "555-0199"
    assert "ready" in logs[0]["message"]

def test_seat_party_with_auth():
    headers = get_auth_headers()
    
    # Seating John Doe (party size 2) at Table 1 (capacity 2)
    response = client.post("/api/waitlist/1/seat", json={"table_id": 1}, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["party"]["status"] == "SEATED"
    assert data["party"]["table_id"] == 1
    assert data["table"]["status"] == "OCCUPIED"
    assert data["table"]["current_party_id"] == 1

def test_seat_party_capacity_mismatch():
    headers = get_auth_headers()
    
    # Attempting to seat Jane Smith (party size 4) at Table 1 (capacity 2) should fail
    response = client.post("/api/waitlist/2/seat", json={"table_id": 1}, headers=headers)
    assert response.status_code == 400
    assert "Failed to seat party" in response.json()["detail"]

def test_clear_table_workflow():
    headers = get_auth_headers()
    
    # Seat party first
    client.post("/api/waitlist/1/seat", json={"table_id": 1}, headers=headers)
    
    # 1. Clear occupied table -> DIRTY
    response = client.post("/api/tables/1/clear", headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "DIRTY"
    assert response.json()["current_party_id"] is None

    # 2. Clear dirty table -> AVAILABLE
    response2 = client.post("/api/tables/1/clear", headers=headers)
    assert response2.status_code == 200
    assert response2.json()["status"] == "AVAILABLE"

def test_cancel_party_public():
    # Seated first
    headers = get_auth_headers()
    client.post("/api/waitlist/1/seat", json={"table_id": 1}, headers=headers)

    # Public cancel (No Authorization header required)
    response = client.post("/api/waitlist/1/cancel")
    assert response.status_code == 200
    assert response.json()["status"] == "CANCELLED"
    assert response.json()["table_id"] is None

    # Confirm table became AVAILABLE directly
    tables_resp = client.get("/api/tables")
    assert tables_resp.json()[0]["status"] == "AVAILABLE"

def test_websocket_connection():
    # 1. Assert initial active websockets are 0
    assert len(store.active_websockets) == 0

    # 2. Connect to /ws and assert websocket is registered
    with client.websocket_connect("/ws") as websocket:
        assert len(store.active_websockets) == 1
        
    # 3. Assert websocket is unregistered upon closing the connection
    assert len(store.active_websockets) == 0
