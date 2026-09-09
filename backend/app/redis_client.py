import os

import redis
from dotenv import load_dotenv

load_dotenv()

_redis_host = os.getenv("REDIS_HOST")
_redis_port = os.getenv("REDIS_PORT")
_redis_password = os.getenv("REDIS_PASSWORD")

if _redis_host and _redis_port:
    r = redis.Redis(
        host=_redis_host,
        port=int(_redis_port),
        password=_redis_password or None,
        decode_responses=True,
    )
else:
    r = None
