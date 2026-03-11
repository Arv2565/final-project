"""
Backend test suite — runs in myenv without a real MongoDB connection.

Coverage:
  1. App startup / import chain
  2. Route registration
  3. Health endpoint (200)
  4. Auth endpoint shape (422 on missing fields)
  5. Security utilities (hashing + JWT)
  6. Schema validation
"""
import sys
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# Ensure 'src' package is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ===========================================================================
# Helpers
# ===========================================================================

def _import_app():
    """Import the FastAPI app, patching away the DB init."""
    import src.main as main_mod
    with patch.object(main_mod, "init_db", new_callable=AsyncMock):
        return main_mod.app


# ===========================================================================
# 1. Import / startup sanity
# ===========================================================================

def test_app_imports():
    """The FastAPI app can be imported without error."""
    app = _import_app()
    assert app is not None


def test_app_has_expected_routes():
    """All expected route prefixes are registered."""
    app = _import_app()
    paths = [route.path for route in app.routes]
    assert any("/api/health" in p for p in paths), f"Missing /api/health in {paths}"
    assert any("/api/auth" in p for p in paths), f"Missing /api/auth in {paths}"
    assert any("/api/user" in p for p in paths), f"Missing /api/user in {paths}"
    assert any("/api/chat-history" in p for p in paths), f"Missing /api/chat-history in {paths}"
    assert any("/api/documents" in p for p in paths), f"Missing /api/documents in {paths}"


# ===========================================================================
# 2. Health endpoint
# ===========================================================================

@pytest.mark.asyncio
async def test_health_endpoint(async_client):
    """GET /api/health should return 200."""
    response = await async_client.get("/api/health")
    assert response.status_code == 200


# ===========================================================================
# 3. Auth endpoint shapes (no DB needed — these fail at validation layer)
# ===========================================================================

@pytest.mark.asyncio
async def test_signup_missing_fields(async_client):
    """POST /api/auth/signup with no body → 422 Unprocessable Entity."""
    response = await async_client.post("/api/auth/signup", json={})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_login_missing_fields(async_client):
    """POST /api/auth/login with no body → 422."""
    response = await async_client.post("/api/auth/login", json={})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_refresh_missing_token(async_client):
    """POST /api/auth/refresh with empty body → 422."""
    response = await async_client.post("/api/auth/refresh", json={})
    assert response.status_code == 422


# ===========================================================================
# 4. Security utility unit tests (no DB)
# ===========================================================================

def test_password_hash_and_verify():
    """Hashing a password and then verifying it should succeed."""
    from src.core.security import get_password_hash, verify_password
    plaintext = "SuperSecret123!"
    hashed = get_password_hash(plaintext)
    assert hashed != plaintext
    assert verify_password(plaintext, hashed) is True


def test_wrong_password_fails_verification():
    """Verifying the wrong password should return False."""
    from src.core.security import get_password_hash, verify_password
    hashed = get_password_hash("correct_password")
    assert verify_password("wrong_password", hashed) is False


def test_get_access_token_is_valid_jwt():
    """get_access_token should return a properly formatted JWT string."""
    from src.core.security import get_access_token
    from beanie import PydanticObjectId

    mock_user = MagicMock()
    mock_user.id = PydanticObjectId()
    mock_user.name = "Test User"
    mock_user.username = "testuser"

    token = get_access_token(mock_user)
    assert isinstance(token, str)
    parts = token.split(".")
    assert len(parts) == 3, f"Expected 3 JWT parts, got: {parts}"


# ===========================================================================
# 5. Schema validation unit tests
# ===========================================================================

def test_user_create_schema_valid():
    """UserCreate accepts valid input."""
    from src.schemas.user import UserCreate
    user = UserCreate(
        name="Test User",
        username="testuser",
        email="test@example.com",
        password="password123",
        phone="1234567890",
    )
    assert user.username == "testuser"
    assert user.email == "test@example.com"


def test_user_create_schema_rejects_invalid_email():
    """UserCreate should reject a non-email string."""
    from pydantic import ValidationError
    from src.schemas.user import UserCreate
    with pytest.raises(ValidationError):
        UserCreate(
            name="Test",
            username="test",
            email="not-an-email",
            password="pass",
            phone="000",
        )


def test_user_login_schema():
    """UserLogin accepts username + password."""
    from src.schemas.user import UserLogin
    login = UserLogin(username="testuser", password="pass123")
    assert login.username == "testuser"
    assert login.password == "pass123"
