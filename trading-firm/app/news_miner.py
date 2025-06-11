import json
import logging
import os
from datetime import datetime
from time import sleep

import feedparser
import yaml
from app import bus
from app.playbook_schema import NewsHeadline

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# --- CONFIGURATION ---
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "settings.yaml")
with open(CONFIG_PATH, "r") as f:
    config = yaml.safe_load(f)

RSS_FEEDS = config["optics"]["rss_feeds"]
POLL_INTERVAL_SECONDS = 300  # 5 minutes


def main():
    """
    Continuously polls RSS feeds for new headlines, publishing them to two topics:
    1. 'news_raw' for immediate signal generation.
    2. 'playbook' for long-term memory storage and strategic context.
    """
    logging.info(
        f"News Miner started. Polling {len(RSS_FEEDS)} feeds every {POLL_INTERVAL_SECONDS} seconds."
    )

    # Use a set to keep track of headlines we've already seen to avoid duplicates
    seen_headlines = set()

    with bus.graceful_shutdown() as is_shutting_down:
        while not is_shutting_down():
            for feed_url in RSS_FEEDS:
                try:
                    feed = feedparser.parse(feed_url)
                    source = feed.feed.get("title", "Unknown Source")
                    for entry in feed.entries:
                        headline_text = entry.title
                        if headline_text not in seen_headlines:
                            seen_headlines.add(headline_text)

                            # Basic ticker extraction (can be improved with NLP)
                            # TODO: Implement more robust ticker extraction
                            ticker = None

                            # 1. Publish raw news for signal maker
                            raw_news_item = {
                                "headline": headline_text,
                                "source": source,
                                "link": entry.link,
                                "ticker": ticker,
                            }
                            bus.publish(bus.TOPIC_NEWS_RAW, raw_news_item)
                            logging.info(f"Published raw news: '{headline_text}'")

                            # 2. Publish a structured headline to the playbook stream for memory
                            try:
                                headline_for_memory = NewsHeadline(
                                    headline=headline_text, source=source, ticker=ticker
                                )
                                bus.publish(
                                    bus.TOPIC_PLAYBOOK,
                                    headline_for_memory.model_dump(mode="json"),
                                )
                                logging.info(
                                    f"Published headline to playbook/memory: '{headline_text}'"
                                )
                            except Exception as e:
                                logging.error(
                                    f"Error creating/publishing NewsHeadline to playbook: {e}"
                                )

                except Exception as e:
                    logging.error(f"Error fetching or parsing feed {feed_url}: {e}")

            sleep(POLL_INTERVAL_SECONDS)

    logging.info("News Miner shutting down.")


if __name__ == "__main__":
    main()
