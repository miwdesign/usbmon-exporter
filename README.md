# usbmon Exporter

`usbmon_exporter` is a Prometheus exporter, that captures USB device metrics
using the Linux Kernel usbmon interface.

## Installation

Install using `pipx`:

```console
$ sudo PIPX_HOME=/opt/pipx PIPX_BIN_DIR=/usr/local/bin pipx install usbmon-exporter
```

## Usage

Make sure the `usbmon` Kernel module is loaded:

```console
$ sudo modprobe usbmon
```

Run `usbmon_exporter` as root:

```console
$ sudo usbmon_exporter
```

Metrics should now be readable at http://localhost:10040/metrics.

Options:
- `-l`, `--listen-address`: Address to listen on for metrics exposition.
  Default: `0.0.0.0:10040` (listen on all interfaces on port 10040).
- `-d`, `--device`: Path to the usbmon device. Default: `/dev/usbmon0`.

## Exposed metrics

Here is a summary of all exposed metrics.

### Counter `usbmon_urbs_by_usb_id_total{usb_id}`

Total number of URBs by USB ID.

### Counter `usbmon_urbs_by_bus_total{busnum, direction, xfer_type}`

Total number of URBs by bus number.

### Counter `usbmon_urb_errors_total{busnum, xfer_type}`

Total number of URB errors.

### Counter `usbmon_urb_submit_errors_total{busnum, xfer_type}`

Total number of URB submission errors.

### Gauge `usbmon_devices{busnum}`

Current number of USB devices.

### Histogram `usbmon_urb_size_bytes{busnum, xfer_type}`

Size of URBs in bytes.

### Gauge `usbmon_stats_queued`

Number of URBs currently queued in the usbmon buffer.

### Counter `usbmon_stats_dropped_total`

Total number of URBs dropped due to usbmon buffer overflow.

### Gauge `usbmon_pending_usb_id_assignment`

Current number of URBs pending USB ID assignment. This metric is mostly for
debugging `usbmon_exporter`. Counts the number of URBs, that are recorded during
enumeration, that cannot be assigned to a USB ID, before the Kernel emits a
uevent for the new device. The value should be `0` most of the time.

## Labels

### `usb_id`

Identifies the host USB port. Either `<busnum>-<devpath>` or `bus<busnum>`. For
traffic before enumeration `devpath` is set to `0`.

Example: `1-4.2`.

### `busnum`

Bus number.

### `direction`

URB direction, either `in` or `out`.

### `xfer_type`

URB type, one of `Isochronous`, `Interrupt`, `Control` or `Bulk`.
