import collections
import select

from prometheus_client import core as prometheus_core
from prometheus_client import registry as prometheus_registry

from . import _metrics as metrics
from . import _sysfs as sysfs


class Exporter:
    def __init__(self, usbmon, uevent):
        self._usbmon = usbmon
        self._uevent = uevent
        self._usb_id_map = collections.defaultdict(dict)
        self._pending_packets = collections.defaultdict(list)

    def __enter__(self):
        self._poll = select.poll()
        self._poll.register(self._usbmon.fileno, select.POLLIN)
        self._poll.register(self._uevent.fileno, select.POLLIN)

        self._build_usb_id_map()
        self._init_metrics()

        return self

    def __exit__(self, exc_type, exc_value, traceback):
        pass

    def _build_usb_id_map(self):
        # initialize the USB ID map from sysfs
        self._usb_id_map = sysfs.build_usb_id_map()

        # update the map with any events that occurred since we read sysfs
        for action, busnum, devnum, usb_id in self._usb_events():
            if action == "add":
                self._usb_id_map[busnum][devnum] = usb_id
            elif action == "remove" and devnum in self._usb_id_map[busnum]:
                del self._usb_id_map[busnum][devnum]

        # flush pending packets, because they may not have corresponding events
        for _ in self._usbmon.receive_iter():
            pass

    def _init_metrics(self):
        for busnum, dev_map in self._usb_id_map.items():
            for _, usb_id in dev_map.items():
                metrics.URBS_BY_USB_ID.labels(usb_id)

            for xfer_type in metrics.XFER_TYPES.values():
                for direction in metrics.DIRECTIONS:
                    metrics.URBS_BY_BUS.labels(busnum, xfer_type, direction)

                metrics.URB_ERRORS.labels(busnum, xfer_type)
                metrics.URB_SUBMIT_ERRORS.labels(busnum, xfer_type)
                metrics.URB_SIZE_BYTES.labels(busnum, xfer_type)

            metrics.DEVICES.labels(busnum).set_function(
                lambda b=busnum: len(self._usb_id_map[b])
            )

            metrics.PENDING.set_function(
                lambda: sum(
                    len(packets) for _, packets in self._pending_packets.items()
                )
            )

        prometheus_core.REGISTRY.register(_Collector(self._usbmon))

    def run_forever(self):
        while True:
            self._poll.poll()
            self._on_event()

    def _on_event(self):
        packets, events = self._drain_sources()
        to_remove = self._process_events(events)
        self._process_packets(packets)
        self._cleanup_removed_devices(to_remove)

    def _drain_sources(self):
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
                return packets, events

    def _process_events(self, events):
        to_remove = set()
        for action, busnum, devnum, usb_id in events:
            key = (busnum, devnum)
            if action == "add":
                self._usb_id_map[busnum][devnum] = usb_id
                to_remove.discard(key)

                pending = self._pending_packets.pop(key, [])
                for packet in pending:
                    self._observe_packet(packet, usb_id)
            else:
                to_remove.add(key)

        return to_remove

    def _process_packets(self, packets):
        for packet in packets:
            if packet.devnum == 0:
                # enumeration packet, no devnum assigned yet
                usb_id = f"{packet.busnum}-0"
            else:
                usb_id = self._usb_id_map[packet.busnum].get(packet.devnum)

            if usb_id is not None:
                self._observe_packet(packet, usb_id)
            else:
                # initial traffic occurs before uevent is received, queue it
                key = (packet.busnum, packet.devnum)
                self._pending_packets[key].append(packet)

    def _cleanup_removed_devices(self, to_remove):
        for busnum, devnum in to_remove:
            if devnum in self._usb_id_map[busnum]:
                del self._usb_id_map[busnum][devnum]

    def _usb_events(self):
        for event in self._uevent.receive_iter():
            if (
                event.get("SUBSYSTEM") == "usb"
                and event.get("DEVTYPE") == "usb_device"
                and event["ACTION"] in ("add", "remove")
            ):
                usb_id = event["DEVPATH"].rsplit("/", 1)[-1]
                yield (
                    event["ACTION"],
                    int(event["BUSNUM"]),
                    int(event["DEVNUM"]),
                    usb_id,
                )

    def _observe_packet(self, packet, usb_id):
        if packet.is_submit_error:
            metrics.URB_SUBMIT_ERRORS.labels(
                packet.busnum,
                packet.xfer_type,
            ).inc()
        elif packet.status == 0 and packet.iso_error_count == 0:
            metrics.URBS_BY_USB_ID.labels(usb_id).inc()
            metrics.URBS_BY_BUS.labels(
                packet.busnum,
                packet.xfer_type,
                packet.direction,
            ).inc()
            metrics.URB_SIZE_BYTES.labels(
                packet.busnum,
                packet.xfer_type,
            ).observe(packet.length)
        else:
            metrics.URB_ERRORS.labels(
                packet.busnum,
                packet.xfer_type,
            ).inc()


class _Collector(prometheus_registry.Collector):
    def __init__(self, usbmon):
        self._usbmon = usbmon

    def collect(self):
        stats = self._usbmon.get_stats()
        yield prometheus_core.GaugeMetricFamily(
            "usbmon_stats_queued",
            "Number of USB URBs currently queued in the usbmon buffer",
            value=stats["queued"],
        )
        yield prometheus_core.CounterMetricFamily(
            "usbmon_stats_dropped_total",
            "Total number of USB URBs dropped due to usbmon buffer overflow",
            value=stats["dropped"],
        )
