import threading
from datetime import datetime
from typing import List, Dict, Any, Optional, Set
from fastapi import WebSocket

class InMemoryStore:
    def __init__(self):
        self.lock = threading.Lock()
        
        # Physical tables seeding
        self.tables: List[Dict[str, Any]] = [
            {"id": 1, "name": "Table 1", "capacity": 2, "status": "AVAILABLE", "current_party_id": None},
            {"id": 2, "name": "Table 2", "capacity": 2, "status": "AVAILABLE", "current_party_id": None},
            {"id": 3, "name": "Table 3", "capacity": 4, "status": "AVAILABLE", "current_party_id": None},
            {"id": 4, "name": "Table 4", "capacity": 4, "status": "AVAILABLE", "current_party_id": None},
            {"id": 5, "name": "Booth 5", "capacity": 6, "status": "AVAILABLE", "current_party_id": None},
            {"id": 6, "name": "Booth 6", "capacity": 6, "status": "AVAILABLE", "current_party_id": None},
            {"id": 7, "name": "Table 7", "capacity": 8, "status": "AVAILABLE", "current_party_id": None},
        ]
        
        # Waitlist seeding
        self.waitlist: List[Dict[str, Any]] = [
            {
                "id": 1,
                "guest_name": "John Doe",
                "party_size": 2,
                "phone_number": "555-0199",
                "status": "WAITING",
                "joined_at": datetime.utcnow(),
                "notified_at": None,
                "seated_at": None,
                "table_id": None
            },
            {
                "id": 2,
                "guest_name": "Jane Smith",
                "party_size": 4,
                "phone_number": "555-0244",
                "status": "WAITING",
                "joined_at": datetime.utcnow(),
                "notified_at": None,
                "seated_at": None,
                "table_id": None
            }
        ]
        
        self.sms_logs: List[Dict[str, Any]] = []
        
        self.next_waitlist_id = 3
        self.next_sms_id = 1
        
        # WebSockets connections set
        self.active_websockets: Set[WebSocket] = set()

    # --- WebSocket connection management ---
    def register_websocket(self, websocket: WebSocket):
        with self.lock:
            self.active_websockets.add(websocket)

    def unregister_websocket(self, websocket: WebSocket):
        with self.lock:
            if websocket in self.active_websockets:
                self.active_websockets.remove(websocket)

    async def broadcast_event(self, event: str):
        sockets = list(self.active_websockets)
        for ws in sockets:
            try:
                await ws.send_text(event)
            except Exception:
                self.unregister_websocket(ws)

    # --- Tables Operations ---
    def get_tables(self) -> List[Dict[str, Any]]:
        with self.lock:
            return [dict(t) for t in self.tables]

    def clear_table(self, table_id: int) -> Optional[Dict[str, Any]]:
        with self.lock:
            for t in self.tables:
                if t["id"] == table_id:
                    if t["status"] == "OCCUPIED":
                        t["status"] = "DIRTY"
                        t["current_party_id"] = None
                    elif t["status"] == "DIRTY":
                        t["status"] = "AVAILABLE"
                    return dict(t)
            return None

    # --- Waitlist Operations ---
    def get_waitlist(self) -> List[Dict[str, Any]]:
        with self.lock:
            # Return copy of the waitlist
            return [dict(w) for w in self.waitlist]

    def add_to_waitlist(self, guest_name: str, party_size: int, phone_number: str) -> Dict[str, Any]:
        with self.lock:
            entry = {
                "id": self.next_waitlist_id,
                "guest_name": guest_name,
                "party_size": party_size,
                "phone_number": phone_number,
                "status": "WAITING",
                "joined_at": datetime.utcnow(),
                "notified_at": None,
                "seated_at": None,
                "table_id": None
            }
            self.next_waitlist_id += 1
            self.waitlist.append(entry)
            return dict(entry)

    def notify_party(self, party_id: int) -> Optional[Dict[str, Any]]:
        with self.lock:
            for w in self.waitlist:
                if w["id"] == party_id:
                    if w["status"] != "WAITING":
                        return None
                    w["status"] = "NOTIFIED"
                    w["notified_at"] = datetime.utcnow()
                    
                    # Log mock SMS
                    sms = {
                        "id": self.next_sms_id,
                        "phone_number": w["phone_number"],
                        "message": f"Hi {w['guest_name']}, your table is ready! Please proceed to the host stand.",
                        "sent_at": datetime.utcnow()
                    }
                    self.next_sms_id += 1
                    self.sms_logs.append(sms)
                    return dict(w)
            return None

    def seat_party(self, party_id: int, table_id: int) -> Optional[Dict[str, Any]]:
        with self.lock:
            # 1. Find party and table
            party = None
            table = None
            for w in self.waitlist:
                if w["id"] == party_id:
                    party = w
                    break
            for t in self.tables:
                if t["id"] == table_id:
                    table = t
                    break
            
            if not party or not table:
                return None
                
            # 2. Check rules
            if party["status"] not in ("WAITING", "NOTIFIED"):
                return None
            if table["status"] != "AVAILABLE":
                return None
            if table["capacity"] < party["party_size"]:
                return None
                
            # 3. Update status
            party["status"] = "SEATED"
            party["table_id"] = table_id
            party["seated_at"] = datetime.utcnow()
            
            table["status"] = "OCCUPIED"
            table["current_party_id"] = party_id
            
            return {"party": dict(party), "table": dict(table)}

    def cancel_party(self, party_id: int) -> Optional[Dict[str, Any]]:
        with self.lock:
            target_party = None
            for w in self.waitlist:
                if w["id"] == party_id:
                    target_party = w
                    break
            
            if not target_party:
                return None
                
            # If they were seated, clear their table back to AVAILABLE directly
            if target_party["status"] == "SEATED" and target_party["table_id"] is not None:
                for t in self.tables:
                    if t["id"] == target_party["table_id"]:
                        t["status"] = "AVAILABLE"
                        t["current_party_id"] = None
                        break
            
            target_party["status"] = "CANCELLED"
            target_party["table_id"] = None
            return dict(target_party)

    # --- SMS operations ---
    def get_sms_logs(self) -> List[Dict[str, Any]]:
        with self.lock:
            return [dict(s) for s in self.sms_logs]

# Global single instance of our store
store = InMemoryStore()
