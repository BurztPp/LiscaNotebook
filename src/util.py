import base64
import threading
import time
import traceback


def make_uid(obj):
    """Generate a unique identifier of `obj`.

    The unique identifier is returned as string and is technically unique
    during the lifetime of the process.

    Implementation detail: The unique identifier is a base64-encoded string
    (trailing '=' are stripped) of memory address and time.
    """
    b = bytearray(16)
    b[:8] = id(obj).to_bytes(8, 'little')
    b[-8:] = time.perf_counter_ns().to_bytes(8, 'little')
    return base64.b64encode(b).rstrip(b'=').decode()


def threaded(fun):
    """Decorator function for running in a new thread

    `fun` is the function to be run in a new thread.
    The thread is started and the thread object is returned.
    """
    def threaded_fun(*args, **kwargs):
        t = threading.Thread(target=fun, args=args, kwargs=kwargs)
        t.start()
        return t
    return threaded_fun


@threaded
def listen_for_events(qu):
    """Process events from event queue `qu`.

    The function is called in its own thread.
    Write `None` into `qu` to quit the thread.
    """
    while True:
        try:
            evt = qu.get()
            if evt is None:
                return
            evt()
        except Exception:
            print(traceback.format_exc())
            continue

