"""Auto-broadcast Tuesday 16:00 UTC before GW deadline"""
import json, logging, pathlib, datetime
log=logging.getLogger("broadcaster")
SUBS_FILE=pathlib.Path(".subscribers.json")
def load_subs(): return json.loads(SUBS_FILE.read_text()) if SUBS_FILE.exists() else []
def save_subs(s): SUBS_FILE.write_text(json.dumps(s))

def schedule_broadcast(app):
    app.job_queue.run_daily(
        callback=_broadcast, time=datetime.time(hour=16,minute=0), days=(1,), name="gw_broadcast"
    )
    log.info("Broadcast scheduled — Tuesdays 16:00 UTC")

async def _broadcast(ctx):
    from fpl_logic import build_brief
    subs=load_subs()
    if not subs: return
    msg=build_brief()
    sent=0
    for cid in subs[:]:
        try:
            await ctx.bot.send_message(cid, msg, parse_mode="Markdown"); sent+=1
        except Exception as e:
            if "403" in str(e) or "blocked" in str(e).lower():
                save_subs([s for s in load_subs() if s!=cid])
    log.info(f"Broadcast sent {sent}/{len(subs)}")
