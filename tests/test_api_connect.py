"""Tests for VivintSkyApi.connect(), verify_mfa(), and __call() retry logic."""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any

import pytest

from vivintpy.api import VivintSkyApi
from vivintpy.exceptions import (
    VivintSkyApiAuthenticationError,
    VivintSkyApiMfaRequiredError,
)
from vivintpy.models import AuthUserData


class _FakeResponse:
    """Fake aiohttp response for testing."""

    def __init__(
        self,
        status: int = 200,
        json_data: Any | None = None,
        text_data: str | None = None,
        content_type: str = "application/json",
        headers: dict[str, str] | None = None,
    ) -> None:
        self.status = status
        self._json_data = json_data or {}
        self._text_data = text_data or ""
        self.content_type = content_type
        self.headers = headers or {}

    async def json(self, encoding: str = "utf-8") -> Any:
        return self._json_data

    async def text(self) -> str:
        return self._text_data

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        pass

    def raise_for_status(self):
        pass


@pytest.fixture()
def base_api(monkeypatch) -> VivintSkyApi:
    """Return API instance with minimal setup."""
    dummy_session = SimpleNamespace(closed=False)
    monkeypatch.setattr(
        VivintSkyApi,
        "_VivintSkyApi__get_new_client_session",
        lambda self: dummy_session,
        raising=True,
    )
    return VivintSkyApi("user", password="pw", client_session=dummy_session)


@pytest.mark.asyncio
async def test_connect_with_refresh_token_success(monkeypatch, base_api):
    """Test connect() using refresh token successfully."""
    # Mock refresh_token method
    async def mock_refresh_token(token):
        base_api._VivintSkyApi__token = {"access_token": "xyz", "id_token": "abc"}

    monkeypatch.setattr(base_api, "refresh_token", mock_refresh_token)
    
    # Mock get_authuser_data to return valid user data with proper structure - needs panid
    mock_authuser_data = AuthUserData(
        u=[{"_id": "123", "n": "Test User", "system": [{"_id": "456", "panid": 789}]}],
        is_read_only=False
    )
    
    async def mock_get_authuser_data():
        return mock_authuser_data
    
    monkeypatch.setattr(base_api, "get_authuser_data", mock_get_authuser_data)
    
    # Set refresh token and call connect
    base_api._VivintSkyApi__refresh_token = "fake_refresh_token"
    result = await base_api.connect()
    
    assert result == mock_authuser_data
    assert base_api._VivintSkyApi__token is not None


@pytest.mark.asyncio
async def test_connect_with_password_fallback(monkeypatch, base_api):
    """Test connect() falls back to password when no refresh token."""
    # Mock password login
    async def mock_get_vivintsky_session(username, password):
        base_api._VivintSkyApi__token = {"access_token": "xyz", "id_token": "abc"}

    monkeypatch.setattr(base_api, "_VivintSkyApi__get_vivintsky_session", mock_get_vivintsky_session)
    
    # Mock get_authuser_data with proper structure - needs panid
    mock_authuser_data = AuthUserData(
        u=[{"_id": "123", "n": "Test User", "system": [{"_id": "456", "panid": 789}]}],
        is_read_only=False
    )
    
    async def mock_get_authuser_data():
        return mock_authuser_data
    
    monkeypatch.setattr(base_api, "get_authuser_data", mock_get_authuser_data)
    
    # Ensure no refresh token, but password exists
    base_api._VivintSkyApi__refresh_token = None
    result = await base_api.connect()
    
    assert result == mock_authuser_data


@pytest.mark.asyncio
async def test_connect_no_credentials_error(monkeypatch, base_api):
    """Test connect() raises error when no credentials provided."""
    # Remove both refresh token and password
    base_api._VivintSkyApi__refresh_token = None
    base_api._VivintSkyApi__password = None
    
    with pytest.raises(VivintSkyApiAuthenticationError, match="No password or refresh token provided"):
        await base_api.connect()


@pytest.mark.asyncio
async def test_connect_no_users_error(monkeypatch, base_api):
    """Test connect() raises error when authuser_data has no users."""
    # Mock successful authentication but empty users
    async def mock_refresh_token(token):
        base_api._VivintSkyApi__token = {"access_token": "xyz", "id_token": "abc"}

    monkeypatch.setattr(base_api, "refresh_token", mock_refresh_token)
    
    # Mock get_authuser_data with empty users list
    mock_authuser_data = AuthUserData(u=[], is_read_only=False)
    
    async def mock_get_authuser_data():
        return mock_authuser_data
    
    monkeypatch.setattr(base_api, "get_authuser_data", mock_get_authuser_data)
    
    # Set refresh token
    base_api._VivintSkyApi__refresh_token = "fake_refresh_token"
    
    with pytest.raises(VivintSkyApiAuthenticationError, match="Unable to login to Vivint"):
        await base_api.connect()


@pytest.mark.asyncio
async def test_verify_mfa_success_code_type(monkeypatch, base_api):
    """Test verify_mfa() success with code type."""
    base_api._VivintSkyApi__mfa_pending = True
    base_api._VivintSkyApi__mfa_type = "code"
    base_api._VivintSkyApi__username = "testuser"
    base_api._VivintSkyApi__password = "testpass"
    
    # Mock successful MFA response
    mfa_response = {"success": True}
    auth_response = {"access_token": "new_token", "id_token": "new_id"}
    
    # Mock __post to return the json data directly (not _FakeResponse)
    async def mock_post(*args, **kwargs):
        return mfa_response
        
    # Mock __get to return auth response
    async def mock_get(*args, **kwargs):
        return auth_response
    
    monkeypatch.setattr(base_api, "_VivintSkyApi__post", mock_post)
    monkeypatch.setattr(base_api, "_VivintSkyApi__get", mock_get)
    
    # verify_mfa returns None, so just check that MFA pending is cleared
    await base_api.verify_mfa("123456")
    
    assert not base_api._VivintSkyApi__mfa_pending


@pytest.mark.asyncio
async def test_verify_mfa_success_push_type(monkeypatch, base_api):
    """Test verify_mfa() success with push type."""
    base_api._VivintSkyApi__mfa_pending = True
    base_api._VivintSkyApi__mfa_type = "push"
    base_api._VivintSkyApi__username = "testuser"
    base_api._VivintSkyApi__password = "testpass"
    
    # Mock successful MFA response with URL
    mfa_response = {"url": "/oauth/authorize?code=abc123"}
    auth_response = {"access_token": "new_token", "id_token": "new_id"}
    
    # Mock __post to return the json data directly (not _FakeResponse)
    async def mock_post(*args, **kwargs):
        return mfa_response
        
    # Mock __get to return auth response
    async def mock_get(*args, **kwargs):
        return auth_response
    
    monkeypatch.setattr(base_api, "_VivintSkyApi__post", mock_post)
    monkeypatch.setattr(base_api, "_VivintSkyApi__get", mock_get)
    
    # verify_mfa returns None, so just check that MFA pending is cleared
    await base_api.verify_mfa("push_response")
    
    assert not base_api._VivintSkyApi__mfa_pending


@pytest.mark.asyncio
async def test_call_retry_on_invalid_session(monkeypatch, base_api):
    """Test __call() retries by calling connect() when session is invalid."""
    # Set up token initially
    base_api._VivintSkyApi__token = {"access_token": "xyz", "id_token": "abc"}
    
    connect_called = False
    
    async def mock_connect():
        nonlocal connect_called
        connect_called = True
        # Refresh token after connect
        base_api._VivintSkyApi__token = {"access_token": "new_xyz", "id_token": "new_abc"}
        return AuthUserData(
            u=[{"_id": "123", "n": "Test User", "system": [{"_id": "456", "panid": 789}]}],
            is_read_only=False
        )
    
    # Mock is_session_valid to return False first time, True second time
    call_count = 0
    def mock_is_session_valid():
        nonlocal call_count 
        call_count += 1
        return call_count > 1  # False first time, True after
    
    monkeypatch.setattr(base_api, "connect", mock_connect)
    monkeypatch.setattr(base_api, "is_session_valid", mock_is_session_valid)
    
    # Mock the actual HTTP call
    resp = _FakeResponse(status=200, json_data={"success": True})
    async def mock_post(*args, **kwargs):
        return resp
    
    dummy_session = SimpleNamespace(post=mock_post, closed=False)
    monkeypatch.setattr(base_api, "_VivintSkyApi__client_session", dummy_session)
    
    # Call __call via __post - should trigger retry logic
    result = await base_api._VivintSkyApi__post("test/endpoint")  # type: ignore[attr-defined]
    
    assert connect_called
    assert result == {"success": True}


@pytest.mark.asyncio
async def test_call_mfa_pending_blocks_non_mfa_requests(monkeypatch, base_api):
    """Test __call() raises MfaRequiredError when MFA pending and not MFA request."""
    base_api._VivintSkyApi__mfa_pending = True
    base_api._VivintSkyApi__token = {"access_token": "xyz", "id_token": "abc"}
    
    # Mock is_session_valid to return True
    monkeypatch.setattr(base_api, "is_session_valid", lambda: True)
    
    dummy_session = SimpleNamespace(post=lambda *args, **kwargs: None, closed=False)
    monkeypatch.setattr(base_api, "_VivintSkyApi__client_session", dummy_session)
    
    with pytest.raises(VivintSkyApiMfaRequiredError):
        await base_api._VivintSkyApi__post("test/endpoint")  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_call_mfa_request_allowed_when_pending(monkeypatch, base_api):
    """Test __call() allows MFA requests when MFA is pending."""
    base_api._VivintSkyApi__mfa_pending = True
    base_api._VivintSkyApi__token = {"access_token": "xyz", "id_token": "abc"}
    
    # Mock is_session_valid to return True
    monkeypatch.setattr(base_api, "is_session_valid", lambda: True)
    
    resp = _FakeResponse(status=200, json_data={"mfa_success": True})
    async def mock_post(*args, **kwargs):
        return resp
    
    dummy_session = SimpleNamespace(post=mock_post, closed=False)
    monkeypatch.setattr(base_api, "_VivintSkyApi__client_session", dummy_session)
    
    # MFA request contains "code" in data - should be allowed
    result = await base_api._VivintSkyApi__post("mfa/endpoint", data='{"code": "123456"}')  # type: ignore[attr-defined]
    
    assert result == {"mfa_success": True}
