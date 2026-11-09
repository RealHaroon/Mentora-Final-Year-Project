from slowapi import Limiter
from slowapi.util import get_remote_address

# Phase 8 §8 security pass — rate limiting on auth endpoints, specifically
# to blunt brute-force login attempts.
limiter = Limiter(key_func=get_remote_address)
