"""
SportsClaw FPL Telegram Bot
python-telegram-bot v20.7 + Python 3.11
"""
import os, logging, json, pathlib, threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, ContextTypes
)
from fpl_data import get_players, get_current_gw, refresh_cache
from fpl_logic import build_brief, get_captain_picks, get_transfers, get_differentials, get_chip_advice
from broadcaster import schedule_broadcast

logging.basicConfig(format="%(asctime)s [%(levelname)s] %(message)s", level=logging.INFO)
log = logging.getLogger("SportsClaw")

# ── Health server so Render Web Service doesn't kill the process ──────────────
class _Health(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")
    def log_message(self, *a):
        pass  # silence noisy access logs

def _start_health_server():
    port = int(os.environ.get("PORT", 8080))
    HTTPServer(("0.0.0.0", port), _Health).serve_forever()
# ─────────────────────────────────────────────────────────────────────────────

# Load token — from Render env vars or local .env file
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    env_path = pathlib.Path(".env")
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                if k.strip() == "TELEGRAM_BOT_TOKEN":
                    TOKEN = v.strip()
                    break

if not TOKEN:
    log.error("TELEGRAM_BOT_TOKEN not found! Set it as an environment variable on Render.")
    raise SystemExit(1)

log.info(f"Token loaded — starts with: {TOKEN[:10]}...")

SUBS_FILE = pathlib.Path(".subscribers.json")
def load_subs(): return json.loads(SUBS_FILE.read_text()) if SUBS_FILE.exists() else []
def save_subs(s): SUBS_FILE.write_text(json.dumps(s))


async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    name = update.effective_user.first_name or "Manager"
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📋 GW Brief",         callback_data="brief")],
        [InlineKeyboardButton("👑 Captain Pick",     callback_data="captain")],
        [InlineKeyboardButton("🔄 Transfer Targets", callback_data="transfers")],
        [InlineKeyboardButton("🎯 Differentials",    callback_data="diffs")],
        [InlineKeyboardButton("🃏 Chip Advice",      callback_data="chips")],
    ])
    await update.message.reply_text(
        f"Hey {name}! 👋 Welcome to *SportsClaw FPL Bot* 🦅\n\nPick an option below:",
        parse_mode="Markdown",
        reply_markup=kb,
    )


async def subscribe(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    cid = update.effective_chat.id
    subs = load_subs()
    if cid not in subs:
        subs.append(cid)
        save_subs(subs)
        await update.message.reply_text("✅ Subscribed! You'll get weekly GW briefings.")
    else:
        await update.message.reply_text("You're already subscribed.")


async def unsubscribe(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    cid = update.effective_chat.id
    subs = load_subs()
    if cid in subs:
        subs.remove(cid)
        save_subs(subs)
        await update.message.reply_text("❌ Unsubscribed.")
    else:
        await update.message.reply_text("You're not subscribed.")


async def button(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    players = get_players()
    gw      = get_current_gw()

    if data == "brief":
        text = build_brief(players, gw)
    elif data == "captain":
        text = get_captain_picks(players)
    elif data == "transfers":
        text = get_transfers(players)
    elif data == "diffs":
        text = get_differentials(players)
    elif data == "chips":
        text = get_chip_advice(gw)
    else:
        text = "Unknown option."

    await query.edit_message_text(text, parse_mode="Markdown")


def main():
    # Start health server in background thread FIRST so Render sees the port
    threading.Thread(target=_start_health_server, daemon=True).start()
    log.info("Health server started on PORT %s", os.environ.get("PORT", 8080))

    log.info("Loading FPL data...")
    refresh_cache()
    log.info("Starting SportsClaw bot...")

    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start",       start))
    app.add_handler(CommandHandler("subscribe",   subscribe))
    app.add_handler(CommandHandler("unsubscribe", unsubscribe))
    app.add_handler(CallbackQueryHandler(button))

    schedule_broadcast(app)

    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
