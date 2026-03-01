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

# ── Health server so Render Web Service does not kill the process ─────────────
class _Health(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")
    def log_message(self, *a):
        pass

def _start_health_server():
    port = int(os.environ.get("PORT", 8080))
    HTTPServer(("0.0.0.0", port), _Health).serve_forever()
# ─────────────────────────────────────────────────────────────────────────────

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
    log.error("TELEGRAM_BOT_TOKEN not found!")
    raise SystemExit(1)

log.info(f"Token loaded — starts with: {TOKEN[:10]}...")

SUBS_FILE = pathlib.Path(".subscribers.json")
def load_subs(): return json.loads(SUBS_FILE.read_text()) if SUBS_FILE.exists() else []
def save_subs(s): SUBS_FILE.write_text(json.dumps(s))

MAIN_KB = InlineKeyboardMarkup([
    [InlineKeyboardButton("📋 GW Brief",         callback_data="brief")],
    [InlineKeyboardButton("👑 Captain Pick",     callback_data="captain")],
    [InlineKeyboardButton("🔄 Transfer Targets", callback_data="transfers")],
    [InlineKeyboardButton("🎯 Differentials",    callback_data="diffs")],
    [InlineKeyboardButton("🃏 Chip Advice",      callback_data="chips")],
])


async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    name = update.effective_user.first_name or "Manager"
    await update.message.reply_text(
        f"Hey {name}! 👋 Welcome to *SportsClaw FPL Bot* 🦅\n\nPick an option below:",
        parse_mode="Markdown",
        reply_markup=MAIN_KB,
    )

async def cmd_brief(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(build_brief(), parse_mode="Markdown", reply_markup=MAIN_KB)

async def cmd_captain(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(get_captain_picks(), parse_mode="Markdown", reply_markup=MAIN_KB)

async def cmd_transfers(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    args = ctx.args  # e.g. /transfers Salah 13.8
    if args:
        player_out = args[0]
        budget = float(args[1]) if len(args) > 1 else None
        text = get_transfers(player_out=player_out, budget=budget)
    else:
        text = get_transfers()
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=MAIN_KB)

async def cmd_diffs(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(get_differentials(), parse_mode="Markdown", reply_markup=MAIN_KB)

async def cmd_chips(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(get_chip_advice(), parse_mode="Markdown", reply_markup=MAIN_KB)

async def subscribe(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    cid = update.effective_chat.id
    subs = load_subs()
    if cid not in subs:
        subs.append(cid); save_subs(subs)
        await update.message.reply_text("✅ Subscribed! You'll get weekly GW briefings.")
    else:
        await update.message.reply_text("You're already subscribed.")

async def unsubscribe(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    cid = update.effective_chat.id
    subs = load_subs()
    if cid in subs:
        subs.remove(cid); save_subs(subs)
        await update.message.reply_text("❌ Unsubscribed.")
    else:
        await update.message.reply_text("You're not subscribed.")


async def button(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    try:
        if query.data == "brief":       text = build_brief()
        elif query.data == "captain":   text = get_captain_picks()
        elif query.data == "transfers": text = get_transfers()
        elif query.data == "diffs":     text = get_differentials()
        elif query.data == "chips":     text = get_chip_advice()
        else:                           text = "Unknown option."
    except Exception as e:
        log.error(f"Button error [{query.data}]: {e}", exc_info=True)
        text = "⚠️ Something went wrong. Try again in a moment."
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=MAIN_KB)


def main():
    threading.Thread(target=_start_health_server, daemon=True).start()
    log.info("Health server started on PORT %s", os.environ.get("PORT", 8080))

    log.info("Loading FPL data...")
    refresh_cache()
    log.info("Starting SportsClaw bot...")

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start",       start))
    app.add_handler(CommandHandler("brief",       cmd_brief))
    app.add_handler(CommandHandler("captain",     cmd_captain))
    app.add_handler(CommandHandler("transfers",   cmd_transfers))
    app.add_handler(CommandHandler("diffs",       cmd_diffs))
    app.add_handler(CommandHandler("chips",       cmd_chips))
    app.add_handler(CommandHandler("subscribe",   subscribe))
    app.add_handler(CommandHandler("unsubscribe", unsubscribe))
    app.add_handler(CallbackQueryHandler(button))

    schedule_broadcast(app)

    app.run_polling(
        drop_pending_updates=True,
        allowed_updates=Update.ALL_TYPES,
    )


if __name__ == "__main__":
    main()
