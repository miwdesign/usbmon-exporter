import argparse
import contextlib

import prometheus_client as prometheus

from ._exporter import Exporter
from ._uevent import UEvent
from ._usbmon import UsbMon


def main():
    parser = argparse.ArgumentParser(
        description="usbmon Prometheus Exporter",
    )
    parser.add_argument(
        "-l",
        "--listen-address",
        default="0.0.0.0:10040",
        help="Address to listen on for metrics exposition",
    )
    parser.add_argument(
        "-d", "--device", default="/dev/usbmon0", help="Path to the usbmon device"
    )
    args = parser.parse_args()

    host, port = args.listen_address.split(":")

    with (
        UsbMon(args.device) as usbmon,
        UEvent() as uevent,
        Exporter(usbmon, uevent) as exporter,
    ):
        prometheus.start_http_server(int(port), host)
        with contextlib.suppress(KeyboardInterrupt):
            exporter.run_forever()
