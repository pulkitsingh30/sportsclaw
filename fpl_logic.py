"""FPL brief logic — pure Python"""
from fpl_data import get_players, get_current_gw, get_team_snapshot

def _optimise(players, budget=100.0):
    targets = {"GK":2,"DEF":5,"MID":5,"FWD":3}
    active  = sorted([p for p in players if p["injury"]!="Injured" and p["proj_pts"]>0],
                     key=lambda p:-p["value_score"])
    squad,bl,pc,cc = [],[],{},{},
    squad,bl,pc,cc = [],budget,{},{}
    for p in active:
        if sum(pc.values())>=15: break
        if pc.get(p["pos"],0)>=targets[p["pos"]]: continue
        if cc.get(p["team"],0)>=3: continue
        if p["price"]>bl: continue
        squad.append(p); bl-=p["price"]
        pc[p["pos"]]=pc.get(p["pos"],0)+1
        cc[p["team"]]=cc.get(p["team"],0)+1
    return squad, round(bl,1)

def _team_ctx(team_id):
    if not team_id:
        return None, None
    return get_team_snapshot(team_id)


def build_brief(team_id=None):
    gw=get_current_gw(); players=get_players(); gw_id=gw["id"] if gw else "?"
    snapshot, err = _team_ctx(team_id)
    if snapshot:
        squad = snapshot["players"]
        bank = snapshot["bank"]
        budget_used = round(sum(p["price"] for p in squad), 1)
        header = f"🏆 *SportsClaw — GW{gw_id} Brief (Your Team)*"
        sub = f"👤 *{snapshot['manager_name']}* | 🛡 *{snapshot['entry_name']}*"
    else:
        squad, bl = _optimise(players)
        bank = bl
        budget_used = round(100 - bl, 1)
        header = f"🏆 *SportsClaw — GW{gw_id} Brief*"
        sub = "⚙️ Link your squad with _/myteam <fpl_team_id>_ for personalised advice."

    s = sorted(squad, key=lambda p:-p["proj_pts"])
    if len(s) < 2:
        return "⚠️ Not enough player data to build your GW brief."
    cap,vc = s[0],s[1]
    diffs = sorted([p for p in players if p["ownership_pct"]<15 and p["proj_pts"]>4 and p["injury"]=="Active"],
                   key=lambda p:-p["proj_pts_diff"])[:4]
    lines = [header, sub, "",
             f"👑 *Captain: {cap['player']}* (£{cap['price']}m) — {cap['proj_pts']}pts",
             f"⭐ *VC: {vc['player']}* (£{vc['price']}m) — {vc['proj_pts']}pts","",
             f"📋 *Starting XI (£{budget_used:.1f}m used, £{bank:.1f}m bank):*"]
    for i,p in enumerate(s[:11],1):
        flag = " 👑" if p["player"]==cap["player"] else " ⭐" if p["player"]==vc["player"] else ""
        lines.append(f"{i}. {p['player']} ({p['pos']}, £{p['price']}m) — {p['proj_pts']}pts{flag}")
    if diffs:
        lines+=["","🎯 *Differentials:*"]
        for p in diffs:
            lines.append(f"• {p['player']} — {p['proj_pts_diff']:.0f}pts diff @ {p['ownership_pct']:.1f}% owned")
    if err:
        lines += ["", f"ℹ️ {err}"]
    lines+=["","_/captain /transfers /diffs /chips for more_"]
    return "\n".join(lines)

def get_captain_picks(team_id=None):
    gw=get_current_gw(); players=get_players(); gw_id=gw["id"] if gw else "?"
    snapshot, _ = _team_ctx(team_id)
    source = snapshot["players"] if snapshot else players
    caps=sorted([p for p in source if p["injury"]=="Active" and p["proj_pts"]>0],
                key=lambda p:-p["proj_pts"])[:6]
    title = f"👑 *GW{gw_id} Captain Picks (Your Team)*" if snapshot else f"👑 *GW{gw_id} Captain Picks*"
    lines=[title,""]
    if not caps:
        return "⚠️ No active captain options found right now."
    for i,p in enumerate(caps,1):
        pre="👑 1st choice" if i==1 else "⭐ VC" if i==2 else f"{i}."
        lines.append(f"*{pre} — {p['player']}* (£{p['price']}m, {p['pos']})")
        lines.append(f"   Form: {p['form']} | xG+xA: {p['xG']+p['xA']:.2f} | {p['ownership_pct']:.1f}% owned\n")
    if not snapshot:
        lines.append("_Tip: link your team with /myteam <id> for personalised picks._")
    return "\n".join(lines)

def get_transfers(player_out=None, budget=None, team_id=None):
    gw=get_current_gw(); players=get_players(); gw_id=gw["id"] if gw else "?"
    snapshot, _ = _team_ctx(team_id)
    owned_ids = snapshot["player_ids"] if snapshot else set()

    if player_out:
        out=next((p for p in players if player_out.lower() in p["player"].lower()),None)
        if not out: return f"❌ *{player_out}* not found. Try surname only."
        b=budget or out["price"] + (snapshot["bank"] if snapshot else 0)
        t=sorted([p for p in players if p["pos"]==out["pos"] and p["price"]<=b
                  and p["price"]>=b*0.7 and p["injury"]=="Active" and p["player"]!=out["player"]
                  and p["id"] not in owned_ids],
                 key=lambda p:-p["proj_pts"])[:5]
        lines=[f"🔄 *GW{gw_id} Trade Finder*","",f"*OUT: {out['player']}* (£{out['price']}m)",""]
        if t:
            lines.append(f"*Best trade-ins (≤£{b:.1f}m):*")
            for i,p in enumerate(t,1):
                lines.append(f"{i}. *{p['player']}* — £{p['price']}m | {p['proj_pts']}pts | {p['ownership_pct']:.1f}% owned")
            lines+=["",f"💡 *Recommend: {t[0]['player']}*"]
        else: lines.append("No targets found — try relaxing budget.")
        return "\n".join(lines)
    if snapshot:
        weakest = sorted(snapshot["players"], key=lambda p:(p["injury"]=="Active", p["proj_pts"]))[:3]
        if not weakest:
            return "⚠️ Could not identify transfer candidates from your linked team."
        lines=[f"🔄 *GW{gw_id} Suggested Transfers (Your Team):*",""]
        for out in weakest:
            b = out["price"] + snapshot["bank"]
            targets = sorted([p for p in players if p["pos"]==out["pos"] and p["injury"]=="Active"
                              and p["price"]<=b and p["id"] not in owned_ids],
                             key=lambda p:-p["proj_pts"])[:2]
            if not targets:
                continue
            best = targets[0]
            gain = round(best["proj_pts"] - out["proj_pts"], 1)
            lines.append(f"• *OUT {out['player']}* (£{out['price']}m) → *IN {best['player']}* (£{best['price']}m) | Δ {gain:+.1f} pts")
        if len(lines) == 2:
            lines.append("No suitable swaps found with your current budget.")
        lines += ["", "_Use /transfers <surname> [budget] for a specific replacement search._"]
        return "\n".join(lines)

    t=sorted([p for p in players if p["injury"]=="Active" and p["price"]<9.0],
             key=lambda p:-p["value_score"])[:8]
    lines=[f"🔄 *GW{gw_id} Top Value Transfers:*",""]
    for i,p in enumerate(t,1):
        rise=f" 📈+£{p['price_rise']:.1f}m" if p["price_rise"]>0 else ""
        lines.append(f"{i}. *{p['player']}* ({p['pos']}, £{p['price']}m) — {p['proj_pts']}pts | {p['ownership_pct']:.1f}%{rise}")
    lines+=["","_/transfers Salah 13.8 for specific player_"]
    return "\n".join(lines)

def get_differentials():
    gw=get_current_gw(); players=get_players(); gw_id=gw["id"] if gw else "?"
    d=sorted([p for p in players if p["ownership_pct"]<15 and p["proj_pts"]>4 and p["injury"]=="Active"],
             key=lambda p:-p["proj_pts_diff"])[:8]
    lines=[f"🎯 *GW{gw_id} Differentials (<15% owned):*",""]
    for i,p in enumerate(d,1):
        rise=f" 📈+£{p['price_rise']:.1f}m" if p["price_rise"]>0 else ""
        lines.append(f"{i}. *{p['player']}* ({p['pos']}, £{p['price']}m)")
        lines.append(f"   {p['proj_pts_diff']:.1f} diff score | {p['ownership_pct']:.1f}% owned | xGI: {p['xG']+p['xA']:.2f}{rise}\n")
    return "\n".join(lines)

def get_chip_advice():
    gw=get_current_gw(); gw_id=int(gw["id"]) if gw else 29
    half=1 if gw_id<=19 else 2; left=(19-gw_id) if half==1 else (38-gw_id)
    return "\n".join([
        f"🃏 *Chip Advisor — GW{gw_id}*","",
        f"📅 Half {half} | {left} GWs left","✅ All 4 chips usable TWICE in 2025/26","",
        "*Key upcoming windows:*",
        "• BGW31 (21 Mar): ARS/WOL/MCI/CRY blank → 🔄 *Free Hit*",
        "• DGW33 (Apr): MCI+CRY double → 3️⃣ *Triple Captain*",
        "• BGW34 (Apr): FA Cup semis → 📊 *Bench Boost*","",
        "⏸ *Current: Hold all chips* — BGW31 is your next trigger",
    ])
