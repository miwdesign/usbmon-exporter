import prometheus_client as prometheus

prometheus.disable_created_metrics()

XFER_TYPES = {
    0: "Isochronous",
    1: "Interrupt",
    2: "Control",
    3: "Bulk",
}
DIRECTIONS = ["in", "out"]

URBS_BY_USB_ID = prometheus.Counter(
    "usbmon_urbs_by_usb_id_total",
    "Total number of USB URBs by USB ID",
    ["usb_id"],
)
URBS_BY_BUS = prometheus.Counter(
    "usbmon_urbs_by_bus_total",
    "Total number of USB URBs by bus number",
    ["busnum", "xfer_type", "direction"],
)
URB_ERRORS = prometheus.Counter(
    "usbmon_urb_errors_total",
    "Total number of USB URB errors",
    ["busnum", "xfer_type"],
)
URB_SUBMIT_ERRORS = prometheus.Counter(
    "usbmon_urb_submit_errors_total",
    "Total number of USB URB submission errors",
    ["busnum", "xfer_type"],
)
DEVICES = prometheus.Gauge(
    "usbmon_devices",
    "Current number of USB devices",
    ["busnum"],
)
PENDING = prometheus.Gauge(
    "usbmon_pending_usb_id_assignment",
    "Current number of USB URBs pending USB ID assignment",
)
URB_SIZE_BYTES = prometheus.Histogram(
    "usbmon_urb_size_bytes",
    "Size of USB URBs in bytes",
    ["busnum", "xfer_type"],
    buckets=[2**x for x in range(3, 17)],  # 8 to 65536
)
