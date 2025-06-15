import asyncio
import os

import logging
from vivintpy.account import Account
from vivintpy.devices import VivintDevice
from vivintpy.devices.camera import MOTION_DETECTED, Camera
from vivintpy.exceptions import VivintSkyApiMfaRequiredError
import config

logging.getLogger('pubnub').setLevel(logging.ERROR)

USERNAME = config.USERNAME
PASSWORD = config.PASSWORD
REFRESH_TOKEN_FILE = "refresh_token.txt"


async def main():
    logging.getLogger().setLevel(logging.DEBUG)
    logging.debug("Demo started")

    def camera_motion_callback(device: VivintDevice) -> None:
        logging.debug("Motion detected from camera: %s", device)

    # Load existing refresh token if available
    refresh_token = None
    if os.path.exists(REFRESH_TOKEN_FILE):
        with open(REFRESH_TOKEN_FILE, "r") as f:
            refresh_token = f.read().strip()
    # Initialize account with saved refresh token
    account = Account(username=USERNAME, password=PASSWORD, refresh_token=refresh_token)
    try:
        # Connect (handle MFA if required)
        try:
            await account.connect(load_devices=True, subscribe_for_realtime_updates=True)
        except VivintSkyApiMfaRequiredError:
            code = input("Enter MFA Code: ")
            await account.verify_mfa(code)
            logging.debug("MFA verified")
        # Persist refresh token for future runs
        new_rt = account.refresh_token
        if new_rt:
            with open(REFRESH_TOKEN_FILE, "w") as f:
                f.write(new_rt)

        # Discovered systems & devices
        logging.debug("Discovered systems & devices:")
        for system in account.systems:
            logging.debug(f"\tSystem {system.id}")
            for alarm_panel in system.alarm_panels:
                logging.debug(
                    f"\t\tAlarm panel {alarm_panel.id}:{alarm_panel.partition_id}"
                )
                for device in alarm_panel.devices:
                    logging.debug(f"\t\t\tDevice: {device}")
                    if isinstance(device, Camera):
                        device.on(
                            MOTION_DETECTED,
                            lambda event: camera_motion_callback(event["device"]),
                        )

        # Keep alive and refresh periodically
        while True:
            await asyncio.sleep(300)
            await account.refresh()
    finally:
        await account.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
