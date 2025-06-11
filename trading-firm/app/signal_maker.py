import json
import logging
import os
from datetime import datetime, timezone

from app import bus

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
AGENT_NAME = "signal_maker"


# --- MOCK SENTIMENT ANALYSIS ---
def finbert_sentiment(headline: str) -> float:
    """
    MOCK: Placeholder for a real FinBERT sentiment analysis model.
    Returns a score from -1.0 (very negative) to 1.0 (very positive).
    On a Pi, running a full transformer model might be slow.
    Consider a lightweight model or an API call.
    """
    # Simple keyword-based mock
    positive_words = ["up", "beats", "gains", "rises", "profit", "upgrade"]
    negative_words = ["down", "misses", "losses", "falls", "plunges", "downgrade"]

    score = 0.0
    for word in positive_words:
        if word in headline.lower():
            score += 0.7
    for word in negative_words:
        if word in headline.lower():
            score -= 0.7

    return max(-1.0, min(1.0, score))


def handle_playbook_message(msg: dict):
    """Processes messages from the playbook stream to update holds."""
    r = bus.get_redis_client()
    msg_type = msg.get("type")

    if msg_type == "CatalystEvent" and msg.get("ticker") and msg.get("hold_until_utc"):
        ticker = msg["ticker"]
        hold_until_str = msg["hold_until_utc"]
        hold_until_dt = datetime.fromisoformat(hold_until_str)

        if hold_until_dt > datetime.now(timezone.utc):
            r.hset("holds", ticker, hold_until_str)
            logging.info(
                f"HOLD ACTIVATED for {ticker} until {hold_until_str} due to event '{msg['event_name']}'."
            )


def process_news_and_generate_signals():
    """
    Main loop for the signal maker. Subscribes to two streams:
    1. `playbook` to get hold instructions.
    2. `news_raw` to generate trade signals.
    """
    logging.info("Signal Maker started. Listening for news and playbook events.")
    r = bus.get_redis_client()

    # Use a combined subscription approach if possible, or alternate between them.
    # For simplicity, we'll use two generators and interleave checks.
    # A more robust solution might use threads or asyncio.

    playbook_stream = bus.subscribe(
        bus.TOPIC_PLAYBOOK, AGENT_NAME, consumer="playbook_consumer"
    )
    news_stream = bus.subscribe(
        bus.TOPIC_NEWS_RAW, AGENT_NAME, consumer="news_consumer"
    )

    with bus.graceful_shutdown() as is_shutting_down:
        while not is_shutting_down():
            # Non-blocking check on playbook stream
            for playbook_msg in playbook_stream:
                handle_playbook_message(playbook_msg)
                if is_shutting_down():
                    break

            # Blocking check on news stream
            for news_msg in news_stream:
                if is_shutting_down():
                    break
                ticker = news_msg.get("ticker")
                if not ticker:  # For now, we only trade on ticker-specific news
                    continue

                # Check for holds
                hold_until_str = r.hget("holds", ticker)
                if hold_until_str:
                    hold_until_dt = datetime.fromisoformat(hold_until_str)
                    if datetime.now(timezone.utc) < hold_until_dt:
                        logging.info(
                            f"Signal for {ticker} SUPPRESSED due to active hold until {hold_until_str}."
                        )
                        action = "HOLD"
                    else:
                        # Hold has expired, remove it
                        r.hdel("holds", ticker)
                        logging.info(f"Hold for {ticker} has expired. Removing.")
                        action = None  # Re-evaluate
                else:
                    action = None

                if action != "HOLD":
                    # Generate signal if not on hold
                    score = finbert_sentiment(news_msg["headline"])
                    if score > 0.6:
                        action = "BUY"
                    elif score < -0.6:
                        action = "SELL"
                    else:
                        action = "NEUTRAL"

                if action in ["BUY", "SELL"]:
                    signal = {
                        "ticker": ticker,
                        "action": action,
                        "score": score,
                        "source": AGENT_NAME,
                        "headline": news_msg["headline"],
                    }
                    bus.publish(bus.TOPIC_TRADE_SIGNALS, signal)
                    logging.info(f"Generated signal: {signal}")


if __name__ == "__main__":
    # A real implementation would need to handle multiple streams more robustly.
    # This example interleaves them in a single loop.
    # For production, consider two threads or an async implementation.
    process_news_and_generate_signals()
