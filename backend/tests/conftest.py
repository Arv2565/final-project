"""
Pytest configuration for backend tests.

Strategy:
- We patch `init_db` in src.main BEFORE the app module runs startup.
  We do this by patching at module attribute level right after import.
- The ASGITransport calls FastAPI's ASGI lifespan; we disable on_startup
  after import to avoid real DB calls.
"""
import sys
import os
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch

# Ensure 'src' package is importable from backend/ root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


@pytest_asyncio.fixture
async def async_client():
    """
    Provides an httpx AsyncClient bound to the FastAPI ASGI app.
    Patches the startup lifecycle so no real MongoDB connection occurs.
    """
    # Must import before patching so the module object exists
    import src.main as main_mod

    with patch.object(main_mod, "init_db", new_callable=AsyncMock) as mock_init:
        # Also clear the startup event list that references init_db
        app = main_mod.app
        original_startup = list(app.router.on_startup)
        app.router.on_startup.clear()

        from httpx import AsyncClient, ASGITransport
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            yield client

        # Restore
        app.router.on_startup[:] = original_startup
