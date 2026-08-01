"""Pull league data from ESPN and bake it into docs/data/ for the static site.

Run: python scripts/generate_data.py
"""

import datetime
import json
from pathlib import Path

from config import CURRENT_SEASON, LEAGUE_ID, LEAGUE_NAME, SEASONS
from espn_client import fetch_league, fetch_players_by_id
from espn_maps import LINEUP_SLOT_MAP, POSITION_MAP, PRO_TEAM_MAP

DOCS_DATA = Path(__file__).parent.parent / "docs" / "data"

VIEWS = ["mTeam", "mRoster", "mSettings", "mMatchup", "mDraftDetail"]


def build_teams(league):
    members = {m["id"]: m["displayName"] for m in league.get("members", [])}
    teams = []
    for t in league["teams"]:
        record = t["record"]["overall"]
        owners = [members.get(o, o) for o in t.get("owners", [])]
        teams.append(
            {
                "id": t["id"],
                "name": t["name"],
                "abbrev": t["abbrev"],
                "logo": t.get("logo"),
                "owners": owners,
                "wins": record["wins"],
                "losses": record["losses"],
                "ties": record["ties"],
                "points_for": record["pointsFor"],
                "points_against": record["pointsAgainst"],
                "playoff_seed": t.get("playoffSeed"),
                "final_rank": t.get("rankCalculatedFinal"),
            }
        )
    return teams


def build_matchups(league):
    regular_season_weeks = league["settings"]["scheduleSettings"]["matchupPeriodCount"]
    matchups = []
    for m in league["schedule"]:
        if "home" not in m or "away" not in m:
            continue  # bye week
        matchups.append(
            {
                "week": m["matchupPeriodId"],
                "is_playoffs": m["matchupPeriodId"] > regular_season_weeks,
                "home_team_id": m["home"].get("teamId"),
                "home_score": m["home"].get("totalPoints", 0),
                "away_team_id": m["away"].get("teamId"),
                "away_score": m["away"].get("totalPoints", 0),
                "winner": m.get("winner"),
            }
        )
    return matchups


def build_rosters(league):
    rosters = {}
    for t in league["teams"]:
        entries = t.get("roster", {}).get("entries", [])
        players = []
        for e in entries:
            p = e["playerPoolEntry"]["player"]
            players.append(
                {
                    "player_id": e["playerId"],
                    "name": p["fullName"],
                    "position": POSITION_MAP.get(p["defaultPositionId"], p["defaultPositionId"]),
                    "pro_team": PRO_TEAM_MAP.get(p["proTeamId"], p["proTeamId"]),
                    "lineup_slot": LINEUP_SLOT_MAP.get(e["lineupSlotId"], e["lineupSlotId"]),
                    "keeper_value": e["playerPoolEntry"].get("keeperValue"),
                    "injury_status": e.get("injuryStatus"),
                    "acquisition_type": e.get("acquisitionType"),
                }
            )
        rosters[t["id"]] = players
    return rosters


def build_draft(league, season):
    picks = league["draftDetail"]["picks"]

    # Resolve player names from current rosters first (no extra API call
    # needed), then batch-fetch anything still missing (players since
    # dropped/cut who won't appear on any current roster).
    known = {}
    for t in league["teams"]:
        for e in t.get("roster", {}).get("entries", []):
            known[e["playerId"]] = e["playerPoolEntry"]["player"]

    missing_ids = sorted({p["playerId"] for p in picks if p["playerId"] != -1} - known.keys())
    known.update(fetch_players_by_id(LEAGUE_ID, season, missing_ids))

    draft = []
    for p in picks:
        player = known.get(p["playerId"])
        draft.append(
            {
                "round": p["roundId"],
                "round_pick": p["roundPickNumber"],
                "overall_pick": p["overallPickNumber"],
                "team_id": p["teamId"],
                "player_id": p["playerId"] if p["playerId"] != -1 else None,
                "player_name": player["fullName"] if player else None,
                "position": POSITION_MAP.get(player["defaultPositionId"], None) if player else None,
                "pro_team": PRO_TEAM_MAP.get(player["proTeamId"], None) if player else None,
                "keeper": p["keeper"],
                "reserved_for_keeper": p.get("reservedForKeeper", False),
            }
        )
    return draft


def main():
    DOCS_DATA.mkdir(parents=True, exist_ok=True)

    for season in SEASONS:
        league = fetch_league(LEAGUE_ID, season, VIEWS, CURRENT_SEASON)

        season_dir = DOCS_DATA / str(season)
        season_dir.mkdir(exist_ok=True)

        (season_dir / "teams.json").write_text(json.dumps(build_teams(league), indent=2))
        (season_dir / "matchups.json").write_text(json.dumps(build_matchups(league), indent=2))
        (season_dir / "rosters.json").write_text(json.dumps(build_rosters(league), indent=2))
        (season_dir / "draft.json").write_text(json.dumps(build_draft(league, season), indent=2))

        print(f"Wrote data for {season}")

    meta = {
        "league_id": LEAGUE_ID,
        "league_name": LEAGUE_NAME,
        "current_season": CURRENT_SEASON,
        "seasons": SEASONS,
        "last_updated": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    (DOCS_DATA / "meta.json").write_text(json.dumps(meta, indent=2))
    print("Wrote meta.json")


if __name__ == "__main__":
    main()
