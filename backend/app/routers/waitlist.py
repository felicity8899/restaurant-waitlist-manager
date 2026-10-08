from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Dict, Any
from app.models import WaitlistEntry, WaitlistCreate, WaitlistSeat, Table
from app.store import store
from app.auth import get_current_user

router = APIRouter(prefix="/api/waitlist", tags=["Waitlist"])

@router.get("", response_model=List[WaitlistEntry])
async def get_active_waitlist():
    return store.get_waitlist()

@router.post("", response_model=WaitlistEntry, status_code=status.HTTP_201_CREATED)
async def join_waitlist(guest: WaitlistCreate):
    try:
        new_entry = store.add_to_waitlist(guest.guest_name, guest.party_size, guest.phone_number)
        await store.broadcast_event("QUEUE_UPDATE")
        return new_entry
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.post("/{party_id}/notify", response_model=WaitlistEntry)
async def notify_party(party_id: int, current_user: str = Depends(get_current_user)):
    updated_entry = store.notify_party(party_id)
    if not updated_entry:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to notify party {party_id}. Either party does not exist or status is not WAITING."
        )
    
    await store.broadcast_event("QUEUE_UPDATE")
    await store.broadcast_event("SMS_UPDATE")
    return updated_entry

@router.post("/{party_id}/seat")
async def seat_party(party_id: int, payload: WaitlistSeat, current_user: str = Depends(get_current_user)):
    result = store.seat_party(party_id, payload.table_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to seat party. Verify that party and table exist, table is AVAILABLE, and table capacity is sufficient."
        )
    
    await store.broadcast_event("QUEUE_UPDATE")
    await store.broadcast_event("TABLE_UPDATE")
    return result

@router.post("/{party_id}/cancel", response_model=WaitlistEntry)
async def cancel_party(party_id: int):
    updated_entry = store.cancel_party(party_id)
    if not updated_entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Party with ID {party_id} not found."
        )
    
    await store.broadcast_event("QUEUE_UPDATE")
    # If the party was seated, table is also updated back to AVAILABLE
    await store.broadcast_event("TABLE_UPDATE")
    return updated_entry
