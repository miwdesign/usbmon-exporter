import contextlib
import ctypes
import dataclasses
import fcntl
import mmap
import os

MON_IOCQ_RING_SIZE = 0x00009205
MON_IOCX_MFETCH = 0xC0109207
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


class UsbMon:
    def __init__(self, usbmon_path):
        self._usbmon_path = usbmon_path

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

        xfer_types = {
            0: "Isochronous",
            1: "Interrupt",
            2: "Control",
            3: "Bulk",
        }

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

                if hdr.type != b"C":
                    # only process callback events
                    continue

                is_in = hdr.epnum & 0x80
                direction = "in" if is_in else "out"

                xfer_type = xfer_types.get(hdr.xfer_type)
                if xfer_type is None:
                    continue

                yield UsbPacket(
                    xfer_type=xfer_type,
                    direction=direction,
                    busnum=hdr.busnum,
                    devnum=hdr.devnum,
                    length=hdr.length,
                    status=hdr.status,
                )


@dataclasses.dataclass
class UsbPacket:
    xfer_type: str
    direction: str
    busnum: int
    devnum: int
    length: int
    status: int
