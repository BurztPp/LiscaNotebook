import base64
import queue
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
    return base64.b64encode(b, altchars=b'+-').rstrip(b'=').decode()


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


def poll_event_queue_tk(obj, qu, interval=10, evt_map=None):
    """Poll event queue in tkinter mainloop.

    The queue is polled all `interval` milliseconds.
    Errors during event processing are ignored.
    If `None` is read from `queue`, the polling stops.

    Arguments:
        obj -- calling tkinter widget
        qu -- queue to be polled
        interval -- poll interval (in milliseconds)
        evt_map -- dict, keys are event commands (str), values are functions
    """
    if evt_map is None:
        evt_map = {}
    while True:
        try:
            evt = qu.get_nowait()
            if evt is None:
                return
            elif isinstance(evt, str):
                evt_map[evt]()
            elif evt.fun is None:
                evt(fun=evt_map[evt.cmd])
            else:
                evt()
        except queue.Empty:
            break
        except Exception:
            print(traceback.format_exc())
    obj.after(interval, poll_event_queue_tk, obj, qu, interval, evt_map)
