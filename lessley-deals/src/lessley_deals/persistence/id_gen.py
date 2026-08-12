import secrets
import time


def generate_id() -> str:
    """Generate a sortable, collision-resistant ID.

    Format: {timestamp_ms_hex}_{random_hex}
    - Sortable by creation time (hex timestamp sorts lexicographically)
    - 8 bytes of randomness for collision resistance
    """
    ts = int(time.time() * 1000)
    rand = secrets.token_hex(8)
    return f"{ts:012x}_{rand}"
