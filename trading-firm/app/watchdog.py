import logging
import os

import yaml
from app import bus
from app.playbook_schema import SystemHalt

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
AGENT_NAME = "watchdog"

# --- CONFIGURATION ---
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "settings.yaml")
with open(CONFIG_PATH, "r") as f:
    config = yaml.safe_load(f)

MAX_NOTIONAL_USD = config["risk"]["max_notional_usd"]
HALT_KEY = config["risk"]["halt_key"]


def main():
    """
    Subscribes to the 'fills' topic to monitor portfolio exposure.
    If risk limits are breached, it sets a system-wide HALT flag in Redis
    and publishes a HALT message to the playbook.
    """
    logging.info("Watchdog agent started. Monitoring portfolio risk.")
    r = bus.get_redis_client()

    # Initialize current notional value from Redis or start at 0
    current_notional = float(r.get("portfolio:notional_usd") or 0.0)
    logging.info(f"Initial portfolio notional value: ${current_notional:,.2f}")

    with bus.graceful_shutdown() as is_shutting_down:
        for msg in bus.subscribe(bus.TOPIC_FILLS, AGENT_NAME):
            if is_shutting_down():
                break

            try:
                qty = float(msg.get("qty", 0))
                price = float(msg.get("price", 0))
                side = msg.get("side")

                trade_value = qty * price

                if side == "buy":
                    current_notional += trade_value
                elif side == "sell":
                    current_notional -= trade_value

                # Persist the new notional value
                r.set("portfolio:notional_usd", current_notional)
                logging.info(f"Portfolio notional updated to: ${current_notional:,.2f}")

                # Check against risk limits
                if abs(current_notional) > MAX_NOTIONAL_USD:
                    if r.get(HALT_KEY) != "1":
                        logging.critical(
                            f"RISK LIMIT BREACHED! Notional value ${current_notional:,.2f} "
                            f"exceeds max of ${MAX_NOTIONAL_USD:,.2f}. HALTING SYSTEM."
                        )
                        # 1. Set the global HALT flag in Redis
                        r.set(HALT_KEY, "1")

                        # 2. Publish a HALT event to the playbook stream for logging and alerting
                        halt_event = SystemHalt(
                            reason=f"Max notional limit of ${MAX_NOTIONAL_USD:,.2f} breached."
                        )
                        bus.publish(
                            bus.TOPIC_PLAYBOOK, halt_event.model_dump(mode="json")
                        )

                # TODO: Implement VaR calculation and check against max_var_pct

            except (TypeError, ValueError) as e:
                logging.error(f"Could not process fill message: {msg}. Error: {e}")

    logging.info("Watchdog agent shutting down.")


if __name__ == "__main__":
    main()
