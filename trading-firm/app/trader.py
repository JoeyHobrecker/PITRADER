import logging, os, time
import alpaca_trade_api as tradeapi
from app import bus

api = tradeapi.REST(os.environ["ALPACA_KEY"], os.environ["ALPACA_SECRET"], base_url=os.environ.get("ALPACA_BASE_URL","https://paper-api.alpaca.markets"))
for sig in bus.subscribe(bus.TOPIC_TRADE_SIGNALS, "trader"):
    sym = sig["ticker"]; side = sig["action"].lower()
    try:
        o = api.submit_order(symbol=sym, qty=10, side=side, type='market', time_in_force='day')
        time.sleep(2)
        filled = api.get_order(o.id)
        if filled.status=="filled":
            bus.publish(bus.TOPIC_FILLS, {"ticker":sym,"qty":filled.filled_qty,"price":filled.filled_avg_price,"side":side})
    except Exception as e:
        logging.error(e)
