import secrets
import string

ALPHABET = string.ascii_uppercase + string.digits


def control_id() -> str:
    """20 uppercase letters and digits. B columns 60-80, and the MQ correlation id."""
    return "".join(secrets.choice(ALPHABET) for _ in range(20))


def kn_number() -> str:
    """Up to 21 characters in A columns 60-80. ACE echoes it unchanged."""
    left = "".join(secrets.choice(ALPHABET) for _ in range(4))
    right = "".join(secrets.choice(string.digits) for _ in range(2))
    return f"KN-{left}-{right}:EE"
