# VivintPy Device Documentation

This document provides detailed information about the device classes available in the `vivintpy` library. It aims to be a comprehensive guide for developers, covering constructors, public properties, and public methods for each device.

**Reading this Document:**

*   **Inheritance:** Device classes often inherit from base classes like `VivintDevice` or `BypassTamperDevice`. Key inherited members are typically listed directly under each concrete device for clarity, but understanding the base classes can provide additional context.
*   **Type Hints:** Python type hints are used extensively. `Optional[X]` means the value can be `X` or `None`. String literals like `"AlarmPanel"` are used for forward references to avoid circular imports in type hinting.
*   **Source Links:** Where available, links to the approximate source code location are provided for deeper understanding.

---

## Base Device Classes

These are foundational classes from which specific device types inherit.

### `VivintDevice`

Base class for all Vivint devices. Provides common attributes and functionalities.

**Key Properties (Inherited by all devices):**

| Property                 | Type                           | Description                                                                 | Source Link                                      |
| ------------------------ | ------------------------------ | --------------------------------------------------------------------------- | ------------------------------------------------ |
| `id`                     | `str`                          | The unique identifier of the device.                                        | `vivintpy/devices/__init__.py`                   |
| `name`                   | `str`                          | The name of the device.                                                     | `vivintpy/devices/__init__.py`                   |
| `mac_address`            | `Optional[str]`                | The MAC address of the device.                                              | `vivintpy/devices/__init__.py`                   |
| `serial_number`          | `Optional[str]`                | The serial number of the device.                                            | `vivintpy/devices/__init__.py`                   |
| `software_version`       | `Optional[str]`                | The software version of the device.                                         | `vivintpy/devices/__init__.py`                   |
| `firmware_version`       | `Optional[str]`                | The firmware version of the device.                                         | `vivintpy/devices/__init__.py`                   |
| `model`                  | `Optional[str]`                | The model of the device.                                                    | `vivintpy/devices/__init__.py`                   |
| `manufacturer`           | `Optional[str]`                | The manufacturer of the device.                                             | `vivintpy/devices/__init__.py`                   |
| `is_online`              | `bool`                         | Indicates if the device is currently online.                                | `vivintpy/devices/__init__.py`                   |
| `raw_data`               | `dict`                         | The raw data dictionary for the device.                                     | `vivintpy/devices/__init__.py`                   |
| `data_model`             | `VivintDeviceData`             | The Pydantic model representing the device's data.                          | `vivintpy/devices/__init__.py`                   |
| `associated_alarm_panel` | `"AlarmPanel"`                 | A reference to the alarm panel this device is associated with.              | `vivintpy/devices/__init__.py`                   |

**Key Methods (Inherited by all devices):**

| Method Signature                               | Description                                                                    |
| ---------------------------------------------- | ------------------------------------------------------------------------------ |
| `async refresh() -> None`                      | Refreshes the device's data from the API.                                      |
| `update_data(new_data: dict) -> None`          | Updates the device's internal data with new data.                              |
| `handle_pubnub_message(message: dict) -> None` | Handles real-time messages from PubNub relevant to this device. (If implemented) |

### `BypassTamperDevice`

Inherits from: `VivintDevice`

Base class for devices that can be bypassed and can report tamper status.

**Additional Key Properties (Inherited by relevant devices):**

| Property      | Type   | Description                                  |
| ------------- | ------ | -------------------------------------------- |
| `is_bypassed` | `bool` | Indicates if the device is currently bypassed. |
| `is_tampered` | `bool` | Indicates if the device is currently tampered. |

**Additional Key Methods (Inherited by relevant devices):**

| Method Signature               | Description                               |
| ------------------------------ | ----------------------------------------- |
| `async set_bypass(bypass: bool) -> None` | Sets the bypass state of the device.      |
| `async bypass() -> None`       | Bypasses the device.                      |
| `async unbypass() -> None`     | Unbypasses (activates) the device.        |

---

## Concrete Device Classes

### `AlarmPanel`

Represents the central alarm panel.

Inherits from: `VivintDevice`

**Constructor:**

`AlarmPanel(data: dict, panel_id: int, system_id: int, api: VivintSkyApi, pubnub: PubNub)`

Initializes an AlarmPanel instance.

**Properties:**

| Property                           | Type                               | Description                                                                                                | Source Link                                |
| ---------------------------------- | ---------------------------------- | ---------------------------------------------------------------------------------------------------------- | ------------------------------------------ |
| `id`                               | `str`                              | The unique identifier of the alarm panel.                                                                  | `vivintpy/devices/alarm_panel.py`          |
| `name`                             | `str`                              | The name of the alarm panel (often "Main Panel").                                                          | `vivintpy/devices/alarm_panel.py`          |
| `mac_address`                      | `Optional[str]`                    | The MAC address of the panel.                                                                              | `vivintpy/devices/alarm_panel.py`          |
| `serial_number`                    | `Optional[str]`                    | The serial number of the panel.                                                                            | `vivintpy/devices/alarm_panel.py`          |
| `software_version`                 | `Optional[str]`                    | The software version running on the panel.                                                                 | `vivintpy/devices/alarm_panel.py`          |
| `firmware_version`                 | `Optional[str]`                    | The firmware version of the panel.                                                                         | `vivintpy/devices/alarm_panel.py`          |
| `model`                            | `Optional[str]`                    | The model of the panel.                                                                                    | `vivintpy/devices/alarm_panel.py`          |
| `manufacturer`                     | `Optional[str]`                    | The manufacturer of the panel.                                                                             | `vivintpy/devices/alarm_panel.py`          |
| `is_online`                        | `bool`                             | Indicates if the panel is online.                                                                          | `vivintpy/devices/alarm_panel.py`          |
| `state`                            | `AlarmPanelState`                  | The current arming state of the panel (e.g., `DISARMED`, `ARMED_STAY`, `ARMED_AWAY`).                        | `vivintpy/devices/alarm_panel.py`          |
| `is_armed`                         | `bool`                             | True if the panel is in any armed state (`ARMED_STAY` or `ARMED_AWAY`).                                      | `vivintpy/devices/alarm_panel.py`          |
| `devices`                          | `List[VivintDevice]`               | A list of all devices associated with this alarm panel.                                                      | `vivintpy/devices/alarm_panel.py`          |
| `panel_id`                         | `int`                              | The panel's unique ID.                                                                                     | `vivintpy/devices/alarm_panel.py`          |
| `system_id`                        | `int`                              | The system ID this panel belongs to.                                                                       | `vivintpy/devices/alarm_panel.py`          |
| `can_arm_stay`                     | `bool`                             | Indicates if the panel supports arming in "stay" mode. (Dynamically checked capability)                     | `vivintpy/devices/alarm_panel.py`          |
| `can_arm_away`                     | `bool`                             | Indicates if the panel supports arming in "away" mode. (Dynamically checked capability)                     | `vivintpy/devices/alarm_panel.py`          |
| `can_disarm`                       | `bool`                             | Indicates if the panel supports disarming. (Dynamically checked capability)                                | `vivintpy/devices/alarm_panel.py`          |
| `can_reboot`                       | `bool`                             | Indicates if the panel can be rebooted remotely. (Dynamically checked capability)                          | `vivintpy/devices/alarm_panel.py`          |
| `can_bypass_sensors`               | `bool`                             | Indicates if the panel allows bypassing sensors. (Dynamically checked capability)                          | `vivintpy/devices/alarm_panel.py`          |
| `can_set_panel_credentials`        | `bool`                             | Indicates if panel credentials can be set remotely. (Dynamically checked capability)                       | `vivintpy/devices/alarm_panel.py`          |
| `can_get_panel_credentials`        | `bool`                             | Indicates if panel credentials can be retrieved. (Dynamically checked capability)                          | `vivintpy/devices/alarm_panel.py`          |
| *... (other `can_...` properties)* | `bool`                             | Additional capability flags based on panel features (e.g., `can_get_panel_config`, `can_set_panel_users`). | `vivintpy/devices/alarm_panel.py`          |
| `credentials`                      | `Optional[PanelCredentialsData]`   | Panel credentials data, if fetched.                                                                        | `vivintpy/devices/alarm_panel.py`          |

**Methods:**

| Method Signature                                                                 | Description                                                                                                |
| -------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| `async arm_stay() -> None`                                                       | Arms the panel in "stay" mode.                                                                             |
| `async arm_away() -> None`                                                       | Arms the panel in "away" mode.                                                                             |
| `async disarm() -> None`                                                         | Disarms the panel.                                                                                         |
| `async reboot() -> None`                                                         | Reboots the alarm panel.                                                                                   |
| `async get_panel_credentials() -> PanelCredentialsData`                            | Retrieves the panel's credentials.                                                                         |
| `async set_panel_credentials(new_pin: str, duress_pin: str) -> None`             | Sets new PIN and duress PIN for the panel.                                                                 |
| `async refresh() -> None`                                                        | Refreshes the alarm panel's data and its associated devices.                                               |
| `handle_pubnub_message(message: dict) -> None`                                   | Handles real-time messages from PubNub for the panel and routes them to relevant devices.                  |
| `update_data(new_data: dict) -> None`                                            | Updates the panel's internal data.                                                                         |
| `get_device_by_id(device_id: Union[str, int]) -> Optional[VivintDevice]`         | Retrieves a specific device associated with the panel by its ID.                                           |
| `get_devices_by_type(device_type: DeviceType) -> List[VivintDevice]`             | Retrieves all devices of a specific type associated with the panel.                                        |
| `async get_panel_update() -> PanelUpdateData`                                    | Fetches detailed panel update information.                                                                 |
| `async get_panel_config() -> dict`                                               | Retrieves the panel's configuration.                                                                       |
| `async set_panel_config(config: dict) -> None`                                   | Sets the panel's configuration.                                                                            |
| `async get_panel_diagnostics() -> dict`                                          | Retrieves panel diagnostic information.                                                                    |
| `async get_panel_users() -> dict`                                                | Retrieves panel user information.                                                                          |
| `async set_panel_users(users_data: dict) -> None`                                | Sets panel user information.                                                                               |
| *... (other panel-specific get/set methods)*                                     | Additional methods for interacting with specific panel settings and features.                              |

---

### `Camera`

Represents a camera device.

Inherits from: `VivintDevice`

**Constructor:**

`Camera(data: dict, alarm_panel: "AlarmPanel")`

Initializes a Camera instance.

**Properties:**

| Property                     | Type                           | Description                                                                                             | Source Link                          |
| ---------------------------- | ------------------------------ | ------------------------------------------------------------------------------------------------------- | ------------------------------------ |
| `id`                         | `str`                          | Camera ID.                                                                                              | `vivintpy/devices/camera.py`         |
| `name`                       | `str`                          | Camera name.                                                                                            | `vivintpy/devices/camera.py`         |
| `mac_address`                | `Optional[str]`                | MAC address.                                                                                            | `vivintpy/devices/camera.py`         |
| `serial_number`              | `Optional[str]`                | Serial number.                                                                                          | `vivintpy/devices/camera.py`         |
| `software_version`           | `Optional[str]`                | Software version.                                                                                       | `vivintpy/devices/camera.py`         |
| `firmware_version`           | `Optional[str]`                | Firmware version.                                                                                       | `vivintpy/devices/camera.py`         |
| `model`                      | `Optional[str]`                | Camera model.                                                                                           | `vivintpy/devices/camera.py`         |
| `manufacturer`               | `Optional[str]`                | Camera manufacturer.                                                                                    | `vivintpy/devices/camera.py`         |
| `is_online`                  | `bool`                         | Online status.                                                                                          | `vivintpy/devices/camera.py`         |
| `capture_clip_on_motion`     | `bool`                         | Whether the camera captures a clip on motion.                                                           | `vivintpy/devices/camera.py`         |
| `is_in_privacy_mode`         | `bool`                         | Whether the camera is in privacy mode.                                                                  | `vivintpy/devices/camera.py`         |
| `is_recording_enabled`       | `bool`                         | Whether recording is enabled.                                                                           | `vivintpy/devices/camera.py`         |
| `is_sound_enabled`           | `bool`                         | Whether sound detection is enabled.                                                                     | `vivintpy/devices/camera.py`         |
| `is_mic_enabled`             | `bool`                         | Whether the microphone is enabled.                                                                      | `vivintpy/devices/camera.py`         |
| `is_speaker_enabled`         | `bool`                         | Whether the speaker is enabled.                                                                         | `vivintpy/devices/camera.py`         |
| `thumbnail_url`              | `Optional[str]`                | URL for the camera's thumbnail image.                                                                   | `vivintpy/devices/camera.py`         |
| `rtsp_access_url`            | `Optional[str]`                | RTSP access URL for the camera stream (requires fetching).                                              | `vivintpy/devices/camera.py`         |
| `wireless_signal_strength`   | `Optional[int]`                | Wireless signal strength in dBm.                                                                        | `vivintpy/devices/camera.py`         |
| `camera_rules`               | `Optional[Dict]`               | Current camera rules.                                                                                   | `vivintpy/devices/camera.py`         |
| `associated_alarm_panel`     | `"AlarmPanel"`                 | The alarm panel this camera is associated with.                                                         | `vivintpy/devices/camera.py`         |

**Methods:**

| Method Signature                                                              | Description                                                                                                |
| ----------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| `async request_thumbnail() -> None`                                           | Requests a new thumbnail image for the camera.                                                             |
| `async get_rtsp_access_url(url_type: RtspUrlType = RtspUrlType.INTERNAL) -> str` | Gets the RTSP access URL for the camera stream.                                                            |
| `async reboot() -> None`                                                      | Reboots the camera.                                                                                        |
| `async set_privacy_mode(enabled: bool) -> None`                               | Enables or disables privacy mode for the camera.                                                           |
| `async set_capture_clip_on_motion(enabled: bool) -> None`                     | Enables or disables capturing a clip on motion.                                                            |
| `async set_recording_enabled(enabled: bool) -> None`                          | Enables or disables recording.                                                                             |
| `async set_sound_enabled(enabled: bool) -> None`                              | Enables or disables sound detection.                                                                       |
| `async set_mic_enabled(enabled: bool) -> None`                                | Enables or disables the microphone.                                                                        |
| `async set_speaker_enabled(enabled: bool) -> None`                            | Enables or disables the speaker.                                                                           |
| `async update_camera_rules(rules: Dict) -> None`                              | Updates the camera rules.                                                                                  |
| `handle_pubnub_message(message: dict) -> None`                                | Handles real-time messages from PubNub relevant to this camera.                                            |

---

### `DoorLock`

Represents a door lock device.

Inherits from: `BypassTamperDevice`

**Constructor:**

`DoorLock(data: dict, alarm_panel: "AlarmPanel")`

Initializes a DoorLock instance.

**Properties:**

| Property                 | Type                           | Description                                                     | Source Link                             |
| ------------------------ | ------------------------------ | --------------------------------------------------------------- | --------------------------------------- |
| `id`                     | `str`                          | Door lock ID.                                                   | `vivintpy/devices/door_lock.py`         |
| `name`                   | `str`                          | Door lock name.                                                 | `vivintpy/devices/door_lock.py`         |
| `mac_address`            | `Optional[str]`                | MAC address.                                                    | `vivintpy/devices/door_lock.py`         |
| `serial_number`          | `Optional[str]`                | Serial number.                                                  | `vivintpy/devices/door_lock.py`         |
| `software_version`       | `Optional[str]`                | Software version.                                               | `vivintpy/devices/door_lock.py`         |
| `firmware_version`       | `Optional[str]`                | Firmware version.                                               | `vivintpy/devices/door_lock.py`         |
| `model`                  | `Optional[str]`                | Door lock model.                                                | `vivintpy/devices/door_lock.py`         |
| `manufacturer`           | `Optional[str]`                | Door lock manufacturer.                                         | `vivintpy/devices/door_lock.py`         |
| `is_online`              | `bool`                         | Online status.                                                  | `vivintpy/devices/door_lock.py`         |
| `is_locked`              | `bool`                         | Whether the door lock is currently locked.                      | `vivintpy/devices/door_lock.py`         |
| `low_battery`            | `bool`                         | Whether the door lock has low battery.                          | `vivintpy/devices/door_lock.py`         |
| `is_bypassed`            | `bool`                         | Indicates if the device is currently bypassed.                  | `vivintpy/devices/__init__.py`          |
| `is_tampered`            | `bool`                         | Indicates if the device is currently tampered.                  | `vivintpy/devices/__init__.py`          |
| `associated_alarm_panel` | `"AlarmPanel"`                 | The alarm panel this door lock is associated with.              | `vivintpy/devices/door_lock.py`         |

**Methods:**

| Method Signature                               | Description                                                               |
| ---------------------------------------------- | ------------------------------------------------------------------------- |
| `async set_state(lock: bool) -> None`          | Sets the lock state (True to lock, False to unlock).                      |
| `async lock() -> None`                         | Locks the door.                                                           |
| `async unlock() -> None`                       | Unlocks the door.                                                         |
| `async set_bypass(bypass: bool) -> None`       | Sets the bypass state of the device. (Inherited)                          |
| `async bypass() -> None`                       | Bypasses the device. (Inherited)                                          |
| `async unbypass() -> None`                     | Unbypasses (activates) the device. (Inherited)                            |
| `handle_pubnub_message(message: dict) -> None` | Handles real-time messages from PubNub relevant to this door lock.        |

---

### `GarageDoor`

Represents a garage door opener.

Inherits from: `VivintDevice`

**Constructor:**

`GarageDoor(data: dict, alarm_panel: "AlarmPanel")`

Initializes a GarageDoor instance.

**Properties:**

| Property                 | Type                           | Description                                                                | Source Link                              |
| ------------------------ | ------------------------------ | -------------------------------------------------------------------------- | ---------------------------------------- |
| `id`                     | `str`                          | Garage door ID.                                                            | `vivintpy/devices/garage_door.py`        |
| `name`                   | `str`                          | Garage door name.                                                          | `vivintpy/devices/garage_door.py`        |
| `mac_address`            | `Optional[str]`                | MAC address.                                                               | `vivintpy/devices/garage_door.py`        |
| `serial_number`          | `Optional[str]`                | Serial number.                                                             | `vivintpy/devices/garage_door.py`        |
| `software_version`       | `Optional[str]`                | Software version.                                                          | `vivintpy/devices/garage_door.py`        |
| `firmware_version`       | `Optional[str]`                | Firmware version.                                                          | `vivintpy/devices/garage_door.py`        |
| `model`                  | `Optional[str]`                | Garage door model.                                                         | `vivintpy/devices/garage_door.py`        |
| `manufacturer`           | `Optional[str]`                | Garage door manufacturer.                                                  | `vivintpy/devices/garage_door.py`        |
| `is_online`              | `bool`                         | Online status.                                                             | `vivintpy/devices/garage_door.py`        |
| `state`                  | `GarageDoorState`              | Current state of the garage door (`OPEN`, `OPENING`, `CLOSED`, `CLOSING`). | `vivintpy/devices/garage_door.py`        |
| `is_closed`              | `bool`                         | Whether the garage door is closed.                                         | `vivintpy/devices/garage_door.py`        |
| `is_opening`             | `bool`                         | Whether the garage door is currently opening.                              | `vivintpy/devices/garage_door.py`        |
| `is_closing`             | `bool`                         | Whether the garage door is currently closing.                              | `vivintpy/devices/garage_door.py`        |
| `associated_alarm_panel` | `"AlarmPanel"`                 | The alarm panel this garage door is associated with.                       | `vivintpy/devices/garage_door.py`        |

**Methods:**

| Method Signature                                       | Description                                                                 |
| ------------------------------------------------------ | --------------------------------------------------------------------------- |
| `async set_state(state: GarageDoorState) -> None`      | Sets the state of the garage door (e.g., `GarageDoorState.OPEN`).           |
| `async close() -> None`                                | Closes the garage door.                                                     |
| `async open() -> None`                                 | Opens the garage door.                                                      |
| `handle_pubnub_message(message: dict) -> None`         | Handles real-time messages from PubNub relevant to this garage door.        |

---

### `Switch`

Represents a generic switch device. Base class for `BinarySwitch` and `MultilevelSwitch`.

Inherits from: `VivintDevice`

**Constructor:**

`Switch(data: dict, alarm_panel: "AlarmPanel")`

Initializes a Switch instance.

**Properties:**

| Property                 | Type                           | Description                                                              | Source Link                         |
| ------------------------ | ------------------------------ | ------------------------------------------------------------------------ | ----------------------------------- |
| `id`                     | `str`                          | Switch ID.                                                               | `vivintpy/devices/switch.py`        |
| `name`                   | `str`                          | Switch name.                                                             | `vivintpy/devices/switch.py`        |
| `mac_address`            | `Optional[str]`                | MAC address.                                                             | `vivintpy/devices/switch.py`        |
| `serial_number`          | `Optional[str]`                | Serial number.                                                           | `vivintpy/devices/switch.py`        |
| `software_version`       | `Optional[str]`                | Software version.                                                        | `vivintpy/devices/switch.py`        |
| `firmware_version`       | `Optional[str]`                | Firmware version.                                                        | `vivintpy/devices/switch.py`        |
| `model`                  | `Optional[str]`                | Switch model.                                                            | `vivintpy/devices/switch.py`        |
| `manufacturer`           | `Optional[str]`                | Switch manufacturer.                                                     | `vivintpy/devices/switch.py`        |
| `is_online`              | `bool`                         | Online status.                                                           | `vivintpy/devices/switch.py`        |
| `is_on`                  | `bool`                         | Whether the switch is currently on.                                      | `vivintpy/devices/switch.py`        |
| `level`                  | `Optional[int]`                | Brightness level (0-100) if it's a multilevel switch, else None.         | `vivintpy/devices/switch.py`        |
| `associated_alarm_panel` | `"AlarmPanel"`                 | The alarm panel this switch is associated with.                          | `vivintpy/devices/switch.py`        |

**Methods:**

| Method Signature                               | Description                                                               |
| ---------------------------------------------- | ------------------------------------------------------------------------- |
| `async set_state(is_on: bool) -> None`         | Sets the switch state (True for on, False for off).                       |
| `async turn_on() -> None`                      | Turns the switch on.                                                      |
| `async turn_off() -> None`                     | Turns the switch off.                                                     |
| `handle_pubnub_message(message: dict) -> None` | Handles real-time messages from PubNub relevant to this switch.           |

---

### `BinarySwitch`

Represents a simple on/off switch.

Inherits from: `Switch`

**Constructor:**

`BinarySwitch(data: dict, alarm_panel: "AlarmPanel")`

Initializes a BinarySwitch instance.

**Properties:**

(Inherits all properties from `Switch`. The `level` property will typically be `None`.)

**Methods:**

(Inherits all methods from `Switch`.)

---

### `MultilevelSwitch`

Represents a switch with adjustable levels (e.g., a dimmer).

Inherits from: `Switch`

**Constructor:**

`MultilevelSwitch(data: dict, alarm_panel: "AlarmPanel")`

Initializes a MultilevelSwitch instance.

**Properties:**

(Inherits all properties from `Switch`. The `level` property indicates brightness from 0-100.)

**Methods:**

(Inherits `set_state`, `turn_on`, `turn_off`, `handle_pubnub_message` from `Switch`.)

| Method Signature                     | Description                                         |
| ------------------------------------ | --------------------------------------------------- |
| `async set_level(level: int) -> None`  | Sets the brightness level of the switch (0-100).    |

---

### `Thermostat`

Represents a thermostat device.

Inherits from: `VivintDevice`

**Constructor:**

`Thermostat(data: dict, alarm_panel: "AlarmPanel")`

Initializes a Thermostat instance.

**Properties:**

| Property                 | Type                           | Description                                                                                                | Source Link                            |
| ------------------------ | ------------------------------ | ---------------------------------------------------------------------------------------------------------- | -------------------------------------- |
| `id`                     | `str`                          | Thermostat ID.                                                                                             | `vivintpy/devices/thermostat.py`       |
| `name`                   | `str`                          | Thermostat name.                                                                                           | `vivintpy/devices/thermostat.py`       |
| `mac_address`            | `Optional[str]`                | MAC address.                                                                                               | `vivintpy/devices/thermostat.py`       |
| `serial_number`          | `Optional[str]`                | Serial number.                                                                                             | `vivintpy/devices/thermostat.py`       |
| `software_version`       | `Optional[str]`                | Software version.                                                                                          | `vivintpy/devices/thermostat.py`       |
| `firmware_version`       | `Optional[str]`                | Firmware version.                                                                                          | `vivintpy/devices/thermostat.py`       |
| `model`                  | `Optional[str]`                | Thermostat model.                                                                                          | `vivintpy/devices/thermostat.py`       |
| `manufacturer`           | `Optional[str]`                | Thermostat manufacturer.                                                                                   | `vivintpy/devices/thermostat.py`       |
| `is_online`              | `bool`                         | Online status.                                                                                             | `vivintpy/devices/thermostat.py`       |
| `temperature`            | `Optional[float]`              | Current ambient temperature.                                                                               | `vivintpy/devices/thermostat.py`       |
| `cool_set_point`         | `Optional[float]`              | Desired temperature for cooling.                                                                           | `vivintpy/devices/thermostat.py`       |
| `heat_set_point`         | `Optional[float]`              | Desired temperature for heating.                                                                           | `vivintpy/devices/thermostat.py`       |
| `fan_mode`               | `Optional[ThermostatFanMode]`  | Current fan mode (e.g., `AUTO`, `ON`).                                                                       | `vivintpy/devices/thermostat.py`       |
| `operating_mode`         | `Optional[ThermostatOperatingMode]` | Current operating mode (e.g., `OFF`, `COOL`, `HEAT`, `AUTO`).                                                | `vivintpy/devices/thermostat.py`       |
| `humidity`               | `Optional[int]`                | Current humidity level (percentage).                                                                       | `vivintpy/devices/thermostat.py`       |
| `is_on`                  | `bool`                         | Whether the thermostat is actively heating or cooling (derived from `operating_mode`).                       | `vivintpy/devices/thermostat.py`       |
| `schedule_enabled`       | `Optional[bool]`               | Whether the thermostat schedule is enabled.                                                                | `vivintpy/devices/thermostat.py`       |
| `hold_enabled`           | `Optional[bool]`               | Whether the thermostat is in hold mode (overriding schedule).                                              | `vivintpy/devices/thermostat.py`       |
| `min_cool_set_point`     | `Optional[float]`              | Minimum allowed cool set point.                                                                            | `vivintpy/devices/thermostat.py`       |
| `max_cool_set_point`     | `Optional[float]`              | Maximum allowed cool set point.                                                                            | `vivintpy/devices/thermostat.py`       |

**Methods:**

| Method Signature                                       | Description                                                                    |
| ------------------------------------------------------ | ------------------------------------------------------------------------------ |
| `async refresh() -> None`                              | Refreshes the device's data from the API. (Inherited)                          |
| `update_data(new_data: dict) -> None`                  | Updates the device's internal data with new data. (Inherited)                  |
| `handle_pubnub_message(message: dict) -> None`         | Handles real-time messages from PubNub relevant to this device. (Inherited, if implemented by base) |
| `async set_state(**kwargs: Any) -> None`               | Sets the state of the thermostat (e.g., temperature, mode, fan mode).          |
| `static celsius_to_fahrenheit(celsius: float) -> int`  | Converts a temperature from Celsius to Fahrenheit.                             |

---

### `WirelessSensor`

Represents a Vivint wireless sensor device, such as a door/window sensor, motion sensor, or glass break detector. These devices typically report state changes (e.g., open/closed, motion/no motion) and may support bypassing.

Inherits from: `BypassTamperDevice`, `VivintDevice`

**Constructor:**

`WirelessSensor(data: dict | WirelessSensorData, alarm_panel: "AlarmPanel" | None = None) -> None`

Initializes a wireless sensor instance.

**Properties:**

| Property                 | Type                           | Description                                                                                      | Source Link                                         |
| ------------------------ | ------------------------------ | ------------------------------------------------------------------------------------------------ | --------------------------------------------------- |
| `id`                     | `str`                          | The unique identifier of the device. (Inherited)                                                 | `vivintpy/devices/__init__.py`                      |
| `name`                   | `str`                          | The name of the device. (Inherited)                                                              | `vivintpy/devices/__init__.py`                      |
| `mac_address`            | `Optional[str]`                | The MAC address of the device. (Inherited)                                                       | `vivintpy/devices/__init__.py`                      |
| `serial_number`          | `Optional[str]`                | The serial number of the device. (Inherited)                                                     | `vivintpy/devices/__init__.py`                      |
| `software_version`       | `Optional[str]`                | The firmware version of the device, reported as software version for this device type.           | `vivintpy/devices/wireless_sensor.py`               |
| `firmware_version`       | `Optional[str]`                | The firmware version of the device. (Inherited, often same as `software_version` for sensors)    | `vivintpy/devices/__init__.py`                      |
| `model`                  | `str`                          | The name of the `equipment_code` (e.g., "DW11", "PIR1"), indicating the sensor model.            | `vivintpy/devices/wireless_sensor.py`               |
| `manufacturer`           | `Optional[str]`                | The manufacturer of the device. (Inherited)                                                      | `vivintpy/devices/__init__.py`                      |
| `is_online`              | `bool`                         | Indicates if the device is currently online. (Inherited)                                         | `vivintpy/devices/__init__.py`                      |
| `raw_data`               | `dict`                         | The raw data dictionary for the device. (Inherited)                                              | `vivintpy/devices/__init__.py`                      |
| `data_model`             | `WirelessSensorData`           | The Pydantic model representing the device's data.                                               | `vivintpy/devices/wireless_sensor.py`               |
| `associated_alarm_panel` | `"AlarmPanel"`                 | A reference to the alarm panel this device is associated with. (Inherited)                       | `vivintpy/devices/__init__.py`                      |
| `equipment_code`         | `EquipmentCode`                | The specific equipment code of this sensor.                                                      | `vivintpy/devices/wireless_sensor.py`               |
| `equipment_type`         | `EquipmentType`                | The general equipment type of this sensor (e.g., `CONTACT_SENSOR`, `MOTION_SENSOR`).             | `vivintpy/devices/wireless_sensor.py`               |
| `sensor_type`            | `SensorType`                   | The detailed sensor type (e.g., `DOOR`, `WINDOW`, `MOTION`).                                     | `vivintpy/devices/wireless_sensor.py`               |
| `is_on`                  | `bool`                         | Returns `True` if the sensor's state is "on" (e.g., door open, motion detected).                 | `vivintpy/devices/wireless_sensor.py`               |
| `is_valid`               | `bool`                         | Returns `True` if the wireless sensor is considered valid by the system (has serial, known type). | `vivintpy/devices/wireless_sensor.py`               |
| `is_bypassed`            | `bool`                         | Indicates if the device is currently bypassed. (Inherited from `BypassTamperDevice`)             | `vivintpy/devices/__init__.py`                      |
| `is_tampered`            | `bool`                         | Indicates if the device is currently tampered. (Inherited from `BypassTamperDevice`)             | `vivintpy/devices/__init__.py`                      |

**Methods:**

| Method Signature                                       | Description                                                                                      |
| ------------------------------------------------------ | ------------------------------------------------------------------------------------------------ |
| `async refresh() -> None`                              | Refreshes the device's data from the API. (Inherited)                                            |
| `update_data(new_data: dict, override: bool = False) -> None` | Updates the device's internal data with new data. (Overrides base `VivintDevice` method)         |
| `handle_pubnub_message(message: dict) -> None`         | Handles real-time messages from PubNub relevant to this device. (Inherited, if implemented by base) |
| `async set_bypass(bypass: bool) -> None`               | Sets the bypass state of the device. (Overrides base `BypassTamperDevice` method)                |
| `async bypass() -> None`                               | Bypasses the device. (Overrides base `BypassTamperDevice` method)                                |
| `async unbypass() -> None`                             | Unbypasses (activates) the device. (Overrides base `BypassTamperDevice` method)                  |

| `min_heat_set_point`     | `Optional[float]`              | Minimum allowed heat set point.                                                                            | `vivintpy/devices/thermostat.py`       |
| `max_heat_set_point`     | `Optional[float]`              | Maximum allowed heat set point.                                                                            | `vivintpy/devices/thermostat.py`       |
| `associated_alarm_panel` | `"AlarmPanel"`                 | The alarm panel this thermostat is associated with.                                                        | `vivintpy/devices/thermostat.py`       |

**Methods:**

| Method Signature                                                                                                                               | Description                                                                                                                               |
| ---------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| `async set_state(cool_set_point: Optional[float] = None, heat_set_point: Optional[float] = None, fan_mode: Optional[ThermostatFanMode] = None, operating_mode: Optional[ThermostatOperatingMode] = None) -> None` | Sets the thermostat's state (set points, fan mode, operating mode).                                                                       |
| `handle_pubnub_message(message: dict) -> None`                                                                                                 | Handles real-time messages from PubNub relevant to this thermostat.                                                                       |
| `static celsius_to_fahrenheit(celsius: float) -> float`                                                                                        | Converts Celsius to Fahrenheit. (Utility method)                                                                                          |

---

### `WirelessSensor`

Represents a wireless sensor (e.g., door/window sensor, motion sensor).

Inherits from: `BypassTamperDevice`

**Constructor:**

`WirelessSensor(data: dict, alarm_panel: "AlarmPanel")`

Initializes a WirelessSensor instance.

**Properties:**

| Property                 | Type                               | Description                                                                                                | Source Link                                |
| ------------------------ | ---------------------------------- | ---------------------------------------------------------------------------------------------------------- | ------------------------------------------ |
| `id`                     | `str`                              | Sensor ID.                                                                                                 | `vivintpy/devices/wireless_sensor.py`      |
| `name`                   | `str`                              | Sensor name.                                                                                               | `vivintpy/devices/wireless_sensor.py`      |
| `mac_address`            | `Optional[str]`                    | MAC address.                                                                                               | `vivintpy/devices/wireless_sensor.py`      |
| `serial_number`          | `Optional[str]`                    | Serial number.                                                                                             | `vivintpy/devices/wireless_sensor.py`      |
| `software_version`       | `Optional[str]`                    | Software version.                                                                                          | `vivintpy/devices/wireless_sensor.py`      |
| `firmware_version`       | `Optional[str]`                    | Firmware version.                                                                                          | `vivintpy/devices/wireless_sensor.py`      |
| `model`                  | `Optional[str]`                    | Sensor model.                                                                                              | `vivintpy/devices/wireless_sensor.py`      |
| `manufacturer`           | `Optional[str]`                    | Sensor manufacturer.                                                                                       | `vivintpy/devices/wireless_sensor.py`      |
| `is_online`              | `bool`                             | Online status.                                                                                             | `vivintpy/devices/wireless_sensor.py`      |
| `equipment_code`         | `Optional[int]`                    | Equipment code identifying the sensor type.                                                                | `vivintpy/devices/wireless_sensor.py`      |
| `sensor_type`            | `Optional[WirelessSensorType]`     | Type of sensor (e.g., `CONTACT_SENSOR`, `MOTION_SENSOR`), derived from `equipment_code`.                   | `vivintpy/devices/wireless_sensor.py`      |
| `is_on`                  | `bool`                             | Current state of the sensor (e.g., True if a contact sensor is open, or motion is detected).                | `vivintpy/devices/wireless_sensor.py`      |
| `is_bypassed`            | `bool`                             | Indicates if the device is currently bypassed.                                                             | `vivintpy/devices/__init__.py`             |
| `is_tampered`            | `bool`                             | Indicates if the device is currently tampered.                                                             | `vivintpy/devices/__init__.py`             |
| `low_battery`            | `bool`                             | Whether the sensor has low battery.                                                                        | `vivintpy/devices/wireless_sensor.py`      |
| `is_valid`               | `bool`                             | Whether the sensor is considered valid (based on `equipment_code`).                                        | `vivintpy/devices/wireless_sensor.py`      |
| `associated_alarm_panel` | `"AlarmPanel"`                     | The alarm panel this sensor is associated with.                                                            | `vivintpy/devices/wireless_sensor.py`      |

**Methods:**

| Method Signature                               | Description                                                               |
| ---------------------------------------------- | ------------------------------------------------------------------------- |
| `async set_bypass(bypass: bool) -> None`       | Sets the bypass state of the device. (Inherited)                          |
| `async bypass() -> None`                       | Bypasses the device. (Inherited)                                          |
| `async unbypass() -> None`                     | Unbypasses (activates) the device. (Inherited)                            |
| `handle_pubnub_message(message: dict) -> None` | Handles real-time messages from PubNub relevant to this sensor.           |

---

### `UnknownDevice`

Represents a device whose type is not specifically handled by other classes.

Inherits from: `VivintDevice`

**Constructor:**

`UnknownDevice(data: dict, alarm_panel: "AlarmPanel")`

Initializes an UnknownDevice instance.

**Properties:**

(Inherits all properties from `VivintDevice`. Its primary purpose is to provide a placeholder for unrecognized devices, allowing access to basic information like `id`, `name`, and `raw_data`.)

**Methods:**

(Inherits methods from `VivintDevice`, including `handle_pubnub_message` if implemented in the base or if it receives relevant messages.)

---

## Enumerations

This section would ideally list or link to definitions of Enum types used, such as:

*   `AlarmPanelState`
*   `DeviceType`
*   `GarageDoorState`
*   `RtspUrlType`
*   `ThermostatFanMode`
*   `ThermostatOperatingMode`
*   `WirelessSensorType`

For now, please refer to their usage in the property/method tables and the source code (`vivintpy/enums.py`).
