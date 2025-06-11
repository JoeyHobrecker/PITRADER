import json, logging, os, uuid, datetime as dt
import openai
from app import bus, memory_keeper
from app.playbook_schema import CatalystEvent

openai.api_key = os.environ["OPENAI_API_KEY"]
MODEL = os.environ.get("OPENAI_MODEL_GENERAL", "gpt-4o")

def mock_cases():
    return [{
        "ticker": "MSFT",
        "case_name": "US DOJ vs Microsoft",
        "next_event_date": (dt.datetime.utcnow() + dt.timedelta(days=20)).isoformat(),
        "docket_text": "Verdict expected within 3 weeks."
    }]

def main():
    for case in mock_cases():
        event = {
            "type": "CatalystEvent",
            "event_name": f"{case['case_name']} Verdict",
            "ticker": case["ticker"],
            "event_time_utc": case["next_event_date"],
            "hold_until_utc": case["next_event_date"],
            "expected_impact": "Potentially high volatility."
        }
        bus.publish(bus.TOPIC_PLAYBOOK, event)
        memory_keeper.store(f"catalyst:legal:{case['ticker']}", json.dumps(event))
        logging.info(f"Legal catalyst published for {case['ticker']}")

if __name__ == "__main__":
    main()
