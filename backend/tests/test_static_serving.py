import os
import sys
import shutil
import pytest
from fastapi.testclient import TestClient

@pytest.fixture(scope="module")
def setup_static_environment():
    # Define paths
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    static_dir = os.path.join(backend_dir, "static")
    assets_dir = os.path.join(static_dir, "assets")
    
    # Clean any pre-existing static dir (just in case)
    if os.path.exists(static_dir):
        shutil.rmtree(static_dir)
        
    # Create static & assets directories
    os.makedirs(assets_dir, exist_ok=True)
    
    # Write mock files
    index_content = "<html><body>Mock React Frontend Index</body></html>"
    js_content = "console.log('mock frontend js');"
    favicon_content = "mock favicon"
    
    with open(os.path.join(static_dir, "index.html"), "w") as f:
        f.write(index_content)
    with open(os.path.join(assets_dir, "main.js"), "w") as f:
        f.write(js_content)
    with open(os.path.join(static_dir, "favicon.ico"), "w") as f:
        f.write(favicon_content)
        
    # Force re-import of app by clearing sys.modules cache
    for key in list(sys.modules.keys()):
        if key.startswith("app.") or key == "app":
            del sys.modules[key]
            
    # Import app now that static dir is present
    from app.main import app
    client = TestClient(app)
    
    yield client, index_content, js_content, favicon_content
    
    # Cleanup static dir
    if os.path.exists(static_dir):
        shutil.rmtree(static_dir)
        
    # Force re-import of app again to restore state
    for key in list(sys.modules.keys()):
        if key.startswith("app.") or key == "app":
            del sys.modules[key]

def test_static_files_and_spa_routing(setup_static_environment):
    client, index_content, js_content, favicon_content = setup_static_environment
    
    # 1. Root route should serve index.html
    response = client.get("/")
    assert response.status_code == 200
    assert response.text == index_content
    
    # 2. Mounted asset route should serve static assets
    response = client.get("/assets/main.js")
    assert response.status_code == 200
    assert response.text == js_content
    
    # 3. Static root catch-all should serve root static files (like favicon.ico)
    response = client.get("/favicon.ico")
    assert response.status_code == 200
    assert response.text == favicon_content
    
    # 4. Unmatched routes (SPA routing) should fall back to index.html
    response = client.get("/guest/track/42")
    assert response.status_code == 200
    assert response.text == index_content
    
    # 5. API routes should still function and NOT be intercepted by static catch-all
    response = client.get("/api/tables")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    
    # 6. Unmatched API routes should return 404 rather than falling back to index.html
    response = client.get("/api/nonexistent")
    assert response.status_code == 404
