import os
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
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

# Setup static files serving if the directory exists (e.g. inside Docker)
static_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static")

if os.path.exists(static_dir) and os.path.isdir(static_dir):
    assets_dir = os.path.join(static_dir, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/")
    async def root():
        index_path = os.path.join(static_dir, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        return {
            "status": "online",
            "message": "Restaurant Waitlist & Table Manager API is running. (Frontend index.html not found)",
            "docs_url": "/docs"
        }

    @app.get("/{catchall:path}")
    async def catch_all(catchall: str):
        if catchall.startswith("api/") or catchall.startswith("docs") or catchall.startswith("openapi.json") or catchall == "ws":
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Not Found")
        
        # Check if requested file exists in static_dir
        if catchall:
            file_path = os.path.join(static_dir, catchall)
            if os.path.isfile(file_path):
                return FileResponse(file_path)
                
        # Default to index.html for SPA routing
        index_path = os.path.join(static_dir, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Not Found")
else:
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
