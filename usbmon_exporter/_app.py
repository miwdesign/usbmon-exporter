import contextlib

import prometheus_client as promptheus

from ._monitor import UsbMonitor
from ._uevent import UEvent
from ._usbmon import UsbMon

_prometheus_app = promptheus.make_asgi_app()


async def asgi_app(scope, receive, send):
    if scope["type"] == "lifespan":
        await _handle_lifespan(receive, send)
    elif scope["type"] == "http":
        if scope["path"] == "/metrics":
            await _prometheus_app(scope, receive, send)
        else:
            body = b"Page not found"
            await send(
                {
                    "type": "http.response.start",
                    "status": 404,
                    "headers": [
                        (b"content-type", b"text/plain"),
                        (b"content-length", str(len(body)).encode()),
                    ],
                }
            )
            await send(
                {
                    "type": "http.response.body",
                    "body": body,
                }
            )
    else:
        raise NotImplementedError(f"Unknown scope type {scope['type']}")


async def _handle_lifespan(receive, send):
    stack = contextlib.ExitStack()
    while True:
        message = await receive()
        if message["type"] == "lifespan.startup":
            try:
                _startup(stack)
            except Exception as err:
                await send({"type": "lifespan.startup.failed", "message": str(err)})
            else:
                await send({"type": "lifespan.startup.complete"})
        elif message["type"] == "lifespan.shutdown":
            try:
                stack.close()
            except Exception as err:
                await send({"type": "lifespan.shutdown.failed", "message": str(err)})
            else:
                await send({"type": "lifespan.shutdown.complete"})
            return


def _startup(stack):
    usbmon = stack.enter_context(UsbMon("/dev/usbmon0"))
    uevent = stack.enter_context(UEvent())
    stack.enter_context(UsbMonitor(usbmon, uevent))
