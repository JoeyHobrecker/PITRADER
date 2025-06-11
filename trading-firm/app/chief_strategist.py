import json, logging, os, uuid
from datetime import datetime, timedelta

import openai
from app import bus, memory_keeper
from app.playbook_schema import Playbook

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

openai.api_key = os.environ["OPENAI_API_KEY"]
MODEL = os.environ.get("OPENAI_MODEL_PLANNER", "gpt-4o-mini-high")

def generate():
    today = datetime.utcnow()
    pb = {
        "type": "Playbook",
        "start_date": today.strftime("%Y-%m-%d"),
        "end_date": (today + timedelta(days=7)).strftime("%Y-%m-%d"),
        "okrs": [
            {"objective": "Generate alpha from catalyst plays", "key_results": [">= 1% weekly alpha"]},
        ],
        "tasks": [
            {"description": "Scan news for legal verdicts"},
            {"description": "Reduce exposure before CPI"},
        ],
    }
    return pb

def main():
    pb = generate()
    bus.publish(bus.TOPIC_PLAYBOOK, pb)
    memory_keeper.store(f"playbook:{pb['start_date']}", json.dumps(pb))
    logging.info("New weekly playbook published.")

if __name__ == "__main__":
    main()
