"""Pull league data from ESPN and bake it into docs/data/ for the static site.

Run: python scripts/generate_data.py
"""

import datetime
import json
from pathlib import Path

import io

import requests
from PIL import Image

from config import CURRENT_SEASON, LEAGUE_ID, LEAGUE_NAME, SEASONS
from espn_client import _load_credentials, fetch_league, fetch_players_by_id
from espn_maps import LINEUP_SLOT_MAP, POSITION_MAP, PRO_TEAM_MAP

DOCS_DATA = Path(__file__).parent.parent / "docs" / "data"
LOGOS_DIR = Path(__file__).parent.parent / "docs" / "logos"

VIEWS = ["mTeam", "mRoster", "mSettings", "mMatchup", "mDraftDetail"]

EXT_BY_CONTENT_TYPE = {
    "image/jpg": ".jpg",
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/svg+xml": ".svg",
}


LOGO_MAX_DIM = 160  # displayed at 28-56px; this covers retina with room to spare


def download_logo(team_id, url, season):
    """Custom-uploaded team logos live behind ESPN's auth wall (the default
    stock logos on g.espncdn.com don't, but there's no way to tell which
    from the URL alone) - so hotlinking them breaks for site visitors who
    aren't authenticated. Download with our own credentials, downscale
    (source images can be 400KB+ for a thumbnail shown at 28-56px), and
    host locally.

    Stored per-season (docs/logos/{season}/{team_id}.ext), NOT a single
    shared file per team_id - team_id is just this season's roster slot,
    and owners frequently rebrand (new name/logo) between seasons. A shared
    file would silently overwrite prior seasons' identity every re-pull.
    """
    s2, swid = _load_credentials()
    resp = requests.get(url, cookies={"espn_s2": s2, "SWID": swid}, timeout=30)
    resp.raise_for_status()
    content_type = resp.headers.get("content-type", "").split(";")[0].strip()
    ext = EXT_BY_CONTENT_TYPE.get(content_type, ".png")
    season_dir = LOGOS_DIR / str(season)
    season_dir.mkdir(parents=True, exist_ok=True)
    path = season_dir / f"{team_id}{ext}"

    if ext == ".svg":
        path.write_bytes(resp.content)
    else:
        img = Image.open(io.BytesIO(resp.content))
        img.thumbnail((LOGO_MAX_DIM, LOGO_MAX_DIM))
        if ext == ".jpg":
            img.convert("RGB").save(path, "JPEG", quality=85)
        else:
            img.save(path, "PNG", optimize=True)

    return f"logos/{season}/{team_id}{ext}"


def build_teams(league, season):
    # NOTE for future scripts: team_id is a per-season ESPN roster SLOT, not
    # a stable franchise identity - it's just "whoever holds this draft
    # position this season." The thing that actually persists across
    # seasons is the MANAGER (owners[], i.e. ESPN member displayName). If a
    # slot's ownership ever changes hands, don't attribute the outgoing
    # owner's history (team name, logo, keeper decisions) to the new one
    # based on team_id alone - compare by owners[] for cross-season identity.
    members = {m["id"]: m["displayName"] for m in league.get("members", [])}
    teams = []
    for t in league["teams"]:
        record = t["record"]["overall"]
        owners = [members.get(o, o) for o in t.get("owners", [])]
        logo_url = t.get("logo")
        teams.append(
            {
                "id": t["id"],
                "name": t["name"],
                "abbrev": t["abbrev"],
                "logo": download_logo(t["id"], logo_url, season) if logo_url else None,
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

        (season_dir / "teams.json").write_text(json.dumps(build_teams(league, season), indent=2))
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
