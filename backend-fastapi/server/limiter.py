# server/limiter.py
from slowapi import Limiter
from slowapi.util import get_remote_address

# Tworzymy instancję limitera (tylko raz!)
limiter = Limiter(key_func=get_remote_address)