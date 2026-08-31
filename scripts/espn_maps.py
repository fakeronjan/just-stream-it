"""Static ID -> label maps for ESPN's fantasy football API.

These are stable across the whole ESPN fantasy platform (not
league-specific), verified against real Just Stream It data.
"""

POSITION_MAP = {
    1: "QB",
    2: "RB",
    3: "WR",
    4: "TE",
    5: "K",
    16: "D/ST",
}

LINEUP_SLOT_MAP = {
    0: "QB",
    2: "RB",
    4: "WR",
    6: "TE",
    16: "D/ST",
    17: "K",
    20: "BE",
    21: "IR",
    23: "FLEX",
}

PRO_TEAM_MAP = {
    0: "FA",
    1: "ATL",
    2: "BUF",
    3: "CHI",
    4: "CIN",
    5: "CLE",
    6: "DAL",
    7: "DEN",
    8: "DET",
    9: "GB",
    10: "TEN",
    11: "IND",
    12: "KC",
    13: "LV",
    14: "LAR",
    15: "MIA",
    16: "MIN",
    17: "NE",
    18: "NO",
    19: "NYG",
    20: "NYJ",
    21: "PHI",
    22: "ARI",
    23: "PIT",
    24: "LAC",
    25: "SF",
    26: "SEA",
    27: "TB",
    28: "WSH",
    29: "CAR",
    30: "JAX",
    33: "BAL",
    34: "HOU",
}

# Real NFL team nickname (as used in league_rules/owner_nfl_fandom.json) ->
# the abbrev used everywhere else in this codebase (PRO_TEAM_MAP values).
TEAM_NAME_TO_ABBREV = {
    "Bills": "BUF", "Dolphins": "MIA", "Patriots": "NE", "Jets": "NYJ",
    "Ravens": "BAL", "Bengals": "CIN", "Browns": "CLE", "Steelers": "PIT",
    "Texans": "HOU", "Colts": "IND", "Jaguars": "JAX", "Titans": "TEN",
    "Broncos": "DEN", "Chiefs": "KC", "Raiders": "LV", "Chargers": "LAC",
    "Cowboys": "DAL", "Giants": "NYG", "Eagles": "PHI", "Commanders": "WSH",
    "Bears": "CHI", "Lions": "DET", "Packers": "GB", "Vikings": "MIN",
    "Falcons": "ATL", "Panthers": "CAR", "Saints": "NO", "Buccaneers": "TB",
    "Cardinals": "ARI", "Rams": "LAR", "49ers": "SF", "Seahawks": "SEA",
}

# Real NFL divisions, by team nickname - stable structure, not expected to
# change season to season. Used to find an owner's real-life division
# rivals for the weekly recap's fandom-narrative bits.
NFL_DIVISIONS = {
    "AFC East": ["Bills", "Dolphins", "Patriots", "Jets"],
    "AFC North": ["Ravens", "Bengals", "Browns", "Steelers"],
    "AFC South": ["Texans", "Colts", "Jaguars", "Titans"],
    "AFC West": ["Broncos", "Chiefs", "Raiders", "Chargers"],
    "NFC East": ["Cowboys", "Giants", "Eagles", "Commanders"],
    "NFC North": ["Bears", "Lions", "Packers", "Vikings"],
    "NFC South": ["Falcons", "Panthers", "Saints", "Buccaneers"],
    "NFC West": ["Cardinals", "Rams", "49ers", "Seahawks"],
}


def division_rival_abbrevs(team_name):
    """A team's 3 real division rivals, as abbrevs - e.g. "Bengals" ->
    {"BAL", "CLE", "PIT"}. Returns an empty set for an unrecognized name
    (e.g. an owner's fandom not yet confirmed, still null in the JSON)."""
    for division_teams in NFL_DIVISIONS.values():
        if team_name in division_teams:
            return {TEAM_NAME_TO_ABBREV[t] for t in division_teams if t != team_name}
    return set()
