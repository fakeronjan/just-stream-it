"""Weekly in-season recap for the 2026+ stats page.

Two-tier structure, mirroring how a real sports section works: a handful
of FEATURES up top (Game of the Week, Stud of the Week, upset alerts,
real-NFL-fandom callouts - each its own standalone item with real
narrative prose) and a compact BRIEFS list below (all 6 matchups as
plain scorelines, guaranteeing every team gets covered even when nothing
noteworthy happened to them that week).

This replaces an earlier "matchup-centric" version that attached bonus
storylines as extra clauses onto whichever scoreline they happened in.
That version also guaranteed full coverage, but Ronjan's read after
seeing it rendered was that gluing "Stud of the Week" onto a random
scoreline buried the fun stuff and made the whole page read clinical -
correct: a real paper doesn't fold the box scores and the feature
write-up into the same sentence. Features and briefs are now separate,
features get real narrative phrasing (with template variety, seeded per
week so a given week's text is stable across reruns), and briefs stay
genuinely minimal.

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
  - When multiple items of the same feature type happen in one week
    (e.g. 3 new rival reveals for the same owner in week 1, when
    everything is "new"), they're grouped into ONE item with proper
    list grammar, not N separate items.
  - Looking Ahead only ever uses information available BEFORE next
    week's games are played (records/rank entering, rematch flag) -
    even though testing this against a real past season means the
    actual outcome is sitting right there in the data, using it would
    make the preview meaningless once this runs for real in 2026, where
    next week hasn't happened yet. Never peek.

Run after generate_data.py and build_season_analytics.py (needs
matchups.json, weekly_boxscores.json, teams.json, nfl_schedule.json for
the target season) and league_rules/owner_nfl_fandom.json.
"""

import json
import random
from pathlib import Path

from espn_maps import division_rival_abbrevs
from owner_util import owner_first_name

DOCS_DATA = Path(__file__).parent.parent / "docs" / "data"
LEAGUE_RULES = Path(__file__).parent.parent / "league_rules"

BLOWOUT_MARGIN = 40
UPSET_MIN_RANK_SWING = 5
DIVISION_RIVAL_MIN_POINTS = 25
PLAYOFF_SPOTS = 6

CLOSE_GAME_TEMPLATES = [
    "This week's nail-biter: {winner} squeaked past {loser} {wscore}-{lscore}, a margin of just {margin}.",
    "{winner} survived a scare from {loser}, escaping with a {margin}-point win, {wscore}-{lscore}.",
]
BLOWOUT_TEMPLATES = [
    "{winner} had no mercy for {loser}, winning {wscore}-{lscore} - a {margin}-point beatdown.",
    "Not so close: {winner} ran up the score on {loser}, {wscore}-{lscore}.",
]
STUD_TEMPLATES = [
    "Stud of the week: {name} ({team}) dropped {points} points, best of anyone in the league.",
    "Nobody topped {name} ({team}) this week - {points} points to lead all starters.",
]
UPSET_TEMPLATES = [
    "Upset alert: {winner} came in ranked #{wrank} and knocked off {loser}'s #{lrank}.",
    "{winner} (#{wrank} entering the week) had no business beating {loser} (#{lrank}) - but here we are.",
]
DIVISION_SALT_TEMPLATES = [
    "Division-rival salt: {hits} went off on {owner}, a {fan_team} fan.",
    "Rough week to be a {fan_team} fan: {hits} torched {owner}'s lineup.",
]
PLOT_TWIST_TEMPLATES = [
    "Plot twist: {owner}, a {fan_team} fan, has been starting {reveals} all along.",
    "Buried lede: {owner} ({fan_team} fan) is rostering {reveals}, and has been for a while.",
]
LOOKING_AHEAD_TEMPLATES_PLAIN = [
    "{a} faces {b}",
    "{a} squares off against {b}",
]
LOOKING_AHEAD_TEMPLATES_REMATCH = [
    "{a} faces {b} again - {prior_winner} won the first meeting {prior_score}",
    "Rematch: {a} vs. {b}; {prior_winner} took the first one {prior_score}",
]


def join_list(items):
    """Proper English list grammar: "A", "A and B", "A, B, and C" - so
    multiple same-type items in one week read as one sentence, not a
    repeated item per instance."""
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

    def team_with_meta(self, team_id, *meta):
        """Team name with owner AND extra context (record, rank, ...) in
        ONE parenthetical - "Illusions Michael (Pete, 10-3)" - rather than
        stacking a second paren group after team_short(), which read as
        "Illusions Michael (Pete) (10-3)."""
        t = self.teams[team_id]
        parts = ", ".join([owner_first_name(t["owners"]), *[str(m) for m in meta]])
        return f"{t['name'].strip()} ({parts})"


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
    losses = {tid: 0 for tid in ctx.teams}
    pf = {tid: 0.0 for tid in ctx.teams}
    for m in ctx.matchups:
        if m["is_playoffs"] or m["week"] > through_week:
            continue
        pf[m["home_team_id"]] += m["home_score"]
        pf[m["away_team_id"]] += m["away_score"]
        if m["winner"] == "HOME":
            wins[m["home_team_id"]] += 1
            losses[m["away_team_id"]] += 1
        elif m["winner"] == "AWAY":
            wins[m["away_team_id"]] += 1
            losses[m["home_team_id"]] += 1
    ranked = sorted(ctx.teams, key=lambda tid: (-wins[tid], -pf[tid]))
    rank = {tid: i + 1 for i, tid in enumerate(ranked)}
    record = {tid: (wins[tid], losses[tid], pf[tid]) for tid in ctx.teams}
    return rank, record


def _week_stud(week_box):
    """The single highest-scoring started player league-wide this week."""
    stud = None
    for team_id_str, players in week_box.items():
        for p in players:
            if p["started"] and (stud is None or p["points"] > stud["points"]):
                stud = {**p, "team_id": int(team_id_str)}
    return stud


def _winner_loser(m):
    if m["winner"] == "HOME":
        return m["home_team_id"], m["home_score"], m["away_team_id"], m["away_score"]
    return m["away_team_id"], m["away_score"], m["home_team_id"], m["home_score"]


def build_week_features(ctx, week, week_matchups, entering_rank, stud, week_box):
    """The standalone weekly highlights - each its own item, with real
    narrative prose, never glued onto a plain scoreline."""
    rng = random.Random(week)  # stable phrasing per week across reruns
    features = []

    by_margin = sorted(week_matchups, key=lambda m: abs(m["home_score"] - m["away_score"]))
    closest = by_margin[0]
    cw, cws, cl, cls = _winner_loser(closest)
    features.append({
        "type": "game_of_the_week",
        "team_ids": [cw, cl],
        "text": rng.choice(CLOSE_GAME_TEMPLATES).format(
            winner=ctx.team_short(cw), loser=ctx.team_short(cl),
            wscore=f"{cws:.1f}", lscore=f"{cls:.1f}", margin=f"{abs(cws - cls):.1f}",
        ),
    })

    blowout = by_margin[-1]
    if blowout != closest and abs(blowout["home_score"] - blowout["away_score"]) >= BLOWOUT_MARGIN:
        bw, bws, bl, bls = _winner_loser(blowout)
        features.append({
            "type": "blowout_of_the_week",
            "team_ids": [bw, bl],
            "text": rng.choice(BLOWOUT_TEMPLATES).format(
                winner=ctx.team_short(bw), loser=ctx.team_short(bl),
                wscore=f"{bws:.1f}", lscore=f"{bls:.1f}", margin=f"{abs(bws - bls):.1f}",
            ),
        })

    if stud:
        features.append({
            "type": "stud_of_the_week",
            "team_ids": [stud["team_id"]],
            "text": rng.choice(STUD_TEMPLATES).format(
                name=stud["name"], team=ctx.team_short(stud["team_id"]), points=f"{stud['points']:.1f}",
            ),
        })

    for m in week_matchups:
        if m["winner"] not in ("HOME", "AWAY"):
            continue
        winner_id, _, loser_id, _ = _winner_loser(m)
        if not entering_rank:
            continue
        upset_size = entering_rank[winner_id] - entering_rank[loser_id]
        if upset_size >= UPSET_MIN_RANK_SWING:
            features.append({
                "type": "upset_alert",
                "team_ids": [winner_id, loser_id],
                "text": rng.choice(UPSET_TEMPLATES).format(
                    winner=ctx.team_short(winner_id), loser=ctx.team_short(loser_id),
                    wrank=entering_rank[winner_id], lrank=entering_rank[loser_id],
                ),
            })

    # Fandom: a real division rival torched an owner this week.
    for team_id, owner in ctx.owner_by_team_id.items():
        rivals = ctx.rival_abbrevs_by_owner.get(owner)
        if not rivals:
            continue
        game = next((m for m in week_matchups if team_id in (m["home_team_id"], m["away_team_id"])), None)
        if not game:
            continue
        opp_id = game["away_team_id"] if game["home_team_id"] == team_id else game["home_team_id"]
        hits = [
            f"{p['name']} ({p['pro_team']}, {p['points']:.1f} pts)"
            for p in week_box.get(str(opp_id), [])
            if p["started"] and p["pro_team"] in rivals and p["points"] >= DIVISION_RIVAL_MIN_POINTS
        ]
        if hits:
            features.append({
                "type": "division_rival_salt",
                "team_ids": [team_id, opp_id],
                "text": rng.choice(DIVISION_SALT_TEMPLATES).format(
                    hits=join_list(hits), owner=owner, fan_team=ctx.fandom[owner],
                ),
            })

    # Fandom: owner is rostering a division rival - ONE-TIME reveal per
    # (owner, player), grouped if multiple are new in the same week.
    for team_id, owner in ctx.owner_by_team_id.items():
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
            features.append({
                "type": "plot_twist",
                "team_ids": [team_id],
                "text": rng.choice(PLOT_TWIST_TEMPLATES).format(
                    owner=owner, fan_team=ctx.fandom[owner], reveals=join_list(new_reveals),
                ),
            })

    return features


def build_week_briefs(ctx, week_matchups, record_after):
    """Clean scorelines for all 6 games - the box-score layer, guaranteeing
    every team is covered regardless of whether they made the features.
    Records shown are AS OF AFTER this week's games (real box-score
    convention), not entering it.
    """
    briefs = []
    for m in week_matchups:
        if m["winner"] not in ("HOME", "AWAY"):
            continue
        winner_id, wscore, loser_id, lscore = _winner_loser(m)
        rec_w = f"{record_after[winner_id][0]}-{record_after[winner_id][1]}"
        rec_l = f"{record_after[loser_id][0]}-{record_after[loser_id][1]}"
        briefs.append({
            "winner_team_id": winner_id,
            "loser_team_id": loser_id,
            "winner_score": wscore,
            "loser_score": lscore,
            "text": f"{ctx.team_with_meta(winner_id, rec_w)} beat {ctx.team_with_meta(loser_id, rec_l)} "
                    f"{wscore:.1f}-{lscore:.1f}",
        })
    return briefs


def build_playoff_picture(ctx, week):
    """Top PLAYOFF_SPOTS of 12 make it - confirmed against the real 2025
    bracket in season_moments.json. Same regular-season-only ranking as
    everything else here; no bracket tracing, since real playoffs haven't
    happened yet mid-season.

    Includes cumulative points_for, both because it's the actual
    tiebreaker (see standings_through_week()) and to surface "leap"
    context: `points_back` is only set when a row is tied in wins with
    the row directly above it - that's the one case where points_for is
    literally the deciding gap to close, so it's the only case where
    showing it as a "how far behind" number means something concrete.
    """
    rank, record = standings_through_week(ctx, week)
    ranked_ids = sorted(ctx.teams, key=lambda tid: rank[tid])
    rows = []
    prev = None
    for tid in ranked_ids:
        wins, losses, pf = record[tid]
        points_back = None
        if prev and prev["wins"] == wins:
            points_back = round(prev["points_for"] - pf, 1)
        row = {
            "team_id": tid,
            "rank": rank[tid],
            "wins": wins,
            "losses": losses,
            "points_for": round(pf, 1),
            "points_back": points_back,
            "in_playoffs": rank[tid] <= PLAYOFF_SPOTS,
        }
        rows.append(row)
        prev = row
    return rows


def build_looking_ahead(ctx, week):
    """Next week's matchups, previewed using ONLY information available
    before those games are played: records/rank entering, and - for a
    rematch - the PRIOR meeting's actual result. That prior result is
    fair game even though it's "the answer" to something: it already
    happened, same as it would in a real live 2026 preview written after
    that earlier week's games are final. What stays off-limits is the
    outcome of the games THIS preview is actually previewing - never
    used, even though testing against a real past season means it's
    sitting right there in the data.
    """
    next_week = week + 1
    next_matchups = [m for m in ctx.matchups if m["week"] == next_week and not m["is_playoffs"]]
    if not next_matchups:
        return None
    rng = random.Random(week * 1000 + 1)  # distinct stream from build_week_features' rng

    rank, record = standings_through_week(ctx, week)
    last_meeting = {}
    for m in ctx.matchups:
        if m["is_playoffs"] or m["week"] > week or m["winner"] not in ("HOME", "AWAY"):
            continue
        pair = frozenset((m["home_team_id"], m["away_team_id"]))
        last_meeting[pair] = m  # keep overwriting - ends on the MOST RECENT prior meeting

    previews = []
    for m in next_matchups:
        a, b = m["home_team_id"], m["away_team_id"]
        a_label = ctx.team_with_meta(a, f"#{rank.get(a)}", f"{record[a][0]}-{record[a][1]}")
        b_label = ctx.team_with_meta(b, f"#{rank.get(b)}", f"{record[b][0]}-{record[b][1]}")
        prior = last_meeting.get(frozenset((a, b)))
        if prior:
            pw, pws, pl, pls = _winner_loser(prior)
            text = rng.choice(LOOKING_AHEAD_TEMPLATES_REMATCH).format(
                a=a_label, b=b_label,
                prior_winner=ctx.team_short(pw), prior_score=f"{pws:.1f}-{pls:.1f}",
            )
        else:
            text = rng.choice(LOOKING_AHEAD_TEMPLATES_PLAIN).format(a=a_label, b=b_label)
        previews.append({"team_ids": [a, b], "text": text})
    return {"week": next_week, "matchups": previews}


def build_week_recap(ctx, week):
    week_matchups = [m for m in ctx.matchups if m["week"] == week and not m["is_playoffs"]]
    if not week_matchups:
        return None
    entering_rank, _ = standings_through_week(ctx, week - 1) if week > 1 else (None, None)
    _, record_after = standings_through_week(ctx, week)
    week_box = ctx.boxscores[str(week)]
    stud = _week_stud(week_box)

    return {
        "week": week,
        "features": build_week_features(ctx, week, week_matchups, entering_rank, stud, week_box),
        "briefs": build_week_briefs(ctx, week_matchups, record_after),
        "looking_ahead": build_looking_ahead(ctx, week),
        "playoff_picture": build_playoff_picture(ctx, week),
    }


def main(season):
    ctx = RecapContext(season)
    played_weeks = sorted({m["week"] for m in ctx.matchups if not m["is_playoffs"]})

    weekly_recap = [r for r in (build_week_recap(ctx, week) for week in played_weeks) if r]

    out_path = DOCS_DATA / str(season) / "weekly_recap.json"
    out_path.write_text(json.dumps(weekly_recap, indent=2))
    print(f"Wrote weekly_recap.json ({len(weekly_recap)} weeks, season {season})")


if __name__ == "__main__":
    import sys

    main(int(sys.argv[1]) if len(sys.argv) > 1 else 2026)
