import json
import logging
import os
import uuid
from datetime import datetime, timedelta
from typing import Optional

import openai
from app import bus, memory_keeper
from app.playbook_schema import Playbook
from pydantic import ValidationError

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# --- CONFIGURATION ---
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
# Note: User requested "gpt-4o-mini-high". If this model is not available,
# change to a valid model like "gpt-4o-mini" in settings.yaml.
PLANNER_MODEL = os.environ.get("OPENAI_MODEL_PLANNER", "gpt-4o-mini")
GENERAL_MODEL = os.environ.get("OPENAI_MODEL_GENERAL", "gpt-4o")

openai.api_key = OPENAI_API_KEY
client = openai.OpenAI()


def generate_weekly_playbook() -> Optional[dict]:
    """
    Generates a new weekly playbook using GPT-4.5, based on past performance
    and long-term memory.
    """
    today = datetime.utcnow()
    start_date = today.strftime("%Y-%m-%d")
    end_date = (today + timedelta(days=7)).strftime("%Y-%m-%d")

    logging.info("Querying long-term memory for strategic context...")
    # Query for all memories from the last month to inform the new playbook
    memory_query = f"Retrieve all playbooks, catalyst events, and major news headlines from the last 30 days."
    long_term_memory = memory_keeper.query(memory_query, top_k=25)

    # TODO: Fetch last week's performance data from Alpaca or fills stream summary
    last_week_performance = (
        "neutral performance, with small gains in QQQ and losses in IWM."
    )

    system_prompt = f"""
You are the Chief Investment Strategist for a small, agile, AI-powered trading firm.
Your task is to create a strategic "Playbook" for the upcoming week ({start_date} to {end_date}).
Your output MUST be a valid JSON object that conforms to the Playbook Pydantic schema.
The playbook should contain high-level objectives (OKRs) and specific, actionable tasks for the trading agents.

Analyze the provided context to inform your strategy:
1.  **Last Week's Performance:** {last_week_performance}
2.  **Long-Term Memory & Recent Events (past 30 days):**
    - {"\n- ".join(long_term_memory)}

Based on this, define a coherent strategy. For example, if you see upcoming CPI data and recent tech volatility, a valid strategy might be to be defensive pre-CPI and then trade momentum in the tech sector post-release.
"""

    user_prompt = f"""
Generate the JSON playbook for the week of {start_date} to {end_date}.
The JSON must have keys: "type", "start_date", "end_date", "okrs", and "tasks".
"type" must be "Playbook".
"okrs" should be a list of objects, each with an "objective" and "key_results".
"tasks" should be a list of objects, each with a "description" and optional "dependencies".
"""
    logging.info("Calling OpenAI to generate playbook...")
    try:
        completion = client.chat.completions.create(
            model=PLANNER_MODEL,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            # Every outbound OpenAI call tagged with trace_id header
            extra_headers={"trace_id": str(uuid.uuid4())},
        )
        playbook_json_str = completion.choices[0].message.content
        playbook_data = json.loads(playbook_json_str)

        # Validate with Pydantic
        Playbook.model_validate(playbook_data)
        logging.info("Successfully generated and validated new weekly playbook.")
        return playbook_data

    except (openai.APIError, json.JSONDecodeError, ValidationError) as e:
        logging.error(f"Failed to generate or validate playbook: {e}")
        return None


def main():
    """Main execution function for the Chief Strategist."""
    logging.info("Chief Strategist starting weekly planning cycle...")
    playbook = generate_weekly_playbook()

    if playbook:
        playbook_str = json.dumps(playbook)

        # 1. Publish the new playbook to the message bus for all agents
        bus.publish(bus.TOPIC_PLAYBOOK, playbook)
        logging.info(f"Published new playbook to topic '{bus.TOPIC_PLAYBOOK}'.")

        # 2. Persist the playbook in long-term memory
        doc_id = f"playbook:{playbook['start_date']}"
        memory_keeper.store(doc_id, playbook_str)
        logging.info(f"Stored playbook in Weaviate with ID '{doc_id}'.")
    else:
        logging.error(
            "Could not generate a playbook this week. No new strategy will be issued."
        )

    logging.info("Chief Strategist finished.")


if __name__ == "__main__":
    main()
