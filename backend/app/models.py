from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class TableStatus(str, Enum):
    AVAILABLE = "AVAILABLE"
    OCCUPIED = "OCCUPIED"
    DIRTY = "DIRTY"

class Table(BaseModel):
    id: int
    name: str
    capacity: int
    status: TableStatus
    current_party_id: Optional[int] = None

class WaitlistStatus(str, Enum):
    WAITING = "WAITING"
    NOTIFIED = "NOTIFIED"
    SEATED = "SEATED"
    CANCELLED = "CANCELLED"

class WaitlistEntry(BaseModel):
    id: int
    guest_name: str
    party_size: int
    phone_number: str
    status: WaitlistStatus
    joined_at: datetime
    notified_at: Optional[datetime] = None
    seated_at: Optional[datetime] = None
    table_id: Optional[int] = None

class WaitlistCreate(BaseModel):
    guest_name: str = Field(..., min_length=1)
    party_size: int = Field(..., gt=0)
    phone_number: str = Field(..., min_length=1)

class WaitlistSeat(BaseModel):
    table_id: int

class SMSLog(BaseModel):
    id: int
    phone_number: str
    message: str
    sent_at: datetime

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class LoginRequest(BaseModel):
    username: str
    password: str
