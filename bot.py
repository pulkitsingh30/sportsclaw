"""
SportsClaw FPL Telegram Bot
python-telegram-bot v20.7 + Python 3.11
"""
import os, logging, json, pathlib
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, ContextTypes
)
from fpl_data import get_players, get_current_gw, refresh_cache
from fpl_logic import build_brief, get_captain_picks, get_transfers, get_differentials, get_chip_advice
from broadcaster import schedule_broadcast

logging.basicConfig(format="%(asctime)s [%(levelname)s] %(message)s", level=logging.INFO)
log = logging.getLogger("SportsClaw")

# Load .env
env_path = pathlib.Path(".env")
if env_path.exists():
    for line in env_path.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ[k.strip()] = v.strip()

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN not set in .env")

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
    await update.message.reply_markdown(
        f"🏆 *Welcome to SportsClaw, {name}!*\n\n"
        "Autonomous FPL agent — captain picks, transfers, differentials "
        "and chip advice before every deadline.\n\n"
        "Tap a button or type a command:",
    )