"""Tests for System.handle_pubnub_message edge cases."""

from __future__ import annotations

import logging
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from vivintpy.api import VivintSkyApi
from vivintpy.const import PubNubMessageAttribute
from vivintpy.const import SystemAttribute as Attribute
from vivintpy.models import SystemData, SystemBody
from vivintpy.system import System


@pytest.fixture()
def mock_api():
    """Create a mock API."""
    return MagicMock(spec=VivintSkyApi)


@pytest.fixture()
def basic_system_data():
    """Create basic system data for testing."""
    return SystemData(
        system=SystemBody(
            panid=12345,
            par=[
                {
                    "panel_id": 123,
                    "partition_id": 1,
                    "mac_address": "AA:BB:CC:DD:EE:FF",
                    "state": "disarmed",
                    "devices": [],
                    "unregistered": []
                }
            ],
            users=[]
        )
    )


@pytest.fixture()
def system_with_panel(mock_api, basic_system_data):
    """Create a system with an alarm panel."""
    return System(
        basic_system_data,
        mock_api,
        name="Test System",
        is_admin=True
    )


def test_handle_pubnub_unknown_message_type(system_with_panel, caplog):
    """Test handle_pubnub_message with unknown message type logs warning."""
    unknown_message = {
        PubNubMessageAttribute.TYPE: "unknown_message_type",
        "some_data": "test"
    }
    
    with caplog.at_level(logging.WARNING):
        system_with_panel.handle_pubnub_message(unknown_message)
    
    assert len(caplog.records) == 1
    assert caplog.records[0].levelname == "WARNING"
    assert "Unknown message received by system 12345" in caplog.records[0].message
    assert "unknown_message_type" in caplog.records[0].message


def test_handle_pubnub_account_partition_missing_partition_id(system_with_panel, caplog):
    """Test account_partition message without partition_id logs debug and returns."""
    partition_message = {
        PubNubMessageAttribute.TYPE: "account_partition",
        PubNubMessageAttribute.DATA: {"some": "data"}
        # Missing partition_id
    }
    
    with caplog.at_level(logging.DEBUG):
        system_with_panel.handle_pubnub_message(partition_message)
    
    assert len(caplog.records) == 1
    assert caplog.records[0].levelname == "DEBUG"
    assert "Ignoring account partition message (no partition id specified" in caplog.records[0].message
    assert "system 12345" in caplog.records[0].message


def test_handle_pubnub_account_partition_none_partition_id(system_with_panel, caplog):
    """Test account_partition message with None partition_id logs debug and returns."""
    partition_message = {
        PubNubMessageAttribute.TYPE: "account_partition",
        PubNubMessageAttribute.PARTITION_ID: None,
        PubNubMessageAttribute.DATA: {"some": "data"}
    }
    
    with caplog.at_level(logging.DEBUG):
        system_with_panel.handle_pubnub_message(partition_message)
    
    assert len(caplog.records) == 1
    assert caplog.records[0].levelname == "DEBUG"
    assert "Ignoring account partition message (no partition id specified" in caplog.records[0].message


def test_handle_pubnub_account_partition_missing_data(system_with_panel, caplog):
    """Test account_partition message without data logs debug and returns."""
    partition_message = {
        PubNubMessageAttribute.TYPE: "account_partition",
        PubNubMessageAttribute.PARTITION_ID: 1
        # Missing data
    }
    
    with caplog.at_level(logging.DEBUG):
        system_with_panel.handle_pubnub_message(partition_message)
    
    assert len(caplog.records) == 1
    assert caplog.records[0].levelname == "DEBUG"
    assert "Ignoring account partition message (no data for system 12345, partition 1)" in caplog.records[0].message


def test_handle_pubnub_account_partition_empty_data(system_with_panel, caplog):
    """Test account_partition message with empty data dict logs debug and returns."""
    partition_message = {
        PubNubMessageAttribute.TYPE: "account_partition",
        PubNubMessageAttribute.PARTITION_ID: 1,
        PubNubMessageAttribute.DATA: {}  # Empty dict should be treated as missing data
    }
    
    # Empty dict should still pass the "DATA not in message" check, so no log should occur
    with caplog.at_level(logging.DEBUG):
        system_with_panel.handle_pubnub_message(partition_message)
    
    # Should not log about missing data since empty dict is still present
    # Should process and find the alarm panel
    debug_logs = [r for r in caplog.records if r.levelname == "DEBUG"]
    assert len(debug_logs) == 0  # No debug logs about missing data


def test_handle_pubnub_account_partition_no_matching_panel(system_with_panel, caplog):
    """Test account_partition message with non-existent partition logs debug."""
    partition_message = {
        PubNubMessageAttribute.TYPE: "account_partition",
        PubNubMessageAttribute.PARTITION_ID: 999,  # Non-existent partition
        PubNubMessageAttribute.DATA: {"some": "data"}
    }
    
    with caplog.at_level(logging.DEBUG):
        system_with_panel.handle_pubnub_message(partition_message)
    
    assert len(caplog.records) == 1
    assert caplog.records[0].levelname == "DEBUG"
    assert "No alarm panel found for system 12345, partition 999" in caplog.records[0].message


def test_handle_pubnub_account_partition_success(system_with_panel):
    """Test successful account_partition message handling."""
    # Mock the alarm panel's handle_pubnub_message method
    alarm_panel = system_with_panel.alarm_panels[0]
    alarm_panel.handle_pubnub_message = MagicMock()
    
    partition_message = {
        PubNubMessageAttribute.TYPE: "account_partition",
        PubNubMessageAttribute.PARTITION_ID: 1,  # Matches our alarm panel
        PubNubMessageAttribute.DATA: {"device_update": "data"}
    }
    
    system_with_panel.handle_pubnub_message(partition_message)
    
    # Verify the alarm panel's handler was called
    alarm_panel.handle_pubnub_message.assert_called_once_with(partition_message)


def test_handle_pubnub_account_system_with_users(system_with_panel):
    """Test account_system message with user data updates."""
    # Mock update_user_data method
    system_with_panel.update_user_data = MagicMock()
    
    system_message = {
        PubNubMessageAttribute.TYPE: "account_system",
        PubNubMessageAttribute.OPERATION: "u",
        PubNubMessageAttribute.DATA: {
            Attribute.USERS: [{"_id": 1, "name": "Test User"}],
            "other_data": "value"
        }
    }
    
    system_with_panel.handle_pubnub_message(system_message)
    
    # Verify user data was updated
    system_with_panel.update_user_data.assert_called_once_with([{"_id": 1, "name": "Test User"}])


def test_handle_pubnub_account_system_without_users(system_with_panel):
    """Test account_system message without user data."""
    # Store original update_data method to verify it's called
    original_update_data = system_with_panel.update_data
    system_with_panel.update_data = MagicMock(side_effect=original_update_data)
    
    system_message = {
        PubNubMessageAttribute.TYPE: "account_system",
        PubNubMessageAttribute.OPERATION: "u",
        PubNubMessageAttribute.DATA: {
            "system_property": "new_value"
        }
    }
    
    system_with_panel.handle_pubnub_message(system_message)
    
    # Verify update_data was called with the data
    system_with_panel.update_data.assert_called_once_with({"system_property": "new_value"})


def test_handle_pubnub_account_system_no_operation(system_with_panel):
    """Test account_system message without operation field."""
    system_message = {
        PubNubMessageAttribute.TYPE: "account_system",
        PubNubMessageAttribute.DATA: {"some": "data"}
        # Missing operation
    }
    
    # Store original update_data method to verify it's NOT called
    system_with_panel.update_data = MagicMock()
    
    system_with_panel.handle_pubnub_message(system_message)
    
    # update_data should not be called if operation is not "u"
    system_with_panel.update_data.assert_not_called()


def test_handle_pubnub_account_system_wrong_operation(system_with_panel):
    """Test account_system message with non-update operation."""
    system_message = {
        PubNubMessageAttribute.TYPE: "account_system",
        PubNubMessageAttribute.OPERATION: "d",  # Delete operation, not update
        PubNubMessageAttribute.DATA: {"some": "data"}
    }
    
    # Store original update_data method to verify it's NOT called
    system_with_panel.update_data = MagicMock()
    
    system_with_panel.handle_pubnub_message(system_message)
    
    # update_data should not be called if operation is not "u"
    system_with_panel.update_data.assert_not_called()


def test_handle_pubnub_account_system_no_data(system_with_panel):
    """Test account_system message without data field."""
    system_message = {
        PubNubMessageAttribute.TYPE: "account_system",
        PubNubMessageAttribute.OPERATION: "u"
        # Missing data
    }
    
    # Store original update_data method to verify it's NOT called
    system_with_panel.update_data = MagicMock()
    
    system_with_panel.handle_pubnub_message(system_message)
    
    # update_data should not be called if data is missing
    system_with_panel.update_data.assert_not_called()


def test_handle_pubnub_empty_message(system_with_panel, caplog):
    """Test handle_pubnub_message with empty message."""
    empty_message = {}
    
    with caplog.at_level(logging.WARNING):
        with pytest.raises(KeyError):
            system_with_panel.handle_pubnub_message(empty_message)


def test_handle_pubnub_message_missing_type(system_with_panel, caplog):
    """Test handle_pubnub_message with message missing type field."""
    message_without_type = {
        "some_field": "some_value"
    }
    
    with caplog.at_level(logging.WARNING):
        with pytest.raises(KeyError):
            system_with_panel.handle_pubnub_message(message_without_type)


def test_handle_pubnub_account_system_users_remove_behavior(system_with_panel):
    """Test that users are removed from data dict after processing."""
    # Mock update_user_data method
    system_with_panel.update_user_data = MagicMock()
    system_with_panel.update_data = MagicMock()
    
    original_data = {
        Attribute.USERS: [{"_id": 1, "name": "Test User"}],
        "other_data": "value"
    }
    
    system_message = {
        PubNubMessageAttribute.TYPE: "account_system",
        PubNubMessageAttribute.OPERATION: "u",
        PubNubMessageAttribute.DATA: original_data
    }
    
    system_with_panel.handle_pubnub_message(system_message)
    
    # Verify users were processed
    system_with_panel.update_user_data.assert_called_once_with([{"_id": 1, "name": "Test User"}])
    
    # Verify update_data was called with data sans users
    expected_data = {"other_data": "value"}
    system_with_panel.update_data.assert_called_once_with(expected_data)
    
    # Verify users were removed from original data dict
    assert Attribute.USERS not in original_data


def test_system_multiple_alarm_panels():
    """Test system with multiple alarm panels for partition routing."""
    # Create system data with multiple partitions
    system_data = SystemData(
        system=SystemBody(
            panid=12345,
            par=[
                {
                    "panel_id": 123,
                    "partition_id": 1,
                    "mac_address": "AA:BB:CC:DD:EE:FF",
                    "state": "disarmed",
                    "devices": [],
                    "unregistered": []
                },
                {
                    "panel_id": 123,
                    "partition_id": 2,
                    "mac_address": "AA:BB:CC:DD:EE:F0",
                    "state": "armed_away",
                    "devices": [],
                    "unregistered": []
                }
            ],
            users=[]
        )
    )
    
    mock_api = MagicMock(spec=VivintSkyApi)
    system = System(system_data, mock_api, name="Multi Panel System", is_admin=True)
    
    # Mock both panels' handle_pubnub_message methods
    panel1 = system.alarm_panels[0]  # partition_id=1
    panel2 = system.alarm_panels[1]  # partition_id=2
    panel1.handle_pubnub_message = MagicMock()
    panel2.handle_pubnub_message = MagicMock()
    
    # Send message to partition 2
    partition_message = {
        PubNubMessageAttribute.TYPE: "account_partition",
        PubNubMessageAttribute.PARTITION_ID: 2,
        PubNubMessageAttribute.DATA: {"device_update": "data"}
    }
    
    system.handle_pubnub_message(partition_message)
    
    # Verify only panel2 was called
    panel1.handle_pubnub_message.assert_not_called()
    panel2.handle_pubnub_message.assert_called_once_with(partition_message)
