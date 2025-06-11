import asyncio
import json
import logging
import os
from datetime import datetime

import yaml
from app import bus, memory_keeper
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# --- CONFIGURATION ---
TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = int(os.environ["TELEGRAM_CHAT_ID"])
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "settings.yaml")
with open(CONFIG_PATH, "r") as f:
    config = yaml.safe_load(f)
HALT_KEY = config["risk"]["halt_key"]

# --- Command Handlers ---


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Trading Desk Bot activated. Use /help for commands."
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
Available Commands:
/status - Check if the system is running or halted.
/pause - Halt all new trading activity.
/resume - Resume trading activity.
/objectives - Show current weekly objectives.
/tasks - Show current weekly tasks.
/next_events - List upcoming catalyst events.
"""
    await update.message.reply_text(help_text)


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    r = bus.get_redis_client()
    if r.get(HALT_KEY) == "1":
        await update.message.reply_text("System Status: 🔴 HALTED")
    else:
        await update.message.reply_text("System Status: 🟢 RUNNING")


async def pause(update: Update, context: ContextTypes.DEFAULT_TYPE):
    r = bus.get_redis_client()
    r.set(HALT_KEY, "1")
    logging.warning(f"System manually halted by user {update.effective_user.name}")
    await update.message.reply_text("System HALTED. No new trades will be executed.")


async def resume(update: Update, context: ContextTypes.DEFAULT_TYPE):
    r = bus.get_redis_client()
    r.delete(HALT_KEY)
    logging.info(f"System manually resumed by user {update.effective_user.name}")
    await update.message.reply_text("System RESUMED. Trading is now active.")


async def send_last_playbook_section(
    update: Update, context: ContextTypes.DEFAULT_TYPE, section: str
):
    """Helper to fetch and send a playbook section."""
    data = memory_keeper.get_latest_playbook_section(section)
    if not data:
        await update.message.reply_text(f"Could not find any recent {section}.")
        return

    message = f"📘 *Current {section.capitalize()}* 📘\n\n"
    if section == "okrs":
        for i, okr in enumerate(data, 1):
            message += f"*{i}. {okr['objective']}*\n"
            for res in okr["key_results"]:
                message += f"  - {res}\n"
            message += "\n"
    elif section == "tasks":
        for i, task in enumerate(data, 1):
            message += f"*{i}. {task['description']}*\n"

    await update.message.reply_text(message, parse_mode="Markdown")


async def objectives(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_last_playbook_section(update, context, "okrs")


async def tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_last_playbook_section(update, context, "tasks")


async def next_events(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends upcoming catalyst events from memory."""
    # This query is a simple proxy. A better way would be to query for
    # CatalystEvents with a future event_time_utc.
    results = memory_keeper.query(
        "upcoming catalyst events like CPI, FOMC, or court cases", top_k=10
    )

    if not results:
        await update.message.reply_text(
            "No upcoming catalyst events found in recent memory."
        )
        return

    message = "🗓️ *Next Catalyst Events* 🗓️\n\n"
    for res in results:
        try:
            # We only want to show actual catalyst events, not other memories
            data = json.loads(res)
            if data.get("type") == "CatalystEvent":
                event_time = datetime.fromisoformat(data["event_time_utc"]).strftime(
                    "%Y-%m-%d %H:%M UTC"
                )
                message += f"*{data['event_name']}* ({data.get('ticker', 'GLOBAL')})\n"
                message += f"  - Time: {event_time}\n"
                message += f"  - Impact: {data['expected_impact']}\n\n"
        except (json.JSONDecodeError, KeyError):
            continue

    await update.message.reply_text(message, parse_mode="Markdown")


async def listen_to_bus(app: Application):
    """A background task to listen to Redis and push notifications."""
    logging.info("Telegram notifier started, listening to fills and playbook.")

    # We create a combined stream listener
    # A more robust implementation would use a dedicated consumer group
    stream = bus.subscribe(bus.TOPIC_FILLS, "telegram_notifier_fills")

    for msg in stream:
        try:
            side = msg["side"]
            qty = msg["qty"]
            ticker = msg["ticker"]
            price = float(msg["price"])

            icon = "🟢" if side == "buy" else "🔴"
            text = f"{icon} *Trade Executed*\n\n*{side.upper()}* {qty} *{ticker}* @ ${price:,.2f}"
            await app.bot.send_message(
                chat_id=CHAT_ID, text=text, parse_mode="Markdown"
            )
        except Exception as e:
            logging.error(f"Error sending Telegram notification for fill: {e}")


async def main():
    """Run the bot."""
    app = Application.builder().token(TOKEN).build()

    # Add command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("pause", pause))
    app.add_handler(CommandHandler("resume", resume))
    app.add_handler(CommandHandler("objectives", objectives))
    app.add_handler(CommandHandler("tasks", tasks))
    app.add_handler(CommandHandler("next_events", next_events))

    # Start the background task for listening to Redis
    # We use asyncio.create_task to run it concurrently with the bot polling
    asyncio.create_task(listen_to_bus(app))

    # Run the bot until the user presses Ctrl-C
    await app.run_polling()


if __name__ == "__main__":
    asyncio.run(main())
