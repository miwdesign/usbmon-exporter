#!/usr/bin/env python3

import asyncio
import contextlib

from . import _uevent as uevent
from . import _usbmon as usbmon


async def main():
    with (
        usbmon.UsbMon("/dev/usbmon0"),
        uevent.UEvent() as uev,
    ):
        loop = asyncio.get_running_loop()

        def uevent_callback():
            for event in uev.receive_iter():
                if (
                    event["ACTION"] in ("add", "remove")
                    and event.get("DEVTYPE") == "usb_device"
                ):
                    print(
                        f'{event["ACTION"]} Devnum: {event["DEVNUM"]}, Busnum: {event["BUSNUM"]} = {event["DEVPATH"]}'
                    )

        loop.add_reader(uev.sock.fileno(), uevent_callback)

        await asyncio.Event().wait()


if __name__ == "__main__":
    with contextlib.suppress(KeyboardInterrupt):
        asyncio.run(main())
