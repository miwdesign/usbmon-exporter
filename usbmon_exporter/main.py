#!/usr/bin/env python3

import asyncio
import contextlib

from . import _usbmon as usbmon


async def main():
    with usbmon.UsbMon("/dev/usbmon0"):
        await asyncio.Event().wait()


if __name__ == "__main__":
    with contextlib.suppress(KeyboardInterrupt):
        asyncio.run(main())
