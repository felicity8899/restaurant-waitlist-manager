from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from app.models import Table
from app.store import store
from app.auth import get_current_user

router = APIRouter(prefix="/api/tables", tags=["Tables"])

@router.get("", response_model=List[Table])
async def get_all_tables():
    return store.get_tables()

@router.post("/{table_id}/clear", response_model=Table)
async def clear_table(table_id: int, current_user: str = Depends(get_current_user)):
    updated_table = store.clear_table(table_id)
    if not updated_table:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Table with ID {table_id} not found."
        )
    
    # Broadcast the event
    await store.broadcast_event("TABLE_UPDATE")
    return updated_table
