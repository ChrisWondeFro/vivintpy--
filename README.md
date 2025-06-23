[![pypi](https://img.shields.io/pypi/v/vivintpy?style=for-the-badge)](https://pypi.org/project/vivintpy)
[![downloads](https://img.shields.io/pypi/dm/vivintpy?style=for-the-badge)](https://pypi.org/project/vivintpy)
[![Buy Me A Coffee/Beer](https://img.shields.io/badge/Buy_Me_A_☕/🍺-F16061?style=for-the-badge&logo=ko-fi&logoColor=white&labelColor=grey)](https://ko-fi.com/natekspencer)

# vivintpy

[![PyPI version](https://img.shields.io/pypi/v/vivintpy?style=for-the-badge)](https://pypi.org/project/vivintpy)
[![Downloads](https://img.shields.io/pypi/dm/vivintpy?style=for-the-badge)](https://pypi.org/project/vivintpy)

## Overview

**vivintpy** is an unofficial, reverse-engineered Python client for the Vivint Smart Home API. It enables programmatic access to Vivint security systems, devices, and real-time events, and is suitable for automation, research, and integration with platforms like Home Assistant.

- **Async-first**: Modern asyncio-based design for efficient I/O.
- **Device support**: Alarm panels, cameras, locks, garage doors, switches, thermostats, and sensors.
- **Real-time**: PubNub event subscription for instant device updates.
- **Extensible**: Typed device classes, event emitter pattern, and modular architecture.

---

## Architecture

```
Account (high-level API)
  └─ VivintSkyApi (HTTP/gRPC, Auth, MFA)
      └─ System(s) → AlarmPanel(s) → Device(s)
          └─ PubNub Listener (real-time events)
```

- `account.py`: User/session management, system/device discovery, PubNub connection.
- `api.py`: Handles authentication, REST/gRPC calls, token refresh, error handling.
- `devices/`: Device type wrappers (Camera, Lock, Switch, etc.)
- `stream.py`: Real-time event subscription and dispatch.

See `demo.py` for a working example.

---

## Supported Features

| Feature                    | Supported |
|----------------------------|-----------|
| OAuth2/PKCE login + MFA    | ✅        |
| Device discovery           | ✅        |
| Alarm/lock/garage/camera   | ✅        |
| Real-time updates (PubNub) | ✅        |
| Device commands            | ✅        |
| Panel firmware update      | ✅        |
| Async API                  | ✅        |
| Unit tests                 | ✅        |

---

## Quickstart

1. **Install dependencies:**
   ```sh
   pip install vivintpy
   ```
2. **Set environment variables:**
   ```sh
   export username='your@email.com'
   export password='yourpassword'
   ```
3. **Run the demo:**
   ```sh
   python demo.py
   ```

The demo will:
- Log in (with MFA if required)
- Discover all systems/devices
- Register real-time event handlers
- Print/log device events

---

## Contributing

- PRs and issues welcome! See [CONTRIBUTING.md](CONTRIBUTING.md).
- Please add tests for new device types or API calls.
- For larger changes, open a discussion first.

---

## FastAPI Wrapper

This repository includes a production-grade FastAPI wrapper that exposes `vivintpy`'s functionality via a RESTful API.

### Running the API

1.  **Set Environment Variables:**

    The API requires both Vivint credentials and Redis connection details. Create a `.env` file in the root directory or export the following variables:

    ```sh
    # Vivint Credentials
    VIVINT_USER="your@email.com"
    VIVINT_PASS="yourpassword"

    # Redis Configuration
    REDIS_HOST="localhost"
    REDIS_PORT=6379
    REDIS_DB=0
    ```

2.  **Install Dependencies and Run:**

    ```sh
    poetry install
    poetry run uvicorn vivintpy_api.main:app --reload
    ```

3.  **Access the API Docs:**

    Navigate to [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) to access the interactive FastAPI documentation.

### Authentication Flow (MFA)

The API uses a two-step process for accounts with Multi-Factor Authentication (MFA) enabled.

1.  **Initial Login:**

    Make a POST request to `/auth/login` with your `username` and `password` as form data. If MFA is required, the API will respond with a `400 Bad Request` and a JSON body containing `{"message": "MFA_REQUIRED", "mfa_session_id": "..."}`.

2.  **Verify MFA:**

    Use the `mfa_session_id` from the previous step and your MFA code to make a POST request to `/auth/verify-mfa`. The request body should be a JSON object like this:

    ```json
    {
      "mfa_session_id": "...",
      "mfa_code": "123456"
    }
    ```

    Upon successful verification, the API will return your access and refresh tokens.

### Token Refresh

Use your long-lived *API* `refresh_token` to obtain a fresh access token (and a rotated refresh token):

```sh
curl -X POST http://127.0.0.1:8000/auth/refresh-token \
     -H "Content-Type: application/json" \
     -d '{"refresh_token": "<YOUR_REFRESH_TOKEN>"}'
```

A new JSON payload with `access_token` (and optionally a new `refresh_token`) will be returned.

### Available API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST   | `/auth/login` | Initiate login, returns `MFA_REQUIRED` when applicable |
| POST   | `/auth/verify-mfa` | Complete MFA challenge & issue tokens |
| POST   | `/auth/refresh-token` | Refresh/rotate API tokens |
| GET    | `/systems/` | List systems linked to the authenticated account |
| GET    | `/systems/{system_id}` | Retrieve details for a specific system |
| GET    | `/systems/{system_id}/panel` | Current state of the system's alarm panel |
| POST   | `/systems/{system_id}/panel/arm-stay` | Arm panel in **Stay** mode |
| POST   | `/systems/{system_id}/panel/arm-away` | Arm panel in **Away** mode |
| POST   | `/systems/{system_id}/panel/disarm` | Disarm panel (requires PIN) |
| POST   | `/systems/{system_id}/panel/emergency` | Trigger panic / fire / medical alarm |
| POST   | `/systems/{system_id}/panel/reboot` | Reboot the alarm panel |
| GET    | `/systems/{system_id}/devices` | List all devices for the system |
| GET    | `/systems/{system_id}/devices/{device_id}` | Retrieve details for a specific device |
| GET    | `/systems/{system_id}/devices/{device_id}/snapshot` | Fetch latest camera snapshot (JPEG; add `?refresh=true` to request new) |
| WebSocket | `/ws/events` | Real-time event stream for all systems & devices |

### WebSocket Events

`/ws/events` provides a real-time stream of device and system events.

• **Heartbeat** – when no events have been sent for `30 s` the server sends
  a ping message to keep the connection alive:

```json
{"event_name": "ping"}
```

Clients MAY simply ignore this message or use it to measure latency.

• **Envelope format** – all other messages are JSON objects:

```json
{
  "event_name": "<vivint_event_type>",
  "system_id": 3238653088951452,
  "device_id": 42,
  "timestamp": 1718635987431,
  "data": { /* raw vivintpy event payload */ }
}
```

`event_name` is the Vivint event (e.g. `door_opened`, `lock_state_changed`).

• **Filtering** – reduce traffic by adding query parameters:

```
/ws/events?system_id=3238653088951452           # events for one system
/ws/events?device_id=27                        # events for one device (any system)
/ws/events?system_id=...&device_id=27          # device 27 on that system only
```

• **Back-pressure** – each connection has an internal queue of **1 000**
  messages. If the client falls behind and the queue fills up, the server
  closes the socket with close code **1011** (*internal error – slow consumer*).

• **Authentication** – the WebSocket handshake must include the normal
  `Authorization: Bearer <access_token>` header.


> **Note**
> All routes except the `/auth/*` series require a valid **Bearer** `access_token` in the `Authorization` header.

### Example: List Devices

```sh
curl -H "Authorization: Bearer $ACCESS_TOKEN" \
     http://127.0.0.1:8000/systems/123456/devices
```

---

## Doorbell Media Capture

The backend automatically captures a fresh **snapshot** (JPEG) – and, when
available, the associated **audio clip** – whenever your Vivint doorbell camera
reports a **motion** or **person** event.

• **Storage path** – files are written to
`MEDIA_ROOT/{system_id}/{device_id}/{timestamp}.jpg` (plus `.m4a` for audio).
  Set the `MEDIA_ROOT` environment variable to override the default `media`
  directory.

• **Real-time notification** – once the files are safely written the helper
  emits a `capture_saved` event on the originating `Camera` instance.  You can
  subscribe to this event (e.g. in the WebSocket router) to notify frontend
  clients or trigger further processing.

No additional configuration is required; the capture manager starts
automatically during FastAPI app startup as long as authentication succeeds and
an active PubNub stream is running.

---

## Fork & Credits

- **Original Author:** Nathan Spencer (2021–2023)
- **Forked from:** [ovirs/pyvivint](https://github.com/ovirs/pyvivint) and inspired by [Riebart/vivint.py](https://github.com/Riebart/vivint.py)
- **Current Maintainer:** Christian Mandefro, 2025–present

This fork is maintained independently and may diverge from upstream.

---

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

You are free to use, modify, and distribute this software, provided you retain the original copyright notice.

---

*vivintpy is not affiliated with or endorsed by Vivint Smart Home, Inc. Use at your own risk.*
