"""
SportsClaw FPL Telegram Bot — Python
Uses: python-telegram-bot v21 + requests
Run:  python3 bot.py
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

# Load .env manually
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
        reply_markup=kb
    )

async def cmd_brief(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.callback_query.message
    await msg.reply_text("⚙️ Building your GW brief...")
    await msg.reply_markdown(build_brief())

async def cmd_captain(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.callback_query.message
    await msg.reply_markdown(get_captain_picks())

async def cmd_transfers(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg  = update.message or update.callback_query.message
    args = ctx.args or []
    player_out = " ".join(args[:-1]).strip() if len(args) > 1 else None
    try:    budget = float(args[-1]) if args else None
    except: budget = None
    await msg.reply_markdown(get_transfers(player_out, budget))

async def cmd_diffs(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.callback_query.message
    await msg.reply_markdown(get_differentials())

async def cmd_chips(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.callback_query.message
    await msg.reply_markdown(get_chip_advice())

async def cmd_myteam(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    import requests
    args = ctx.args or []
    if not args or not args[0].isdigit():
        await update.message.reply_markdown(
            "🔗 *Link Your FPL Team*\n\nUsage: `/myteam 1234567`\n\n"
            "Find your ID in the FPL website URL:\n`fantasy.premierleague.com/entry/*12345*/event/29`"
        )
        return
    try:
        r = requests.get(f"https://fantasy.premierleague.com/api/entry/{args[0]}/", timeout=8).json()
        await update.message.reply_markdown(
            f"✅ *Team Linked!*\n\n"
            f"🏆 *{r.get('name','Your Team')}*\n"
            f"👤 {r.get('player_first_name','')} {r.get('player_last_name','')}\n"
            f"🌍 Rank: {r.get('summary_overall_rank', 0):,}"
        )
    except:
        await update.message.reply_text(f"❌ Team ID {args[0]} not found.")

async def cmd_subscribe(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    s = load_subs()
    if update.effective_chat.id not in s:
        s.append(update.effective_chat.id); save_subs(s)
    await update.message.reply_text("✅ Subscribed! Auto-brief before every GW deadline.")

async def cmd_unsubscribe(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    save_subs([x for x in load_subs() if x != update.effective_chat.id])
    await update.message.reply_text("👋 Unsubscribed.")

async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_markdown(
        "🏆 *SportsClaw — Commands*\n\n"
        "/brief — Full GW brief\n"
        "/captain — Captain + VC\n"
        "/transfers — Best transfers\n"
        "/transfers `[name] [budget]` — e.g. `/transfers Salah 13.8`\n"
        "/diffs — Differentials <15% owned\n"
        "/chips — Chip strategy\n"
        "/myteam `[id]` — Link FPL team\n"
        "/subscribe — Auto-brief before deadline\n"
        "/unsubscribe — Stop auto-briefs\n"
        "/help — This menu"
    )

async def button(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    d = update.callback_query.data
    if d == "brief":     await cmd_brief(update, ctx)
    elif d == "captain": await cmd_captain(update, ctx)
    elif d == "transfers":await cmd_transfers(update, ctx)
    elif d == "diffs":   await cmd_diffs(update, ctx)
    elif d == "chips":   await cmd_chips(update, ctx)

async def main():
    log.info("Loading FPL data...")
    refresh_cache()
    log.info("Starting SportsClaw bot...")

    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start",        start))
    app.add_handler(CommandHandler("brief",        cmd_brief))
    app.add_handler(CommandHandler("gw",           cmd_brief))
    app.add_handler(CommandHandler("captain",      cmd_captain))
    app.add_handler(CommandHandler("cap",          cmd_captain))
    app.add_handler(CommandHandler("transfers",    cmd_transfers))
    app.add_handler(CommandHandler("transfer",     cmd_transfers))
    app.add_handler(CommandHandler("diffs",        cmd_diffs))
    app.add_handler(CommandHandler("chips",        cmd_chips))
    app.add_handler(CommandHandler("myteam",       cmd_myteam))
    app.add_handler(CommandHandler("subscribe",    cmd_subscribe))
    app.add_handler(CommandHandler("unsubscribe",  cmd_unsubscribe))
    app.add_handler(CommandHandler("help",         cmd_help))
    app.add_handler(CallbackQueryHandler(button))
    schedule_broadcast(app)

    log.info("Bot is live! Open Telegram -> @SportsClawBot -> /start")
    await app.run_polling(allowed_updates=["message","callback_query"])

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
