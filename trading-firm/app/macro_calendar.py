import json
import logging
import os
from datetime import datetime, time

from app import bus, memory_keeper
from app.playbook_schema import CatalystEvent
from pydantic import ValidationError

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# --- CONFIGURATION ---
# TODO: Get real API key from settings.yaml
CIVICFEED_API_KEY = os.environ.get("CIVICFEED_API_KEY")


def fetch_economic_events() -> list[dict]:
    """
    MOCK: Fetches upcoming major economic events from an API like CivicFeed or a public calendar.
    """
    logging.info("Fetching upcoming economic events...")
    if not CIVICFEED_API_KEY or CIVICFEED_API_KEY == "YOUR_CIVICFEED_API_KEY":
        logging.warning("CIVICFEED_API_KEY not set. Using mock data.")
        # Return mock data for CPI and FOMC
        today = datetime.utcnow().date()
        return [
            {
                "event_name": "CPI Release",
                "event_time_utc": datetime.combine(today, time(12, 30)),  # 8:30 AM EST
                "expected_impact": "High volatility expected across indices. Measures inflation.",
            },
            {
                "event_name": "FOMC Meeting Minutes",
                "event_time_utc": datetime.combine(today, time(18, 0)),  # 2:00 PM EST
                "expected_impact": "Moderate volatility. Provides insight into future monetary policy.",
            },
        ]
    # TODO: Implement actual API call to a financial calendar service
    return []


def main():
    """Main execution for the Macro Calendar agent."""
    logging.info("Macro Calendar starting its daily scan...")

    events = fetch_economic_events()

    if not events:
        logging.info("No major economic events found for today.")
        return

    for event in events:
        try:
            # Add the literal 'type' for Pydantic validation
            event["type"] = "CatalystEvent"
            catalyst_event_model = CatalystEvent.model_validate(event)
            catalyst_event_dict = catalyst_event_model.model_dump(mode="json")

            event_str = json.dumps(catalyst_event_dict)

            # 1. Publish to the playbook stream
            bus.publish(bus.TOPIC_PLAYBOOK, catalyst_event_dict)
            logging.info(
                f"Published macro event to '{bus.TOPIC_PLAYBOOK}': {event_str}"
            )

            # 2. Store in long-term memory
            doc_id = f"catalyst:macro:{catalyst_event_model.event_name}:{catalyst_event_model.event_time_utc.date()}".replace(
                " ", "_"
            )
            memory_keeper.store(doc_id, event_str)
            logging.info(f"Stored macro event in Weaviate with ID '{doc_id}'.")

        except ValidationError as e:
            logging.error(f"Failed to validate and process macro event {event}: {e}")
            continue

    logging.info("Macro Calendar scan complete.")


if __name__ == "__main__":
    main()
