import os
import pytest
from unittest.mock import patch

def test_database_url_configuration():
    # Test that DatabaseStore respects the DATABASE_URL environment variable
    custom_db_path = "test_custom_restaurant.db"
    if os.path.exists(custom_db_path):
        os.remove(custom_db_path)
        
    custom_url = f"sqlite:///{custom_db_path}"
    
    # We patch DATABASE_URL in the environment and re-initialize DatabaseStore to verify it connects to the new DB file
    with patch.dict(os.environ, {"DATABASE_URL": custom_url}):
        import app.store as store_mod
        from importlib import reload
        
        # Reload the store module under the patched env
        reload(store_mod)
        
        store_inst = store_mod.DatabaseStore()
        
        # Verify that the physical tables were created and seeded in the new DB file
        tables = store_inst.get_tables()
        assert len(tables) == 7
        assert tables[0]["name"] == "Table 1"
        
        waitlist = store_inst.get_waitlist()
        assert len(waitlist) == 2
        
    # Cleanup and restore default store
    if os.path.exists(custom_db_path):
        os.remove(custom_db_path)
        
    with patch.dict(os.environ, {"DATABASE_URL": "sqlite:///restaurant.db"}):
        import app.store as store_mod
        from importlib import reload
        reload(store_mod)
