"""FPL data cache — public API, no auth needed"""
import requests, logging, threading

log   = logging.getLogger("fpl_data")
BASE  = "https://fantasy.premierleague.com/api"
_cache = {"players":[], "teams":[], "events":[], "fixtures":[], "current_gw":None}

def refresh_cache():
    global _cache
    try:
        log.info("Refreshing FPL data...")
        boot = requests.get(f"{BASE}/bootstrap-static/", timeout=15).json()
        fix  = requests.get(f"{BASE}/fixtures/", timeout=15).json()
        teams   = boot.get("teams", [])
        events  = boot.get("events", [])
        current = next((e for e in events if e.get("is_current")),
                  next((e for e in events if e.get("is_next")), None))
        players = [_norm(p, teams) for p in boot.get("elements", [])]
        _cache  = {"players":players,"teams":teams,"events":events,"fixtures":fix,"current_gw":current}
        log.info(f"Cache updated — GW{current['id'] if current else '?'} | {len(players)} players")
    except Exception as e:
        log.error(f"Cache refresh failed: {e}")

def _norm(p, teams):
    team  = next((t for t in teams if t["id"]==p["team"]), {})
    pos   = ["GK","DEF","MID","FWD"][p.get("element_type",1)-1]
    price = p.get("now_cost",0)/10
    form  = float(p.get("form",0))
    ppg   = float(p.get("points_per_game",0))
    ict   = float(p.get("ict_index",0))
    own   = float(p.get("selected_by_percent",0))
    xg    = float(p.get("expected_goals",0))
    xa    = float(p.get("expected_assists",0))
    cop   = p.get("chance_of_playing_this_round")
    inj   = "Injured" if cop==0 else "Managed" if cop and cop<75 else "Active"
    base  = form*0.65 + ppg*0.35
    ict_m = 1.12 if ict>80 else 1.06 if ict>60 else 1.02 if ict>40 else 1.0
    xgi_m = 1.08 if (xg+xa)>0.5 else 1.0
    inj_m = 0 if inj=="Injured" else 0.75 if inj=="Managed" else 1.0
    proj  = round(base*ict_m*xgi_m*inj_m, 1)
    dm    = 1.25 if own<2 else 1.20 if own<5 else 1.10 if own<10 else 1.05 if own<15 else 1.0
    return {
        "id":p["id"], "player":f"{p.get('first_name','')} {p.get('second_name','')}".strip(),
        "team":team.get("short_name",""), "pos":pos, "price":price,
        "form":form, "ppg":ppg, "ict":ict, "ownership_pct":own,
        "xG":xg, "xA":xa, "injury":inj,
        "price_rise":(p.get("now_cost",0)-p.get("cost_start",0))/10,
        "proj_pts":proj, "proj_pts_diff":round(proj*dm,1),
        "value_score":round(proj/price,2) if price>0 else 0,
        "news":p.get("news",""), "total_points":p.get("total_points",0),
    }

def get_players():    return _cache["players"]
def get_current_gw(): return _cache["current_gw"]
def get_fixtures(gw=None):
    return [f for f in _cache["fixtures"] if f.get("event")==gw] if gw else _cache["fixtures"]
