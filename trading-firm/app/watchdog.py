import logging, os
from app import bus, playbook_schema
import yaml

cfg = yaml.safe_load(open(os.path.join(os.path.dirname(__file__),"..","config","settings.yaml")))
MAX_NOTIONAL = cfg["risk"]["max_notional_usd"]
redis = bus.get_redis_client()
notional = 0.0
for fill in bus.subscribe(bus.TOPIC_FILLS, "watchdog"):
    q = float(fill["qty"]); p = float(fill["price"])
    notional += q*p if fill["side"]=="buy" else -q*p
    redis.set("portfolio:notional_usd", notional)
    if abs(notional) > MAX_NOTIONAL and redis.get(cfg["risk"]["halt_key"])!="1":
        redis.set(cfg["risk"]["halt_key"], "1")
        bus.publish(bus.TOPIC_PLAYBOOK, {"type":"SystemHalt","reason":"Max notional breached"})
        logging.critical("HALT issued due to risk.")
