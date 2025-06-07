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
