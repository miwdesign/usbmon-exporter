import contextlib
import ctypes
import dataclasses
import fcntl
import mmap
import os

from . import _metrics as metrics

MON_IOCQ_RING_SIZE = 0x00009205
MON_IOCX_MFETCH = 0xC0109207
MON_IOCG_STATS = 0x80089203
OFFVEC_SIZE = 32


class MFetchArg(ctypes.Structure):
    _fields_ = (
        ("offvec", ctypes.POINTER(ctypes.c_uint32)),
        ("nfetch", ctypes.c_uint32),
        ("nflush", ctypes.c_uint32),
    )


class IsoRec(ctypes.Structure):
    _fields_ = (
        ("error_count", ctypes.c_int32),
        ("num_desc", ctypes.c_int32),
    )


class _S(ctypes.Union):
    _fields_ = (
        ("setup", ctypes.c_uint8 * 8),
        ("iso", IsoRec),
    )


class UsbmonPacket(ctypes.Structure):
    _anonymous_ = ("s",)
    _fields_ = (
        ("id", ctypes.c_uint64),
        ("type", ctypes.c_char),
        ("xfer_type", ctypes.c_uint8),
        ("epnum", ctypes.c_uint8),
        ("devnum", ctypes.c_uint8),
        ("busnum", ctypes.c_uint16),
        ("flag_setup", ctypes.c_char),
        ("flag_data", ctypes.c_char),
        ("ts_sec", ctypes.c_int64),
        ("ts_usec", ctypes.c_int32),
        ("status", ctypes.c_int32),
        ("length", ctypes.c_uint32),
        ("len_cap", ctypes.c_uint32),
        ("s", _S),
        ("interval", ctypes.c_int32),
        ("start_frame", ctypes.c_int32),
        ("xfer_flags", ctypes.c_uint32),
        ("ndesc", ctypes.c_uint32),
    )


class UsbmonStats(ctypes.Structure):
    _fields_ = (
        ("queued", ctypes.c_uint32),
        ("dropped", ctypes.c_uint32),
    )


class UsbMon:
    def __init__(self, usbmon_path):
        self._usbmon_path = usbmon_path
        self._dropped_total = 0

    def __enter__(self):
        with contextlib.ExitStack() as stack:
            self._usbmon_fd = stack.enter_context(
                open(self._usbmon_path, "rb")
            ).fileno()
            os.set_blocking(self._usbmon_fd, False)

            ring_size = fcntl.ioctl(self._usbmon_fd, MON_IOCQ_RING_SIZE)
            self._ring_buffer = stack.enter_context(
                mmap.mmap(self._usbmon_fd, ring_size, prot=mmap.PROT_READ)
            )

            self._stack = stack.pop_all()
            self._stack.__enter__()
            return self

    def __exit__(self, exc_type, exc_value, traceback):
        self._stack.__exit__(exc_type, exc_value, traceback)

    @property
    def fileno(self):
        return self._usbmon_fd

    def receive_iter(self):
        offvec = (ctypes.c_uint32 * OFFVEC_SIZE)()
        nflush = 0

        while True:
            mfetch = MFetchArg(
                offvec=ctypes.cast(offvec, ctypes.POINTER(ctypes.c_uint32)),
                nfetch=OFFVEC_SIZE,
                nflush=nflush,
            )

            try:
                fcntl.ioctl(self._usbmon_fd, MON_IOCX_MFETCH, mfetch)
            except BlockingIOError:
                break

            nflush = mfetch.nfetch

            for i in range(nflush):
                hdr = UsbmonPacket.from_buffer_copy(self._ring_buffer, offvec[i])

                if hdr.type not in (b"C", b"E"):
                    # only process callback and error events
                    continue

                is_submit_error = hdr.type == b"E"

                is_in = hdr.epnum & 0x80
                direction = "in" if is_in else "out"

                xfer_type = metrics.XFER_TYPES.get(hdr.xfer_type)
                if xfer_type is None:
                    continue

                iso_error_count = hdr.s.iso.error_count if xfer_type == 0 else 0

                yield UsbPacket(
                    is_submit_error=is_submit_error,
                    xfer_type=xfer_type,
                    direction=direction,
                    busnum=hdr.busnum,
                    devnum=hdr.devnum,
                    length=hdr.length,
                    status=hdr.status,
                    iso_error_count=iso_error_count,
                )

    def get_stats(self):
        stats = UsbmonStats()
        fcntl.ioctl(self._usbmon_fd, MON_IOCG_STATS, stats)
        self._dropped_total += stats.dropped
        return {"queued": stats.queued, "dropped": self._dropped_total}


@dataclasses.dataclass
class UsbPacket:
    is_submit_error: bool
    xfer_type: str
    direction: str
    busnum: int
    devnum: int
    length: int
    status: int
    iso_error_count: int
