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

TEAM_LINKS_FILE = pathlib.Path(".team_links.json")
def load_team_links():
    if not TEAM_LINKS_FILE.exists():
        return {}
    try:
        data = json.loads(TEAM_LINKS_FILE.read_text())
        return {str(k): int(v) for k, v in data.items()}
    except Exception:
        return {}
def save_team_links(links): TEAM_LINKS_FILE.write_text(json.dumps(links))
def get_linked_team_id(chat_id): return load_team_links().get(str(chat_id))

MAIN_KB = InlineKeyboardMarkup([
    [InlineKeyboardButton("📋 GW Brief",         callback_data="brief")],
    [InlineKeyboardButton("👑 Captain Pick",     callback_data="captain")],
    [InlineKeyboardButton("🔄 Transfer Targets", callback_data="transfers")],
    [InlineKeyboardButton("🎯 Differentials",    callback_data="diffs")],
    [InlineKeyboardButton("🃏 Chip Advice",      callback_data="chips")],
])


async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    name = update.effective_user.first_name or "Manager"
    tid = get_linked_team_id(update.effective_chat.id)
    link_status = (
        f"✅ Team linked: *{tid}*\nUse `/myteam <new_id>` to change or `/unlinkteam` to remove.\n\n"
        if tid else
        "1) Link your FPL team: `/myteam <fpl_team_id>`\n"
        "2) Then run `/brief` for your personalised GW plan.\n\n"
    )
    await update.message.reply_text(
        f"Hey {name}! 👋 Welcome to *SportsClaw FPL Bot* 🦅\n\n"
        f"{link_status}"
        "Quick commands: `/brief` `/captain` `/transfers`\n"
        "Need help? `/help`\n\n"
        "Pick an option below:",
        parse_mode="Markdown",
        reply_markup=MAIN_KB,
    )

async def help_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "\n".join([
            "🛠 *SportsClaw Help*",
            "",
            "*Personalise first*",
            "• `/myteam 1234567` — link your FPL team ID",
            "• `/myteam` — view linked team",
            "• `/unlinkteam` — remove linked team",
            "",
            "*Core commands*",
            "• `/brief` — weekly summary + XI + differentials",
            "• `/captain` — best captain options",
            "• `/transfers` — best transfers for your team",
            "• `/transfers Salah 13.8` — replacement search",
            "• `/diffs` — top differentials",
            "• `/chips` — chip timing advice",
            "",
            "*Broadcasts*",
            "• `/subscribe` — weekly push brief",
            "• `/unsubscribe` — stop broadcasts",
            "",
            "Tip: find your team ID in your FPL URL: `/entry/<id>/...`",
        ]),
        parse_mode="Markdown",
        reply_markup=MAIN_KB,
    )

async def cmd_brief(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    tid = get_linked_team_id(update.effective_chat.id)
    await update.message.reply_text(build_brief(team_id=tid), parse_mode="Markdown", reply_markup=MAIN_KB)

async def cmd_captain(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    tid = get_linked_team_id(update.effective_chat.id)
    await update.message.reply_text(get_captain_picks(team_id=tid), parse_mode="Markdown", reply_markup=MAIN_KB)

async def cmd_transfers(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    tid = get_linked_team_id(update.effective_chat.id)
    args = ctx.args  # e.g. /transfers Salah 13.8
    if args:
        player_out = args[0]
        if len(args) > 1:
            try:
                budget = float(args[1])
            except ValueError:
                await update.message.reply_text("❌ Budget must be a number. Example: `/transfers Salah 13.8`", parse_mode="Markdown")
                return
        else:
            budget = None
        text = get_transfers(player_out=player_out, budget=budget, team_id=tid)
    else:
        text = get_transfers(team_id=tid)
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

async def myteam(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    cid = update.effective_chat.id
    links = load_team_links()
    args = ctx.args

    if not args:
        linked = links.get(str(cid))
        if linked:
            await update.message.reply_text(
                f"🔗 Your linked FPL team ID is *{linked}*.\nUse `/myteam <new_id>` to replace it.",
                parse_mode="Markdown",
            )
        else:
            await update.message.reply_text(
                "Link your FPL team: `/myteam <fpl_team_id>`\n"
                "Example: `/myteam 1234567`\n\n"
                "Find team ID by opening your FPL points page URL.",
                parse_mode="Markdown",
            )
        return

    try:
        team_id = int(args[0])
    except ValueError:
        await update.message.reply_text("❌ Team ID must be a number. Example: `/myteam 1234567`", parse_mode="Markdown")
        return

    links[str(cid)] = team_id
    save_team_links(links)
    await update.message.reply_text(
        f"✅ Linked! Team ID *{team_id}* saved.\nNow `/brief`, `/captain`, and `/transfers` are personalised.",
        parse_mode="Markdown",
    )


async def unlinkteam(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    cid = update.effective_chat.id
    links = load_team_links()
    if str(cid) in links:
        links.pop(str(cid), None)
        save_team_links(links)
        await update.message.reply_text("🧹 Removed your linked team. Commands are back to generic mode.")
    else:
        await update.message.reply_text("No linked team found for this chat.")


async def button(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    tid = get_linked_team_id(query.message.chat_id)
    try:
        if query.data == "brief":       text = build_brief(team_id=tid)
        elif query.data == "captain":   text = get_captain_picks(team_id=tid)
        elif query.data == "transfers": text = get_transfers(team_id=tid)
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
    app.add_handler(CommandHandler("help",        help_cmd))
    app.add_handler(CommandHandler("brief",       cmd_brief))
    app.add_handler(CommandHandler("captain",     cmd_captain))
    app.add_handler(CommandHandler("transfers",   cmd_transfers))
    app.add_handler(CommandHandler("diffs",       cmd_diffs))
    app.add_handler(CommandHandler("chips",       cmd_chips))
    app.add_handler(CommandHandler("myteam",      myteam))
    app.add_handler(CommandHandler("unlinkteam",  unlinkteam))
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
