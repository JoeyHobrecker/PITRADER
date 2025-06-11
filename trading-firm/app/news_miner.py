import feedparser, logging, time, os, yaml, json
from datetime import datetime
from app import bus
from app.playbook_schema import NewsHeadline

cfg = yaml.safe_load(open(os.path.join(os.path.dirname(__file__), "..", "config", "settings.yaml")))
FEEDS = cfg["optics"]["rss_feeds"]
SEEN = set()

def run():
    while True:
        for url in FEEDS:
            try:
                feed = feedparser.parse(url)
                for entry in feed.entries:
                    if entry.title in SEEN:
                        continue
                    SEEN.add(entry.title)
                    item = {
                        "headline": entry.title,
                        "source": feed.feed.get("title", "Unknown"),
                        "link": entry.link,
                        "ticker": None,
                    }
                    bus.publish(bus.TOPIC_NEWS_RAW, item)
                    headline = NewsHeadline(headline=entry.title, source=item["source"]).model_dump(mode="json")
                    bus.publish(bus.TOPIC_PLAYBOOK, headline)
            except Exception as e:
                logging.error(e)
        time.sleep(300)

if __name__ == "__main__":
    run()
