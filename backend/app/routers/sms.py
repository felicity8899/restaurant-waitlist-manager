from fastapi import APIRouter, Depends
from typing import List
from app.models import SMSLog
from app.store import store
from app.auth import get_current_user

router = APIRouter(prefix="/api/sms-logs", tags=["SMS"])

@router.get("", response_model=List[SMSLog])
async def get_all_sms_logs(current_user: str = Depends(get_current_user)):
    return store.get_sms_logs()
