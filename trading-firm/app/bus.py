import json
import logging
import os
import signal
from contextlib import contextmanager
from typing import Dict, Generator, List, Optional

import redis

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# --- Message Bus Topics ---
TOPIC_NEWS_RAW = "news_raw"
TOPIC_TRADE_SIGNALS = "trade_signals"
TOPIC_ORDERS = "orders"
TOPIC_FILLS = "fills"
TOPIC_PLAYBOOK = "playbook"  # For OKRs, tasks, catalyst events, HALT signals

_redis_client = None


def get_redis_client() -> redis.Redis:
    """Returns a singleton Redis client instance."""
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.Redis(
            host=os.environ.get("REDIS_HOST", "localhost"),
            port=6379,
            decode_responses=True,
        )
    return _redis_client


def publish(topic: str, data: dict):
    """Publishes a message to a Redis Stream topic."""
    try:
        r = get_redis_client()
        # The '*' tells Redis to generate an ID automatically.
        message_id = r.xadd(topic, data)
        logging.debug(f"Published to {topic} (ID: {message_id}): {data}")
    except Exception as e:
        logging.error(f"Failed to publish to {topic}: {e}")


def subscribe(
    topic: str, group: str, consumer: str = "consumer-1", block_ms: int = 5000
) -> Generator[Dict, None, None]:
    """
    A generator that yields messages from a Redis Stream topic.
    Creates a consumer group if it doesn't exist.
    """
    r = get_redis_client()
    try:
        r.xgroup_create(topic, group, id="0", mkstream=True)
        logging.info(f"Consumer group '{group}' ensured for topic '{topic}'.")
    except redis.exceptions.ResponseError as e:
        if "BUSYGROUP" not in str(e):
            raise
        logging.debug(f"Consumer group '{group}' already exists for topic '{topic}'.")

    while True:
        # '>' means get new messages that haven't been delivered to other consumers in the group.
        response = r.xreadgroup(group, consumer, {topic: ">"}, count=1, block=block_ms)
        if not response:
            continue

        stream, messages = response[0]
        message_id, data = messages[0]

        yield data

        # Acknowledge the message so it's not re-delivered.
        r.xack(topic, group, message_id)


@contextmanager
def graceful_shutdown():
    """Context manager to handle SIGTERM for graceful shutdown."""
    shutdown_flag = False

    def handler(signum, frame):
        nonlocal shutdown_flag
        logging.info(f"Received signal {signum}, shutting down gracefully...")
        shutdown_flag = True

    original_sigterm = signal.getsignal(signal.SIGTERM)
    signal.signal(signal.SIGTERM, handler)

    try:
        yield lambda: shutdown_flag
    finally:
        signal.signal(signal.SIGTERM, original_sigterm)
