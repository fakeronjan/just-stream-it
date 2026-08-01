"""Thin client for ESPN's undocumented Fantasy Football API.

Auth: private leagues require the espn_s2 + SWID cookies from a logged-in
browser session. Locally these come from secrets.json (gitignored); in
GitHub Actions they come from the ESPN_S2 / ESPN_SWID repo secrets.

Note: requests must go to lm-api-reads.fantasy.espn.com, not
fantasy.espn.com - the latter 302-redirects to the site regardless of
cookie validity.
"""

import json
import os
from pathlib import Path

import requests

BASE_URL = "https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl"
SECRETS_PATH = Path(__file__).parent.parent / "secrets.json"


def _load_credentials():
    s2 = os.environ.get("ESPN_S2")
    swid = os.environ.get("ESPN_SWID")
    if s2 and swid:
        return s2, swid
    if SECRETS_PATH.exists():
        data = json.loads(SECRETS_PATH.read_text())
        return data["espn_s2"], data["swid"]
    raise RuntimeError(
        "No ESPN credentials found. Set ESPN_S2 / ESPN_SWID env vars, "
        f"or create {SECRETS_PATH} with {{'espn_s2': ..., 'swid': ...}}."
    )


def fetch_league(league_id, season, views, current_season):
    """Fetch league data for a season, merging the given API `views`."""
    s2, swid = _load_credentials()
    cookies = {"espn_s2": s2, "SWID": swid}
    params = [("view", v) for v in views]

    if season == current_season:
        url = f"{BASE_URL}/seasons/{season}/segments/0/leagues/{league_id}"
    else:
        url = f"{BASE_URL}/leagueHistory/{league_id}"
        params.append(("seasonId", season))

    resp = requests.get(url, cookies=cookies, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    if isinstance(data, list):
        data = data[0]
    return data


def fetch_players_by_id(league_id, season, player_ids):
    """Look up name/position/pro-team for specific player IDs (e.g. to
    resolve draft picks for players no longer on any current roster).
    """
    if not player_ids:
        return {}
    s2, swid = _load_credentials()
    cookies = {"espn_s2": s2, "SWID": swid}
    url = f"{BASE_URL}/seasons/{season}/segments/0/leagues/{league_id}"
    headers = {
        "x-fantasy-filter": json.dumps({"players": {"filterIds": {"value": player_ids}}})
    }
    resp = requests.get(
        url, cookies=cookies, params=[("view", "kona_player_info")], headers=headers, timeout=30
    )
    resp.raise_for_status()
    players = resp.json().get("players", [])
    return {p["id"]: p["player"] for p in players}
