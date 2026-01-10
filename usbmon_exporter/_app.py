import contextlib

import prometheus_client as prometheus

from ._exporter import Exporter
from ._uevent import UEvent
from ._usbmon import UsbMon


def main():
    with (
        UsbMon("/dev/usbmon0") as usbmon,
        UEvent() as uevent,
        Exporter(usbmon, uevent) as exporter,
    ):
        prometheus.start_http_server(8000)
        with contextlib.suppress(KeyboardInterrupt):
            exporter.run_forever()
