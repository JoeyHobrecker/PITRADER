import json
import logging
import os
import uuid
from datetime import datetime
from typing import Optional

import openai
from app import bus, memory_keeper
from app.playbook_schema import CatalystEvent
from pydantic import ValidationError

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# --- CONFIGURATION ---
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
GENERAL_MODEL = os.environ.get("OPENAI_MODEL_GENERAL", "gpt-4o")
# TODO: Get real API key from settings.yaml
COURTLISTENER_API_KEY = os.environ.get("COURTLISTENER_API_KEY")

client = openai.OpenAI(api_key=OPENAI_API_KEY)


def fetch_court_cases(tickers: list[str]) -> list[dict]:
    """
    MOCK: Fetches recent court case dockets from an API like CourtListener.
    Filters for cases involving specified public companies (tickers).
    """
    logging.info(f"Checking for court cases involving: {tickers}")
    if (
        not COURTLISTENER_API_KEY
        or COURTLISTENER_API_KEY == "YOUR_COURTLISTENER_API_KEY"
    ):
        logging.warning("COURTLISTENER_API_KEY not set. Using mock data.")
        # Return a mock docket if any of the tickers are, for example, 'MSFT'
        if "MSFT" in tickers:
            return [
                {
                    "ticker": "MSFT",
                    "case_name": "US DOJ vs. Microsoft Corp",
                    "docket_text": "A new filing indicates a verdict is expected by the end of next month. The core of the case revolves around cloud computing market dominance.",
                    "next_event_date": "2024-07-30",  # Mock date
                }
            ]
    # TODO: Implement actual API call to CourtListener
    return []


def summarize_and_create_event(case: dict) -> Optional[dict]:
    """Uses GPT to summarize docket and create a CatalystEvent."""
    system_prompt = """
You are a legal analyst AI. Your task is to analyze a court case docket and determine if it's a significant market catalyst.
If it is, you must create a JSON object for a "CatalystEvent".
- "event_name" should be concise (e.g., "DOJ vs. MSFT Verdict Expected").
- "ticker" is the company involved.
- "event_time_utc" is when the event is expected.
- "hold_until_utc" should be set to the day AFTER the event if a verdict is pending, to prevent trading on uncertainty.
- "expected_impact" must be a neutral, factual summary.
Your output must be only the JSON object.
"""
    user_prompt = f"Analyze this docket: {json.dumps(case)}"

    try:
        completion = client.chat.completions.create(
            model=GENERAL_MODEL,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            extra_headers={"trace_id": str(uuid.uuid4())},
        )
        event_data_str = completion.choices[0].message.content
        event_data = json.loads(event_data_str)
        event_data["type"] = "CatalystEvent"

        # Validate with Pydantic
        CatalystEvent.model_validate(event_data)
        return event_data

    except (openai.APIError, json.JSONDecodeError, ValidationError) as e:
        logging.error(
            f"Failed to create catalyst event for case {case.get('case_name')}: {e}"
        )
        return None


def main():
    """Main execution for the Legal Sentinel."""
    logging.info("Legal Sentinel starting its scan...")
    # TODO: Get current portfolio tickers from Alpaca or a Redis state store
    current_portfolio = ["AAPL", "MSFT", "GOOG"]

    new_cases = fetch_court_cases(current_portfolio)

    if not new_cases:
        logging.info("No new relevant court cases found.")
        return

    for case in new_cases:
        catalyst_event = summarize_and_create_event(case)
        if catalyst_event:
            event_str = json.dumps(catalyst_event, default=str)

            # 1. Publish to the playbook stream
            bus.publish(bus.TOPIC_PLAYBOOK, catalyst_event)
            logging.info(
                f"Published legal catalyst event to '{bus.TOPIC_PLAYBOOK}': {event_str}"
            )

            # 2. Store in long-term memory
            doc_id = f"catalyst:legal:{catalyst_event['ticker']}:{catalyst_event['event_name']}".replace(
                " ", "_"
            )
            memory_keeper.store(doc_id, event_str)
            logging.info(f"Stored legal catalyst event in Weaviate with ID '{doc_id}'.")

    logging.info("Legal Sentinel scan complete.")


if __name__ == "__main__":
    main()
