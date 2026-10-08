import os
import sys
from datetime import datetime
from typing import List, Dict, Any, Optional, Set
from fastapi import WebSocket
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import StaticPool

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///restaurant.db")

# Normalize old 'postgres://' URLs (often provided by cloud platforms like Heroku/Render) to 'postgresql://'
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# SQLite needs check_same_thread: False
if DATABASE_URL.startswith("sqlite"):
    if DATABASE_URL == "sqlite://" or DATABASE_URL == "sqlite:///:memory:":
        engine = create_engine(
            DATABASE_URL,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool
        )
    else:
        engine = create_engine(
            DATABASE_URL,
            connect_args={"check_same_thread": False}
        )
else:
    engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class DBTable(Base):
    __tablename__ = "tables"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    capacity = Column(Integer, nullable=False)
    status = Column(String, nullable=False, default="AVAILABLE")
    current_party_id = Column(Integer, nullable=True)

class DBWaitlistEntry(Base):
    __tablename__ = "waitlist"
    id = Column(Integer, primary_key=True, index=True)
    guest_name = Column(String, nullable=False)
    party_size = Column(Integer, nullable=False)
    phone_number = Column(String, nullable=False)
    status = Column(String, nullable=False, default="WAITING")
    joined_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    notified_at = Column(DateTime, nullable=True)
    seated_at = Column(DateTime, nullable=True)
    table_id = Column(Integer, nullable=True)

class DBSMSLog(Base):
    __tablename__ = "sms_logs"
    id = Column(Integer, primary_key=True, index=True)
    phone_number = Column(String, nullable=False)
    message = Column(String, nullable=False)
    sent_at = Column(DateTime, nullable=False, default=datetime.utcnow)

class DatabaseStore:
    def __init__(self):
        is_testing = "pytest" in sys.modules
        is_memory = DATABASE_URL == "sqlite://" or DATABASE_URL == "sqlite:///:memory:"
        
        if is_testing or is_memory:
            # Recreate tables to ensure test isolation
            Base.metadata.drop_all(bind=engine)
            Base.metadata.create_all(bind=engine)
            self._seed_default_data()
        else:
            Base.metadata.create_all(bind=engine)
            # Seed only if Table table is empty
            db = SessionLocal()
            try:
                count = db.query(DBTable).count()
                if count == 0:
                    self._seed_default_data()
            finally:
                db.close()
                
        self.active_websockets: Set[WebSocket] = set()

    def _seed_default_data(self):
        db = SessionLocal()
        try:
            # Seed physical tables
            tables = [
                DBTable(id=1, name="Table 1", capacity=2, status="AVAILABLE", current_party_id=None),
                DBTable(id=2, name="Table 2", capacity=2, status="AVAILABLE", current_party_id=None),
                DBTable(id=3, name="Table 3", capacity=4, status="AVAILABLE", current_party_id=None),
                DBTable(id=4, name="Table 4", capacity=4, status="AVAILABLE", current_party_id=None),
                DBTable(id=5, name="Booth 5", capacity=6, status="AVAILABLE", current_party_id=None),
                DBTable(id=6, name="Booth 6", capacity=6, status="AVAILABLE", current_party_id=None),
                DBTable(id=7, name="Table 7", capacity=8, status="AVAILABLE", current_party_id=None),
            ]
            db.add_all(tables)
            
            # Seed waitlist
            waitlist = [
                DBWaitlistEntry(
                    id=1,
                    guest_name="John Doe",
                    party_size=2,
                    phone_number="555-0199",
                    status="WAITING",
                    joined_at=datetime.utcnow(),
                    notified_at=None,
                    seated_at=None,
                    table_id=None
                ),
                DBWaitlistEntry(
                    id=2,
                    guest_name="Jane Smith",
                    party_size=4,
                    phone_number="555-0244",
                    status="WAITING",
                    joined_at=datetime.utcnow(),
                    notified_at=None,
                    seated_at=None,
                    table_id=None
                )
            ]
            db.add_all(waitlist)
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    # --- WebSocket connection management ---
    def register_websocket(self, websocket: WebSocket):
        self.active_websockets.add(websocket)

    def unregister_websocket(self, websocket: WebSocket):
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
        db = SessionLocal()
        try:
            tables = db.query(DBTable).order_by(DBTable.id).all()
            return [
                {
                    "id": t.id,
                    "name": t.name,
                    "capacity": t.capacity,
                    "status": t.status,
                    "current_party_id": t.current_party_id
                }
                for t in tables
            ]
        finally:
            db.close()

    def clear_table(self, table_id: int) -> Optional[Dict[str, Any]]:
        db = SessionLocal()
        try:
            t = db.query(DBTable).filter(DBTable.id == table_id).first()
            if not t:
                return None
            if t.status == "OCCUPIED":
                t.status = "DIRTY"
                t.current_party_id = None
            elif t.status == "DIRTY":
                t.status = "AVAILABLE"
            db.commit()
            return {
                "id": t.id,
                "name": t.name,
                "capacity": t.capacity,
                "status": t.status,
                "current_party_id": t.current_party_id
            }
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    # --- Waitlist Operations ---
    def get_waitlist(self) -> List[Dict[str, Any]]:
        db = SessionLocal()
        try:
            entries = db.query(DBWaitlistEntry).order_by(DBWaitlistEntry.id).all()
            return [
                {
                    "id": w.id,
                    "guest_name": w.guest_name,
                    "party_size": w.party_size,
                    "phone_number": w.phone_number,
                    "status": w.status,
                    "joined_at": w.joined_at,
                    "notified_at": w.notified_at,
                    "seated_at": w.seated_at,
                    "table_id": w.table_id
                }
                for w in entries
            ]
        finally:
            db.close()

    def add_to_waitlist(self, guest_name: str, party_size: int, phone_number: str) -> Dict[str, Any]:
        db = SessionLocal()
        try:
            entry = DBWaitlistEntry(
                guest_name=guest_name,
                party_size=party_size,
                phone_number=phone_number,
                status="WAITING",
                joined_at=datetime.utcnow()
            )
            db.add(entry)
            db.commit()
            db.refresh(entry)
            return {
                "id": entry.id,
                "guest_name": entry.guest_name,
                "party_size": entry.party_size,
                "phone_number": entry.phone_number,
                "status": entry.status,
                "joined_at": entry.joined_at,
                "notified_at": entry.notified_at,
                "seated_at": entry.seated_at,
                "table_id": entry.table_id
            }
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def notify_party(self, party_id: int) -> Optional[Dict[str, Any]]:
        db = SessionLocal()
        try:
            w = db.query(DBWaitlistEntry).filter(DBWaitlistEntry.id == party_id).first()
            if not w or w.status != "WAITING":
                return None
            w.status = "NOTIFIED"
            w.notified_at = datetime.utcnow()
            
            # Log mock SMS
            sms = DBSMSLog(
                phone_number=w.phone_number,
                message=f"Hi {w.guest_name}, your table is ready! Please proceed to the host stand.",
                sent_at=datetime.utcnow()
            )
            db.add(sms)
            db.commit()
            db.refresh(w)
            return {
                "id": w.id,
                "guest_name": w.guest_name,
                "party_size": w.party_size,
                "phone_number": w.phone_number,
                "status": w.status,
                "joined_at": w.joined_at,
                "notified_at": w.notified_at,
                "seated_at": w.seated_at,
                "table_id": w.table_id
            }
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def seat_party(self, party_id: int, table_id: int) -> Optional[Dict[str, Any]]:
        db = SessionLocal()
        try:
            w = db.query(DBWaitlistEntry).filter(DBWaitlistEntry.id == party_id).first()
            t = db.query(DBTable).filter(DBTable.id == table_id).first()
            
            if not w or not t:
                return None
                
            if w.status not in ("WAITING", "NOTIFIED"):
                return None
            if t.status != "AVAILABLE":
                return None
            if t.capacity < w.party_size:
                return None
                
            w.status = "SEATED"
            w.table_id = table_id
            w.seated_at = datetime.utcnow()
            
            t.status = "OCCUPIED"
            t.current_party_id = party_id
            
            db.commit()
            db.refresh(w)
            db.refresh(t)
            return {
                "party": {
                    "id": w.id,
                    "guest_name": w.guest_name,
                    "party_size": w.party_size,
                    "phone_number": w.phone_number,
                    "status": w.status,
                    "joined_at": w.joined_at,
                    "notified_at": w.notified_at,
                    "seated_at": w.seated_at,
                    "table_id": w.table_id
                },
                "table": {
                    "id": t.id,
                    "name": t.name,
                    "capacity": t.capacity,
                    "status": t.status,
                    "current_party_id": t.current_party_id
                }
            }
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def cancel_party(self, party_id: int) -> Optional[Dict[str, Any]]:
        db = SessionLocal()
        try:
            w = db.query(DBWaitlistEntry).filter(DBWaitlistEntry.id == party_id).first()
            if not w:
                return None
                
            if w.status == "SEATED" and w.table_id is not None:
                t = db.query(DBTable).filter(DBTable.id == w.table_id).first()
                if t:
                    t.status = "AVAILABLE"
                    t.current_party_id = None
            
            w.status = "CANCELLED"
            w.table_id = None
            db.commit()
            db.refresh(w)
            return {
                "id": w.id,
                "guest_name": w.guest_name,
                "party_size": w.party_size,
                "phone_number": w.phone_number,
                "status": w.status,
                "joined_at": w.joined_at,
                "notified_at": w.notified_at,
                "seated_at": w.seated_at,
                "table_id": w.table_id
            }
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    # --- SMS operations ---
    def get_sms_logs(self) -> List[Dict[str, Any]]:
        db = SessionLocal()
        try:
            logs = db.query(DBSMSLog).order_by(DBSMSLog.id).all()
            return [
                {
                    "id": s.id,
                    "phone_number": s.phone_number,
                    "message": s.message,
                    "sent_at": s.sent_at
                }
                for s in logs
            ]
        finally:
            db.close()

# Create a single global instance
store = DatabaseStore()
