"""FPL data cache — public API, no auth needed"""
import requests, logging

log   = logging.getLogger("fpl_data")
BASE  = "https://fantasy.premierleague.com/api"
_cache = {"players": [], "teams": [], "events": [], "fixtures": [], "current_gw": None}


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
        _cache  = {"players": players, "teams": teams, "events": events,
                   "fixtures": fix, "current_gw": current}
        log.info(f"Cache updated — GW{current['id'] if current else '?'} | {len(players)} players")
    except Exception as e:
        log.error(f"Cache refresh failed: {e}")


def _norm(p, teams):
    team  = next((t for t in teams if t["id"] == p["team"]), {})
    pos   = ["GK", "DEF", "MID", "FWD"][p.get("element_type", 1) - 1]
    price = p.get("now_cost", 0) / 10
    form  = float(p.get("form", 0) or 0)
    ppg   = float(p.get("points_per_game", 0) or 0)
    ict   = float(p.get("ict_index", 0) or 0)
    own   = float(p.get("selected_by_percent", 0) or 0)

    # Normalise cumulative season xG/xA to per-game rate
    mins  = p.get("minutes", 1) or 1
    games = max(mins / 90, 1)
    xg    = float(p.get("expected_goals", 0) or 0) / games
    xa    = float(p.get("expected_assists", 0) or 0) / games

    cop   = p.get("chance_of_playing_this_round")
    inj   = "Injured" if cop == 0 else "Managed" if cop and cop < 75 else "Active"

    base  = form * 0.65 + ppg * 0.35
    ict_m = 1.12 if ict > 80 else 1.06 if ict > 60 else 1.02 if ict > 40 else 1.0
    xgi_m = 1.08 if (xg + xa) > 0.5 else 1.0
    inj_m = 0 if inj == "Injured" else 0.75 if inj == "Managed" else 1.0
    proj  = round(base * ict_m * xgi_m * inj_m, 1)

    dm    = 1.25 if own < 2 else 1.20 if own < 5 else 1.10 if own < 10 else 1.05 if own < 15 else 1.0

    return {
        "id":           p["id"],
        "player":       f"{p.get('first_name', '')} {p.get('second_name', '')}".strip(),
        "team":         team.get("short_name", ""),
        "pos":          pos,
        "price":        price,
        "form":         form,
        "ppg":          ppg,
        "ict":          ict,
        "ownership_pct": own,
        "xG":           round(xg, 3),
        "xA":           round(xa, 3),
        "injury":       inj,
        "price_rise":   p.get("cost_change_start", 0) / 10,   # fixed: was cost_start
        "proj_pts":     proj,
        "proj_pts_diff": round(proj * dm, 1),
        "value_score":  round(proj / price, 2) if price > 0 else 0,
        "news":         p.get("news", ""),
        "total_points": p.get("total_points", 0),
    }


def get_players():    return _cache["players"]
def get_current_gw(): return _cache["current_gw"]
def get_fixtures(gw=None):
    return [f for f in _cache["fixtures"] if f.get("event") == gw] if gw else _cache["fixtures"]


def get_team_snapshot(team_id, gw=None):
    """Fetch a manager's current squad snapshot with bank and names."""
    players = get_players()
    if not players:
        refresh_cache()
        players = get_players()
    if not players:
        return None, "FPL player cache is empty. Try again soon."

    current = get_current_gw()
    gw_id = gw or (current.get("id") if current else None)
    if not gw_id:
        return None, "Unable to determine current gameweek."

    try:
        entry = requests.get(f"{BASE}/entry/{int(team_id)}/", timeout=15).json()
        picks = requests.get(f"{BASE}/entry/{int(team_id)}/event/{int(gw_id)}/picks/", timeout=15).json()
    except Exception as e:
        log.error("Team fetch failed for %s: %s", team_id, e)
        return None, "Could not load that FPL team right now."

    if isinstance(entry, dict) and entry.get("detail"):
        return None, f"FPL team not found: {entry.get('detail')}"
    if isinstance(picks, dict) and picks.get("detail"):
        return None, f"Could not load picks: {picks.get('detail')}"

    picks_list = picks.get("picks", []) if isinstance(picks, dict) else []
    if not picks_list:
        return None, "No picks found for this team in the current GW."

    by_id = {p["id"]: p for p in players}
    owned = []
    for pick in picks_list:
        pid = pick.get("element")
        player = by_id.get(pid)
        if not player:
            continue
        owned.append({**player, "multiplier": pick.get("multiplier", 1), "is_captain": pick.get("is_captain", False)})

    history = picks.get("entry_history", {}) if isinstance(picks, dict) else {}
    bank = history.get("bank", 0) / 10

    snapshot = {
        "team_id": int(team_id),
        "manager_name": (entry or {}).get("player_name", ""),
        "entry_name": (entry or {}).get("name", ""),
        "players": owned,
        "player_ids": {p["id"] for p in owned},
        "bank": bank,
        "gw": int(gw_id),
    }
    return snapshot, None
