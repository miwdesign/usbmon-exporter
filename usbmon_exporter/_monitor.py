import asyncio
import contextlib

from . import _sysfs as sysfs


class UsbMonitor:
    def __init__(self, usbmon, uevent):
        self._usbmon = usbmon
        self._uevent = uevent
        self._usb_id_map = {}

    def __enter__(self):
        with contextlib.ExitStack() as stack:
            loop = asyncio.get_running_loop()

            loop.add_reader(self._uevent.fileno, self._on_event)
            stack.callback(loop.remove_reader, self._uevent.fileno)

            loop.add_reader(self._usbmon.fileno, self._on_event)
            stack.callback(loop.remove_reader, self._usbmon.fileno)

            self._build_usb_id_map()

            self._stack = stack.pop_all()
            self._stack.__enter__()
            return self

        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self._stack.__exit__(exc_type, exc_value, traceback)

    def _build_usb_id_map(self):
        # initialize the USB ID map from sysfs
        self._usb_id_map = sysfs.build_usb_id_map()

        # update the map with any events that occurred since we read sysfs
        for action, key, usb_id in self._usb_events():
            if action == "add":
                self._usb_id_map[key] = usb_id
            elif action == "remove" and key in self._usb_id_map:
                del self._usb_id_map[key]

        # flush pending packets, because they may not have corresponding events
        for _ in self._usbmon.receive_iter():
            pass

    def _on_event(self):
        packets = []
        events = []

        while True:
            new_packets = list(self._usbmon.receive_iter())
            packets.extend(new_packets)

            new_events = list(self._usb_events())
            events.extend(new_events)

            # make sure both sources are drained, so we can correlate events
            # properly
            if not new_packets and not new_events:
                break

        to_remove = set()
        for action, key, usb_id in events:
            if action == "add":
                self._usb_id_map[key] = usb_id
                to_remove.discard(key)
            else:
                to_remove.add(key)

        for packet in packets:
            if packet.devnum == 0:
                # enumeration packet, no devnum assigned yet
                usb_id = f"{packet.busnum}-0"
            else:
                key = (packet.busnum, packet.devnum)
                usb_id = self._usb_id_map.get(key)

            if usb_id is not None:
                print(f"USB ID: {usb_id}, Packet: {packet}")
            else:
                print("Warning: USB ID not found for packet:", packet)

        for key in to_remove:
            if key in self._usb_id_map:
                del self._usb_id_map[key]

    def _usb_events(self):
        for event in self._uevent.receive_iter():
            if (
                event.get("SUBSYSTEM") == "usb"
                and event.get("DEVTYPE") == "usb_device"
                and event["ACTION"] in ("add", "remove")
            ):
                usb_id = event["DEVPATH"].rsplit("/", 1)[-1]
                key = (int(event["BUSNUM"]), int(event["DEVNUM"]))
                yield event["ACTION"], key, usb_id
