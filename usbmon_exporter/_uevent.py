import contextlib
import os
import socket

NETLINK_KOBJECT_UEVENT = 15
KERN_RCVBUF = 128 * 1024 * 1024
USER_RCVBUF = 16 * 1024
SO_RCVBUFFORCE = 33


class UEvent:
    def __enter__(self):
        with contextlib.ExitStack() as stack:
            self._sock = stack.enter_context(
                socket.socket(
                    socket.AF_NETLINK, socket.SOCK_DGRAM, NETLINK_KOBJECT_UEVENT
                )
            )
            os.set_blocking(self._sock.fileno(), False)

            self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, KERN_RCVBUF)
            self._sock.setsockopt(socket.SOL_SOCKET, SO_RCVBUFFORCE, KERN_RCVBUF)

            groups = 1
            self._sock.bind((os.getpid(), groups))

            self._stack = stack.pop_all()
            self._stack.__enter__()
            return self

    def __exit__(self, exc_type, exc_value, traceback):
        self._stack.__exit__(exc_type, exc_value, traceback)

    @property
    def fileno(self):
        return self._sock.fileno()

    def receive_iter(self):
        while True:
            try:
                data = self._sock.recv(USER_RCVBUF)
            except BlockingIOError:
                break

            yield self._parse_uevent(data)

    def _parse_uevent(self, data):
        fields = data.rstrip(b"\x00").split(b"\x00")

        event = {}

        # First field: ACTION@DEVPATH
        header = fields[0].decode(errors="replace")
        if "@" in header:
            action, devpath = header.split("@", 1)
            event["ACTION"] = action
            event["DEVPATH"] = devpath

        # Remaining fields: KEY=value
        for field in fields[1:]:
            if b"=" in field:
                k, v = field.split(b"=", 1)
                event[k.decode()] = v.decode(errors="replace")

        return event
