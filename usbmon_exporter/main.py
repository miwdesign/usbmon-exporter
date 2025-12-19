#!/usr/bin/env python3

import ctypes
import errno
import fcntl
import mmap

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


def main():
    usbmon_device = "/dev/usbmon0"

    xfer_types = {
        0: "Isochronous",
        1: "Interrupt",
        2: "Control",
        3: "Bulk",
    }

    with open(usbmon_device, "rb") as f:
        # Get ring buffer size
        ring_size = fcntl.ioctl(f.fileno(), MON_IOCQ_RING_SIZE)
        if ring_size < 0:
            raise OSError("Failed to get ring buffer size")

        ring_buffer = mmap.mmap(f.fileno(), ring_size, prot=mmap.PROT_READ)

        offvec = (ctypes.c_uint32 * OFFVEC_SIZE)()
        nflush = 0

        while True:
            mfetch = MFetchArg(
                offvec=ctypes.cast(offvec, ctypes.POINTER(ctypes.c_uint32)),
                nfetch=OFFVEC_SIZE,
                nflush=nflush,
            )

            err = fcntl.ioctl(f.fileno(), MON_IOCX_MFETCH, mfetch)
            if err < 0:
                raise OSError("MON_IOCX_MFETCH ioctl failed")

            nflush = mfetch.nfetch

            for i in range(nflush):
                hdr = UsbmonPacket.from_buffer_copy(ring_buffer, offvec[i])

                if hdr.type != b"C":
                    # only process callback events
                    continue

                is_in = hdr.epnum & 0x80
                direction = "IN" if is_in else "OUT"
                epnum = hdr.epnum & 0x7F

                print(
                    f"ID: 0x{hdr.id:016x}, Type: {hdr.type.decode()}, Xfer Type: {xfer_types.get(hdr.xfer_type, hdr.xfer_type)}, Direction: {direction}, Epnum: {epnum}, Devnum: {hdr.devnum}, Busnum: {hdr.busnum}, Length: {hdr.length}, Flags: 0x{ord(hdr.flag_setup):02x}{ord(hdr.flag_data):02x}, Status: {errno.errorcode.get(-hdr.status, hdr.status)}"
                )


if __name__ == "__main__":
    main()
