import json, logging, datetime as dt
from app import bus, memory_keeper

def main():
    today = dt.datetime.utcnow().date()
    event = {
        "type": "CatalystEvent",
        "event_name": "CPI Release",
        "event_time_utc": dt.datetime.combine(today, dt.time(12, 30)).isoformat(),
        "expected_impact": "High market volatility."
    }
    bus.publish(bus.TOPIC_PLAYBOOK, event)
    memory_keeper.store(f"catalyst:macro:{today}", json.dumps(event))
    logging.info("Macro catalyst published.")

if __name__ == "__main__":
    main()
