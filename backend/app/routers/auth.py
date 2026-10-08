from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from app.auth import USERS_DB, verify_password, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES
from app.models import Token, LoginRequest

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

@router.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    hashed_pass = USERS_DB.get(form_data.username)
    if not hashed_pass or not verify_password(form_data.password, hashed_pass):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": form_data.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/login", response_model=Token)
async def login_via_json(login_req: LoginRequest):
    hashed_pass = USERS_DB.get(login_req.username)
    if not hashed_pass or not verify_password(login_req.password, hashed_pass):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": login_req.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}
