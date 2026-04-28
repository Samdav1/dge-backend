import time
import secrets
import string


def generate_tx_ref(prefix: str = "TX") -> str:
    """
    Generates a unique, URL-safe transaction reference.
    Format: PREFIX-TIMESTAMP-RANDOM
    Example: TX-1734945421500-A1B2C3
    """
    timestamp = int(time.time() * 1000)
    random_part = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(6))
    return f"{prefix}-{timestamp}-{random_part}"