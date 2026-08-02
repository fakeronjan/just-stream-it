"""Fetch real NFL schedules/scores for a season, keyed by week and team -
lets the site show "who did this player's NFL team play, and what was the
final score" alongside a big fantasy week. Pure ESPN's public (no-auth)
scoreboard API, unrelated to the fantasy API the rest of this pipeline uses.

Assumes fantasy week N == NFL week N (true for weeks 1-17 in a normal
season - this league's regular season + playoffs never runs past week 17).
"""

import json
import time
from pathlib import Path

import requests

DOCS_DATA = Path(__file__).parent.parent / "docs" / "data"
SCOREBOARD_URL = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"


def fetch_week(season, week):
    resp = requests.get(
        SCOREBOARD_URL,
        params={"seasontype": 2, "week": week, "dates": season},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def main(season, num_weeks=17):
    schedule = {}
    for week in range(1, num_weeks + 1):
        data = fetch_week(season, week)
        week_map = {}
        for event in data.get("events", []):
            comp = event["competitions"][0]
            teams = comp["competitors"]
            if len(teams) != 2:
                continue
            a, b = teams
            a_abbr, b_abbr = a["team"]["abbreviation"], b["team"]["abbreviation"]
            a_score, b_score = float(a.get("score", 0) or 0), float(b.get("score", 0) or 0)
            week_map[a_abbr] = {
                "opponent": b_abbr,
                "home": a.get("homeAway") == "home",
                "team_score": a_score,
                "opponent_score": b_score,
            }
            week_map[b_abbr] = {
                "opponent": a_abbr,
                "home": b.get("homeAway") == "home",
                "team_score": b_score,
                "opponent_score": a_score,
            }
        schedule[week] = week_map
        print(f"  week {week}: {len(week_map)} teams")
        time.sleep(0.2)

    out_path = DOCS_DATA / str(season) / "nfl_schedule.json"
    out_path.write_text(json.dumps(schedule, indent=2))
    print(f"Wrote nfl_schedule.json for {season}")


if __name__ == "__main__":
    import sys

    season = int(sys.argv[1]) if len(sys.argv) > 1 else 2025
    main(season)
