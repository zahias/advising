from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address

# Single shared limiter instance — attached to app.state in main.py.
limiter = Limiter(key_func=get_remote_address)
