import base64
import time

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
