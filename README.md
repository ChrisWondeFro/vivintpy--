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
- `pubnub.py`: Real-time event subscription and dispatch.

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
| Unit tests                 | 🚧        |

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

---

## Fork & Credits

- **Original Author:** Nathan Spencer (2021–2023)
- **Forked from:** [ovirs/pyvivint](https://github.com/ovirs/pyvivint) and inspired by [Riebart/vivint.py](https://github.com/Riebart/vivint.py)
- **Current Maintainer:** [Your Name], 2025–present

This fork is maintained independently and may diverge from upstream.

---

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

You are free to use, modify, and distribute this software, provided you retain the original copyright notice.

---

*vivintpy is not affiliated with or endorsed by Vivint Smart Home, Inc. Use at your own risk.*
