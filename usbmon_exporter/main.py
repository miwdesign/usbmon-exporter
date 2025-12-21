#!/usr/bin/env python3

import asyncio
import contextlib

from ._monitor import UsbMonitor
from ._uevent import UEvent
from ._usbmon import UsbMon


async def main():
    with (
        UsbMon("/dev/usbmon0") as usbmon,
        UEvent() as uevent,
        UsbMonitor(usbmon, uevent),
    ):
        await asyncio.Event().wait()


if __name__ == "__main__":
    with contextlib.suppress(KeyboardInterrupt):
        asyncio.run(main())

    import prometheus_client as promptheus

    promptheus.write_to_textfile("usbmon.prom", promptheus.REGISTRY)
