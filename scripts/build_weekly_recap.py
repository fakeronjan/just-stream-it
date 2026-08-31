"""Weekly in-season recap for the 2026+ stats page - a matchup-centric
narrative, not a per-category one.

The structure is built around the week's real matchups (one line per
game) rather than a handful of isolated "storyline" categories, because
that's the only way to guarantee every team gets covered without forcing
content that isn't there: 6 matchups = all 12 teams touched, every week,
with zero fabrication - a quiet matchup just stays a bare scoreline.
Bonus storylines (upsets, the week's best performance, real-NFL-fandom
callouts) are attached as extra clauses onto whichever matchup they
actually happened in, rather than floating as disconnected sentences.

This whole design was worked out and stress-tested against the full real
2025 season before being written as real code - a few calibration
decisions came directly out of that:

  - Upset detection uses the standings ENTERING that week, not final
    season rank (which doesn't exist yet mid-season) - see
    standings_through_week().
  - "Started a division rival" only fires ONCE per (owner, player), the
    first week it's true - checked against real data, a handful of
    owners roster a rival's player ALL SEASON, so re-announcing it every
    week was the single most repetitive thing in an early draft of this.
    It's a one-time reveal, not a weekly fact-check.
  - When multiple items of the same clause type land in one matchup
    (e.g. 3 new rival reveals for the same owner in week 1, when
    everything is "new"), they're grouped into ONE sentence with proper
    list grammar, not N repeats of the same clause label.

Run after generate_data.py and build_season_analytics.py (needs
matchups.json, weekly_boxscores.json, teams.json, nfl_schedule.json for
the target season) and league_rules/owner_nfl_fandom.json.
"""

import json
from pathlib import Path

from espn_maps import division_rival_abbrevs
from owner_util import owner_first_name

DOCS_DATA = Path(__file__).parent.parent / "docs" / "data"
LEAGUE_RULES = Path(__file__).parent.parent / "league_rules"

NAIL_BITER_MARGIN = 3
BLOWOUT_MARGIN = 40
UPSET_MIN_RANK_SWING = 5
DIVISION_RIVAL_MIN_POINTS = 25


def join_list(items):
    """Proper English list grammar: "A", "A and B", "A, B, and C" - so a
    matchup with multiple same-type clauses reads as one sentence, not a
    repeated label per item."""
    items = list(items)
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return ", ".join(items[:-1]) + f", and {items[-1]}"


class RecapContext:
    """Everything build_week_recap() needs, loaded once per season rather
    than per week. revealed_rostered_rivals persists across weeks WITHIN
    a run (a fresh instance each `main()` call) - that's what makes the
    one-time-reveal logic work: it's a deterministic replay of the season
    so far, not externally persisted state.
    """

    def __init__(self, season):
        self.teams = {t["id"]: t for t in _load(season, "teams.json")}
        self.matchups = _load(season, "matchups.json")
        self.boxscores = _load(season, "weekly_boxscores.json")
        fandom = json.loads((LEAGUE_RULES / "owner_nfl_fandom.json").read_text())
        self.fandom = {k: v for k, v in fandom.items() if not k.startswith("_")}
        self.rival_abbrevs_by_owner = {
            owner: division_rival_abbrevs(fan_team)
            for owner, fan_team in self.fandom.items()
            if fan_team
        }
        self.owner_by_team_id = {tid: owner_first_name(t["owners"]) for tid, t in self.teams.items()}
        self.revealed_rostered_rivals = set()

    def team_short(self, team_id):
        t = self.teams[team_id]
        return f"{t['name'].strip()} ({owner_first_name(t['owners'])})"


def _load(season, name):
    return json.loads((DOCS_DATA / str(season) / name).read_text())


def standings_through_week(ctx, through_week):
    """Regular-season-only rank as of ENTERING through_week + 1 (i.e. games
    through `through_week` count) - deliberately not the real compute_standings
    in build_season_moments.py, which traces the completed playoff bracket
    and only makes sense once a season is over. Same tiebreak, though:
    -wins, -points_for.
    """
    wins = {tid: 0 for tid in ctx.teams}
    pf = {tid: 0.0 for tid in ctx.teams}
    for m in ctx.matchups:
        if m["is_playoffs"] or m["week"] > through_week:
            continue
        pf[m["home_team_id"]] += m["home_score"]
        pf[m["away_team_id"]] += m["away_score"]
        if m["winner"] == "HOME":
            wins[m["home_team_id"]] += 1
        elif m["winner"] == "AWAY":
            wins[m["away_team_id"]] += 1
    ranked = sorted(ctx.teams, key=lambda tid: (-wins[tid], -pf[tid]))
    return {tid: i + 1 for i, tid in enumerate(ranked)}


def _week_stud(week_box):
    """The single highest-scoring started player league-wide this week -
    attached to whichever matchup that player's team is in."""
    stud = None
    for team_id_str, players in week_box.items():
        for p in players:
            if p["started"] and (stud is None or p["points"] > stud["points"]):
                stud = {**p, "team_id": int(team_id_str)}
    return stud


def _matchup_clauses(ctx, winner_id, loser_id, entering_rank, stud, week_box):
    clauses = []

    if entering_rank:
        upset_size = entering_rank[winner_id] - entering_rank[loser_id]
        if upset_size >= UPSET_MIN_RANK_SWING:
            clauses.append(
                f"upset alert: {ctx.team_short(winner_id)} came in ranked #{entering_rank[winner_id]} "
                f"to {ctx.team_short(loser_id)}'s #{entering_rank[loser_id]}"
            )

    if stud and stud["team_id"] in (winner_id, loser_id):
        clauses.append(f"league-best performance: {stud['name']} ({stud['points']:.1f} pts)")

    # Fandom: a real division rival torched this owner THIS week.
    for team_id in (winner_id, loser_id):
        opp_id = loser_id if team_id == winner_id else winner_id
        owner = ctx.owner_by_team_id[team_id]
        rivals = ctx.rival_abbrevs_by_owner.get(owner)
        if not rivals:
            continue
        hits = [
            f"{p['name']} ({p['pro_team']}, {p['points']:.1f} pts)"
            for p in week_box.get(str(opp_id), [])
            if p["started"] and p["pro_team"] in rivals and p["points"] >= DIVISION_RIVAL_MIN_POINTS
        ]
        if hits:
            clauses.append(f"division-rival salt: {join_list(hits)} went off on {owner}, a {ctx.fandom[owner]} fan")

    # Fandom: owner is rostering a division rival - ONE-TIME reveal per
    # (owner, player), grouped if multiple are new in the same week.
    for team_id in (winner_id, loser_id):
        owner = ctx.owner_by_team_id[team_id]
        rivals = ctx.rival_abbrevs_by_owner.get(owner)
        if not rivals:
            continue
        new_reveals = []
        for p in week_box.get(str(team_id), []):
            if not (p["started"] and p["pro_team"] in rivals and p["position"] != "D/ST"):
                continue
            key = (owner, p["name"])
            if key in ctx.revealed_rostered_rivals:
                continue
            ctx.revealed_rostered_rivals.add(key)
            new_reveals.append(f"{p['name']} ({p['pro_team']})")
        if new_reveals:
            clauses.append(
                f"plot twist: {owner}, a {ctx.fandom[owner]} fan, has been starting "
                f"{join_list(new_reveals)} all along"
            )

    return clauses


def build_week_recap(ctx, week):
    """One line per real matchup that week - always full team coverage,
    with bonus clauses attached only where something real qualifies."""
    week_matchups = [m for m in ctx.matchups if m["week"] == week and not m["is_playoffs"]]
    if not week_matchups:
        return []
    entering_rank = standings_through_week(ctx, week - 1) if week > 1 else None
    week_box = ctx.boxscores[str(week)]
    stud = _week_stud(week_box)

    lines = []
    for m in week_matchups:
        if m["winner"] not in ("HOME", "AWAY"):
            continue
        winner_id = m["home_team_id"] if m["winner"] == "HOME" else m["away_team_id"]
        loser_id = m["away_team_id"] if m["winner"] == "HOME" else m["home_team_id"]
        wscore = m["home_score"] if m["winner"] == "HOME" else m["away_score"]
        lscore = m["away_score"] if m["winner"] == "HOME" else m["home_score"]
        margin = abs(wscore - lscore)

        text = f"{ctx.team_short(winner_id)} beat {ctx.team_short(loser_id)} {wscore:.1f}-{lscore:.1f}"
        if margin <= NAIL_BITER_MARGIN:
            text += " (nail-biter)"
        elif margin >= BLOWOUT_MARGIN:
            text += " (blowout)"

        clauses = _matchup_clauses(ctx, winner_id, loser_id, entering_rank, stud, week_box)
        if clauses:
            text += " - " + "; ".join(clauses)

        lines.append(
            {
                "winner_team_id": winner_id,
                "loser_team_id": loser_id,
                "winner_score": wscore,
                "loser_score": lscore,
                "text": text,
            }
        )
    return lines


def main(season):
    ctx = RecapContext(season)
    played_weeks = sorted({m["week"] for m in ctx.matchups if not m["is_playoffs"]})

    weekly_recap = []
    for week in played_weeks:
        lines = build_week_recap(ctx, week)
        if lines:
            weekly_recap.append({"week": week, "matchups": lines})

    out_path = DOCS_DATA / str(season) / "weekly_recap.json"
    out_path.write_text(json.dumps(weekly_recap, indent=2))
    print(f"Wrote weekly_recap.json ({len(weekly_recap)} weeks, season {season})")


if __name__ == "__main__":
    import sys

    main(int(sys.argv[1]) if len(sys.argv) > 1 else 2026)
