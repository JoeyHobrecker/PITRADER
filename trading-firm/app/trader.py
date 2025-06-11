import logging
import os
from time import sleep

import alpaca_trade_api as tradeapi
from app import bus

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
AGENT_NAME = "trader"

# --- CONFIGURATION ---
ALPACA_KEY = os.environ["ALPACA_KEY"]
ALPACA_SECRET = os.environ["ALPACA_SECRET"]
ALPACA_BASE_URL = os.environ.get("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")
TRADE_QTY = 10  # Default quantity to trade


def get_alpaca_api() -> tradeapi.REST:
    """Returns an authenticated Alpaca API client."""
    return tradeapi.REST(
        key_id=ALPACA_KEY,
        secret_key=ALPACA_SECRET,
        base_url=ALPACA_BASE_URL,
        api_version="v2",
    )


def main():
    """
    Subscribes to the 'trade_signals' topic and executes trades via Alpaca.
    Publishes fill confirmations to the 'fills' topic.
    """
    logging.info("Trader agent started. Awaiting trade signals.")
    api = get_alpaca_api()

    # Check if the market is open now.
    clock = api.get_clock()
    if not clock.is_open:
        logging.warning(
            "Market is closed. Trader will not execute orders until it opens."
        )
        # In a real system, you might wait for market open event.

    with bus.graceful_shutdown() as is_shutting_down:
        for msg in bus.subscribe(bus.TOPIC_TRADE_SIGNALS, AGENT_NAME):
            if is_shutting_down():
                break

            ticker = msg.get("ticker")
            action = msg.get("action")

            if not ticker or action not in ["BUY", "SELL"]:
                logging.warning(f"Invalid trade signal received: {msg}")
                continue

            logging.info(f"Received trade signal: {action} {ticker}")

            try:
                order = api.submit_order(
                    symbol=ticker,
                    qty=TRADE_QTY,
                    side=action.lower(),
                    type="market",
                    time_in_force="day",
                )
                logging.info(
                    f"Submitted {action.lower()} order for {TRADE_QTY} shares of {ticker}. Order ID: {order.id}"
                )

                # Wait for the order to fill to get execution price
                # This is a simplification; a real system would handle this asynchronously.
                filled = False
                for _ in range(10):  # Poll for 50 seconds
                    order_status = api.get_order(order.id)
                    if order_status.status == "filled":
                        fill_data = {
                            "order_id": str(order.id),
                            "ticker": order_status.symbol,
                            "qty": float(order_status.filled_qty),
                            "price": float(order_status.filled_avg_price),
                            "side": order_status.side,
                            "timestamp_utc": order_status.filled_at.isoformat(),
                        }
                        bus.publish(bus.TOPIC_FILLS, fill_data)
                        logging.info(f"Order filled: {fill_data}")
                        filled = True
                        break
                    sleep(5)

                if not filled:
                    logging.warning(
                        f"Order {order.id} for {ticker} did not fill in time."
                    )

            except tradeapi.rest.APIError as e:
                logging.error(
                    f"Alpaca API error while executing trade for {ticker}: {e}"
                )
            except Exception as e:
                logging.error(f"An unexpected error occurred during trading: {e}")

    logging.info("Trader agent shutting down.")


if __name__ == "__main__":
    main()
