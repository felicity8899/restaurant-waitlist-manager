from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from app.routers import auth, tables, waitlist, sms
from app.store import store

app = FastAPI(
    title="Restaurant Waitlist & Table Manager API",
    description="Backend API specification supporting REST routes and WebSocket live state synchronization.",
    version="1.0.0"
)

# Configure CORS so our React frontend can query the APIs
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual frontend origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth.router)
app.include_router(tables.router)
app.include_router(waitlist.router)
app.include_router(sms.router)

@app.get("/")
async def root():
    return {
        "status": "online",
        "message": "Restaurant Waitlist & Table Manager API is running.",
        "docs_url": "/docs"
    }

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    store.register_websocket(websocket)
    try:
        while True:
            # Keep connection open. If client sends anything, discard or log.
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        store.unregister_websocket(websocket)
