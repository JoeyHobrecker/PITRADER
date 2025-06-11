import asyncio, logging, os, json, datetime as dt
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from app import bus, memory_keeper
TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]; CHAT_ID=int(os.environ["TELEGRAM_CHAT_ID"]); HALT="HALT"
redis = bus.get_redis_client()

async def status(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("HALTED" if redis.get(HALT)=="1" else "RUNNING")

async def pause(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    redis.set(HALT,"1"); await update.message.reply_text("HALTED")

async def resume(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    redis.delete(HALT); await update.message.reply_text("RESUMED")

async def objectives(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    okrs = memory_keeper.get_latest_playbook_section("okrs") or []
    await update.message.reply_text(json.dumps(okrs, indent=2))

async def tasks(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    tasks = memory_keeper.get_latest_playbook_section("tasks") or []
    await update.message.reply_text(json.dumps(tasks, indent=2))

async def start_bot():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("pause", pause))
    app.add_handler(CommandHandler("resume", resume))
    app.add_handler(CommandHandler("objectives", objectives))
    app.add_handler(CommandHandler("tasks", tasks))
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(start_bot())
