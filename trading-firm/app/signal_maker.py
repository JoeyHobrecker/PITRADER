import logging, datetime as dt
from app import bus

def sentiment(txt: str) -> float:
    pos = ["up","beats","gain","rise","upgrade"]
    neg = ["down","miss","loss","fall","downgrade"]
    s = 0
    for w in pos:
        if w in txt.lower(): s += .7
    for w in neg:
        if w in txt.lower(): s -= .7
    return max(-1, min(1, s))

def run():
    redis = bus.get_redis_client()
    news = bus.subscribe(bus.TOPIC_NEWS_RAW, "signal_maker_news")
    holds = bus.subscribe(bus.TOPIC_PLAYBOOK, "signal_maker_pb")
    for msg in holds:
        if msg.get("type")=="CatalystEvent" and msg.get("ticker") and msg.get("hold_until_utc"):
            redis.hset("holds", msg["ticker"], msg["hold_until_utc"])

    for n in news:
        t = n.get("ticker")
        if not t: continue
        hold_until = redis.hget("holds", t)
        if hold_until and dt.datetime.utcnow().isoformat() < hold_until:
            continue
        score = sentiment(n["headline"])
        if score>0.6:
            bus.publish(bus.TOPIC_TRADE_SIGNALS, {"ticker":t,"action":"BUY","score":score})
        elif score<-0.6:
            bus.publish(bus.TOPIC_TRADE_SIGNALS, {"ticker":t,"action":"SELL","score":score})

if __name__ == "__main__":
    run()
