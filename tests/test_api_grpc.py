"""Tests for VivintSkyApi._send_grpc() method."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
import grpc.aio

from vivintpy.api import VivintSkyApi
from vivintpy.proto import beam_pb2, beam_pb2_grpc


@pytest.fixture()
def api_with_token(monkeypatch) -> VivintSkyApi:
    """Return API instance with valid token."""
    dummy_session = SimpleNamespace(closed=False)
    monkeypatch.setattr(
        VivintSkyApi,
        "_VivintSkyApi__get_new_client_session",
        lambda self: dummy_session,
        raising=True,
    )
    
    api = VivintSkyApi("user", password="pw", client_session=dummy_session)
    api._VivintSkyApi__token = {"access_token": "test_token", "id_token": "test_id"}
    
    # Mock is_session_valid to return True
    monkeypatch.setattr(api, "is_session_valid", lambda: True)
    
    return api


@pytest.mark.asyncio
async def test_send_grpc_success(monkeypatch, api_with_token):
    """Test _send_grpc() executes callback successfully."""
    # Mock gRPC components
    mock_channel = AsyncMock()
    mock_stub = MagicMock()
    mock_response = beam_pb2.BeamResponse()
    
    # Mock the callback to return our response
    async def mock_callback(stub, metadata):
        # Verify stub and metadata are passed correctly
        assert stub == mock_stub
        assert metadata == [("token", "test_token")]
        return mock_response
    
    # Mock grpc.aio.secure_channel to return our mock channel
    mock_secure_channel = AsyncMock()
    mock_secure_channel.return_value.__aenter__ = AsyncMock(return_value=mock_channel)
    mock_secure_channel.return_value.__aexit__ = AsyncMock(return_value=None)
    
    # Mock BeamStub creation
    mock_beam_stub = MagicMock(return_value=mock_stub)
    
    monkeypatch.setattr(grpc.aio, "secure_channel", mock_secure_channel)
    monkeypatch.setattr(beam_pb2_grpc, "BeamStub", mock_beam_stub)
    monkeypatch.setattr(grpc, "ssl_channel_credentials", MagicMock())
    
    # Execute _send_grpc
    await api_with_token._send_grpc(mock_callback)
    
    # Verify secure_channel was called with correct endpoint
    mock_secure_channel.assert_called_once()
    args, kwargs = mock_secure_channel.call_args
    assert "grpc.vivintsky.com:50051" in args
    assert "credentials" in kwargs
    
    # Verify BeamStub was created with the channel
    mock_beam_stub.assert_called_once_with(mock_channel)


@pytest.mark.asyncio
async def test_send_grpc_callback_receives_correct_metadata(monkeypatch, api_with_token):
    """Test _send_grpc() passes correct token metadata to callback."""
    # Set specific token
    api_with_token._VivintSkyApi__token = {"access_token": "specific_token", "id_token": "id"}
    
    received_metadata = None
    
    async def test_callback(stub, metadata):
        nonlocal received_metadata
        received_metadata = metadata
        return beam_pb2.BeamResponse()
    
    # Mock gRPC components
    mock_channel = AsyncMock()
    mock_stub = MagicMock()
    
    mock_secure_channel = AsyncMock()
    mock_secure_channel.return_value.__aenter__ = AsyncMock(return_value=mock_channel)
    mock_secure_channel.return_value.__aexit__ = AsyncMock(return_value=None)
    
    monkeypatch.setattr(grpc.aio, "secure_channel", mock_secure_channel)
    monkeypatch.setattr(beam_pb2_grpc, "BeamStub", MagicMock(return_value=mock_stub))
    monkeypatch.setattr(grpc, "ssl_channel_credentials", MagicMock())
    
    await api_with_token._send_grpc(test_callback)
    
    # Verify correct token was passed in metadata
    assert received_metadata == [("token", "specific_token")]


@pytest.mark.asyncio
async def test_send_grpc_invalid_session_assertion(monkeypatch, api_with_token):
    """Test _send_grpc() raises AssertionError when session is invalid."""
    # Mock is_session_valid to return False
    monkeypatch.setattr(api_with_token, "is_session_valid", lambda: False)
    
    async def dummy_callback(stub, metadata):
        return beam_pb2.BeamResponse()
    
    with pytest.raises(AssertionError):
        await api_with_token._send_grpc(dummy_callback)


@pytest.mark.asyncio
async def test_send_grpc_no_token_assertion(monkeypatch, api_with_token):
    """Test _send_grpc() raises AssertionError when no token exists."""
    # Remove token
    api_with_token._VivintSkyApi__token = None
    
    async def dummy_callback(stub, metadata):
        return beam_pb2.BeamResponse()
    
    with pytest.raises(AssertionError):
        await api_with_token._send_grpc(dummy_callback)


@pytest.mark.asyncio
async def test_send_grpc_logs_response(monkeypatch, api_with_token, caplog):
    """Test _send_grpc() logs the response at debug level."""
    mock_response = beam_pb2.BeamResponse()
    mock_response.status = "success"
    
    async def mock_callback(stub, metadata):
        return mock_response
    
    # Mock gRPC components
    mock_channel = AsyncMock()
    mock_stub = MagicMock()
    
    mock_secure_channel = AsyncMock()
    mock_secure_channel.return_value.__aenter__ = AsyncMock(return_value=mock_channel)
    mock_secure_channel.return_value.__aexit__ = AsyncMock(return_value=None)
    
    monkeypatch.setattr(grpc.aio, "secure_channel", mock_secure_channel)
    monkeypatch.setattr(beam_pb2_grpc, "BeamStub", MagicMock(return_value=mock_stub))
    monkeypatch.setattr(grpc, "ssl_channel_credentials", MagicMock())
    
    # Set logging level to capture debug messages
    import logging
    logging.getLogger("vivintpy.api").setLevel(logging.DEBUG)
    
    await api_with_token._send_grpc(mock_callback)
    
    # Check that response was logged
    assert "Response received:" in caplog.text
    assert str(mock_response) in caplog.text


@pytest.mark.asyncio
async def test_send_grpc_channel_context_manager(monkeypatch, api_with_token):
    """Test _send_grpc() properly uses secure_channel as context manager."""
    context_entered = False
    context_exited = False
    
    class MockChannel:
        async def __aenter__(self):
            nonlocal context_entered
            context_entered = True
            return self
            
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            nonlocal context_exited
            context_exited = True
    
    mock_channel = MockChannel()
    mock_stub = MagicMock()
    
    async def mock_callback(stub, metadata):
        # Verify we're inside the context when callback is called
        assert context_entered
        assert not context_exited
        return beam_pb2.BeamResponse()
    
    monkeypatch.setattr(grpc.aio, "secure_channel", lambda *args, **kwargs: mock_channel)
    monkeypatch.setattr(beam_pb2_grpc, "BeamStub", MagicMock(return_value=mock_stub))
    monkeypatch.setattr(grpc, "ssl_channel_credentials", MagicMock())
    
    await api_with_token._send_grpc(mock_callback)
    
    # Verify context manager was used properly
    assert context_entered
    assert context_exited
