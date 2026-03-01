# SportsClaw

Autonomous multi-sport fantasy agent — FPL, AFL, NRL, Cricket.

## Setup
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # paste your token
python3 bot.py
```

## Commands
/start /help /brief /captain /transfers /diffs /chips /myteam /unlinkteam /subscribe /unsubscribe

### Link your FPL team for personalised advice
- `/myteam <fpl_team_id>`
- Example: `/myteam 1234567`
- To remove link: `/unlinkteam`
