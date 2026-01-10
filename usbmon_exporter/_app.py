import contextlib

import prometheus_client as prometheus

from ._monitor import UsbMonitor
from ._uevent import UEvent
from ._usbmon import UsbMon


def main():
    with (
        UsbMon("/dev/usbmon0") as usbmon,
        UEvent() as uevent,
        UsbMonitor(usbmon, uevent) as monitor,
    ):
        prometheus.start_http_server(8000)
        with contextlib.suppress(KeyboardInterrupt):
            monitor.run_forever()
