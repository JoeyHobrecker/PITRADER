import json, logging, os, signal
from contextlib import contextmanager
from typing import Dict, Generator

import redis

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

TOPIC_NEWS_RAW = "news_raw"
TOPIC_TRADE_SIGNALS = "trade_signals"
TOPIC_ORDERS = "orders"
TOPIC_FILLS = "fills"
TOPIC_PLAYBOOK = "playbook"

_redis_client = None

def get_redis_client() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.Redis(
            host=os.environ.get("REDIS_HOST", "localhost"),
            port=6379,
            decode_responses=True,
        )
    return _redis_client

def publish(topic: str, data: dict):
    try:
        get_redis_client().xadd(topic, {"data": json.dumps(data)})
    except Exception as e:
        logging.error(f"publish failed: {e}")

def subscribe(topic: str, group: str, consumer: str = "default", block_ms: int = 5000) -> Generator[Dict, None, None]:
    r = get_redis_client()
    try:
        r.xgroup_create(topic, group, id="0", mkstream=True)
    except redis.exceptions.ResponseError:
        pass
    while True:
        resp = r.xreadgroup(group, consumer, {topic: ">"}, count=1, block=block_ms)
        if resp:
            _, msgs = resp[0]
            msg_id, dat = msgs[0]
            payload = json.loads(dat["data"])
            yield payload
            r.xack(topic, group, msg_id)

@contextmanager
def graceful_shutdown():
    shutting = {"flag": False}
    def handler(*_):
        shutting["flag"] = True
    old = signal.signal(signal.SIGTERM, handler)
    try:
        yield lambda: shutting["flag"]
    finally:
        signal.signal(signal.SIGTERM, old)
