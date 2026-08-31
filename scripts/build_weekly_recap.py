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
  - The "rostering a division rival" bit went through 2 versions. v1
    fired once per (owner, player) just for STARTING a rival's player -
    Ronjan's read after a full season of real output: merely rostering
    a rival isn't news, and a one-time reveal still meant a fresh "plot
    twist" almost every week for different players, which read as
    exactly as repetitive as re-announcing the same one weekly. v2 (see
    PLOT_TWIST_TEMPLATES) only fires when that rostered rival player
    actually scores big FOR the owner that week - real production, not
    presence - which is the genuinely ironic thing worth calling out,
    and naturally self-limits since it takes an actual good week to
    trigger, not just a bench slot.
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

from espn_maps import LINEUP_SLOT_MAP, division_rival_abbrevs
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
    "Down to the wire: {winner} edged {loser} {wscore}-{lscore}.",
    "{loser} pushed {winner} to the brink, falling {margin} points short, {wscore}-{lscore}.",
    "It came down to the last stat line: {winner} over {loser}, {wscore}-{lscore}.",
    "{winner} held off a late push from {loser} to win {wscore}-{lscore}.",
]
BLOWOUT_TEMPLATES = [
    "{winner} had no mercy for {loser}, winning {wscore}-{lscore} - a {margin}-point beatdown.",
    "Not so close: {winner} ran up the score on {loser}, {wscore}-{lscore}.",
    "{winner} embarrassed {loser} {wscore}-{lscore}, a {margin}-point statement.",
    "{loser} never had a chance - {winner} rolled to a {wscore}-{lscore} win.",
    "Blowout of the week: {winner} demolished {loser} by {margin}, {wscore}-{lscore}.",
    "{winner} put {loser} away early, cruising to a {wscore}-{lscore} win.",
]
STUD_TEMPLATES = [
    "Stud of the week: {name} ({team}) dropped {points} points, best of anyone in the league.",
    "Nobody topped {name} ({team}) this week - {points} points to lead all starters.",
    "{name} ({team}) turned in the best lineup card of the week - {points} points.",
    "Top scorer this week: {name} ({team}), {points} points.",
    "{name} ({team}) went off for {points} points - nobody else in the league was close.",
    "The stat sheet belonged to {name} ({team}) this week: {points} points.",
]
UPSET_TEMPLATES = [
    "Upset alert: {winner} came in ranked #{wrank} and knocked off {loser}'s #{lrank}.",
    "{winner} (#{wrank} entering the week) had no business beating {loser} (#{lrank}) - but here we are.",
    "Chalk got tossed out the window: #{wrank} {winner} took down #{lrank} {loser}.",
    "{loser} came in ranked #{lrank} and still found a way to lose to #{wrank} {winner}.",
    "Nobody saw this coming: {winner} (#{wrank}) beat {loser} (#{lrank}).",
    "#{wrank} {winner} over #{lrank} {loser} - the standings didn't see that coming.",
]
DIVISION_SALT_TEMPLATES = [
    "Division-rival salt: {hits} went off on {owner}, a {fan_team} fan.",
    "Rough week to be a {fan_team} fan: {hits} torched {owner}'s lineup.",
    "{owner} ({fan_team} fan) just got cooked by a division rival - {hits}.",
    "Nothing like getting beat by a rival: {hits} lit up {owner}'s week.",
    "{owner}'s {fan_team} allegiance took a beating this week, courtesy of {hits}.",
    "{hits} made {owner}'s week miserable - and {owner} roots for the {fan_team}.",
]
# Fires when a rostered division rival scores BIG *for* the owner in a
# given week - see build_week_features() for why this replaced an earlier
# existence-only ("you're rostering a rival at all") version.
PLOT_TWIST_TEMPLATES = [
    "Plot twist: {hits} carried {owner} ({fan_team} fan) to a big week - a division rival doing the heavy lifting.",
    "The irony: {hits} led the way for {owner} this week, and {owner} roots for the {fan_team}.",
    "{owner} ({fan_team} fan) will take the win, even if {hits} did the heavy lifting.",
    "Not exactly on-brand: {owner}'s {fan_team} loyalty didn't stop {hits} from carrying the week.",
    "{hits} showed up big for {owner} this week - awkward, given the {fan_team} allegiance.",
    "{owner} ({fan_team} fan) got bailed out by a division rival: {hits}.",
]
CHAMPIONSHIP_TEMPLATES = [
    "{winner} is your champion, beating {loser} {wscore}-{lscore} to take the title.",
    "It's a title for {winner} - {loser} falls {wscore}-{lscore} in the championship.",
    "{winner} closes it out: {wscore}-{lscore} over {loser} to win it all.",
    "Champions: {winner}, {wscore}-{lscore} over {loser}.",
]
THIRD_PLACE_TEMPLATES = [
    "3rd place: {winner} beat {loser} {wscore}-{lscore}.",
    "Consolation prize - {winner} took 3rd, beating {loser} {wscore}-{lscore}.",
    "Not nothing: {winner} closes with a 3rd-place win over {loser}, {wscore}-{lscore}.",
    "{winner} salvages 3rd place, beating {loser} {wscore}-{lscore}.",
]
LOOKING_AHEAD_TEMPLATES_PLAIN = [
    "{a} faces {b}",
    "{a} squares off against {b}",
    "{a} takes on {b}",
    "Next up: {a} vs. {b}",
    "{a} and {b} go head-to-head",
]
LOOKING_AHEAD_TEMPLATES_REMATCH = [
    "{a} faces {b} again - {prior_winner} won the first meeting {prior_score}",
    "Rematch: {a} vs. {b}; {prior_winner} took the first one {prior_score}",
    "{a} and {b} run it back - {prior_winner} won the first go-round {prior_score}",
    "Second helping: {a} vs. {b} again, after {prior_winner} took the opener {prior_score}",
]
ALL_PLAY_MIN_WEEKS = 3  # don't bother below this - too small a sample to mean anything
ALL_PLAY_TEMPLATES = [
    "Over a full season of head-to-head, {a_owner} would be {aw}-{bw} against {b_owner}",
    "Play every week and it's {a_owner} {aw}-{bw} {b_owner}",
    "By weekly scoring alone, {a_owner} has the edge, {aw}-{bw} over {b_owner}",
    "All-play says {a_owner} {aw}-{bw} {b_owner}",
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
    than per week."""

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
        self.num_regular_weeks = max(m["week"] for m in self.matchups if not m["is_playoffs"])

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


# Real fantasy roster display order - QB, then both RB/WR slots grouped,
# TE, FLEX, then D/ST and K last. Not the raw lineup_slot_id numeric
# order (which interleaves BE/IR between them).
ROSTER_SLOT_ORDER = [0, 2, 4, 6, 23, 16, 17]


def build_lineup(week_box, team_id):
    """A team's full STARTED lineup for one week, in real roster display
    order - the "who actually won this" breakdown for a marquee game,
    same idea as the old league's championship-recap lineup tables."""
    players = [p for p in week_box.get(str(team_id), []) if p["started"]]

    def sort_key(p):
        slot = p["lineup_slot_id"]
        order = ROSTER_SLOT_ORDER.index(slot) if slot in ROSTER_SLOT_ORDER else len(ROSTER_SLOT_ORDER)
        return (order, -p["points"])

    players.sort(key=sort_key)
    return [
        {
            "name": p["name"],
            "position": LINEUP_SLOT_MAP.get(p["lineup_slot_id"], p["position"]),
            "pro_team": p["pro_team"],
            "points": p["points"],
        }
        for p in players
    ]


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
        # Full lineup breakdown, winner then loser - the "how it was
        # actually won" table, same idea as the old league's championship
        # recap. Only for Game of the Week, not every matchup - a lineup
        # table on all 6 games would bury this rather than spotlight it.
        "lineups": {
            str(cw): build_lineup(week_box, cw),
            str(cl): build_lineup(week_box, cl),
        },
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

    # Fandom: the mirror image of division_rival_salt above - a rostered
    # division rival went OFF *for* the owner this week (not just "you
    # happen to own a rival's player", which isn't news - see the module
    # docstring for why this replaced the old one-time-reveal version).
    for team_id, owner in ctx.owner_by_team_id.items():
        rivals = ctx.rival_abbrevs_by_owner.get(owner)
        if not rivals:
            continue
        hits = [
            f"{p['name']} ({p['pro_team']}, {p['points']:.1f} pts)"
            for p in week_box.get(str(team_id), [])
            if p["started"] and p["pro_team"] in rivals and p["points"] >= DIVISION_RIVAL_MIN_POINTS
        ]
        if hits:
            features.append({
                "type": "plot_twist",
                "team_ids": [team_id],
                "text": rng.choice(PLOT_TWIST_TEMPLATES).format(
                    owner=owner, fan_team=ctx.fandom[owner], hits=join_list(hits),
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


def _remaining_games(ctx, week, num_regular_weeks):
    """{team_id: count of regular-season games left after `week`}."""
    remaining = {tid: 0 for tid in ctx.teams}
    for m in ctx.matchups:
        if m["is_playoffs"] or m["week"] <= week or m["week"] > num_regular_weeks:
            continue
        remaining[m["home_team_id"]] += 1
        remaining[m["away_team_id"]] += 1
    return remaining


def _clinch_status(tid, record, remaining, all_ids):
    """(status, magic_number) for one team - "clinched" / "eliminated" /
    "alive", using the standard worst-case/best-case method real sports
    "magic number" tables use: assume the team in question gets the
    extreme outcome (all losses to test clinching, all wins to test
    elimination) and everyone else gets the extreme outcome that helps
    them most, then check whether PLAYOFF_SPOTS teams could still equal
    or beat that. This can be slightly conservative near the very end of
    a season (it doesn't reason about head-to-head tiebreakers), which
    is the safe direction - it will never falsely call a team clinched.

    magic_number is only meaningful for "alive" teams: the fewest
    additional wins (out of their remaining games) that would guarantee
    a clinch regardless of every other result.
    """
    wins, _, pf = record[tid]
    others = [t for t in all_ids if t != tid]

    def would_clinch(extra_wins):
        floor_wins = wins + extra_wins  # worst case for tid beyond these guaranteed wins
        can_catch_up = sum(
            1 for s in others
            if record[s][0] + remaining[s] >= floor_wins
        )
        return can_catch_up < PLAYOFF_SPOTS

    def would_be_eliminated():
        ceiling_wins = wins + remaining[tid]  # best case for tid
        guaranteed_ahead = sum(1 for s in others if record[s][0] >= ceiling_wins)
        return guaranteed_ahead >= PLAYOFF_SPOTS

    if would_clinch(0):
        return "clinched", 0
    if would_be_eliminated():
        return "eliminated", None
    for extra in range(1, remaining[tid] + 1):
        if would_clinch(extra):
            return "alive", extra
    return "alive", None  # can't guarantee it even winning out - still mathematically alive on tiebreakers


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
    remaining = _remaining_games(ctx, week, ctx.num_regular_weeks)
    all_ids = list(ctx.teams)
    ranked_ids = sorted(ctx.teams, key=lambda tid: rank[tid])
    rows = []
    prev = None
    for tid in ranked_ids:
        wins, losses, pf = record[tid]
        points_back = None
        if prev and prev["wins"] == wins:
            points_back = round(prev["points_for"] - pf, 1)
        status, magic_number = _clinch_status(tid, record, remaining, all_ids)
        row = {
            "team_id": tid,
            "rank": rank[tid],
            "wins": wins,
            "losses": losses,
            "points_for": round(pf, 1),
            "points_back": points_back,
            "in_playoffs": rank[tid] <= PLAYOFF_SPOTS,
            "status": status,
            "magic_number": magic_number,
            "games_remaining": remaining[tid],
        }
        rows.append(row)
        prev = row
    return rows


def _team_scores_by_week(ctx, through_week):
    """{team_id: {week: score}} for every regular-season week through
    through_week - what each team actually scored, independent of who
    they actually played. Powers the "all-play" hypothetical head-to-head
    below (every team plays exactly one real game per week, so this
    covers every team for every week in range)."""
    scores = {tid: {} for tid in ctx.teams}
    for m in ctx.matchups:
        if m["is_playoffs"] or m["week"] > through_week:
            continue
        scores[m["home_team_id"]][m["week"]] = m["home_score"]
        scores[m["away_team_id"]][m["week"]] = m["away_score"]
    return scores


def hypothetical_h2h(scores_by_week, team_a, team_b):
    """"If these two had played every week this season" - a's record
    against b, purely by comparing each week's actual scores. Real
    precedent: the old league's own recaps did exactly this for playoff
    rivalry write-ups ("had they played every week, X would be 8-4
    against Y")."""
    a_wins = b_wins = 0
    weeks_a, weeks_b = scores_by_week[team_a], scores_by_week[team_b]
    for wk, a_score in weeks_a.items():
        b_score = weeks_b.get(wk)
        if b_score is None:
            continue
        if a_score > b_score:
            a_wins += 1
        elif b_score > a_score:
            b_wins += 1
    return a_wins, b_wins


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

    scores_by_week = _team_scores_by_week(ctx, week)

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

        # Hypothetical all-play head-to-head - real precedent from the old
        # league's own recaps ("had they played every week, X would be
        # 8-4 against Y"). Only worth showing with enough of a sample.
        aw, bw = hypothetical_h2h(scores_by_week, a, b)
        if aw + bw >= ALL_PLAY_MIN_WEEKS:
            text += "; " + rng.choice(ALL_PLAY_TEMPLATES).format(
                a_owner=ctx.owner_by_team_id[a], b_owner=ctx.owner_by_team_id[b], aw=aw, bw=bw,
            )

        previews.append({"team_ids": [a, b], "text": text})
    return {"week": next_week, "matchups": previews}


def compute_seeds(ctx):
    """Final regular-season standings freeze into seeds 1..PLAYOFF_SPOTS
    for the real bracket. Playoff W-L/points_for context everywhere else
    in playoff-week output uses this same frozen snapshot too - playoff
    games determine placement, not an extension of the regular-season
    record."""
    rank, record = standings_through_week(ctx, ctx.num_regular_weeks)
    seed_to_team = {r: tid for tid, r in rank.items() if r <= PLAYOFF_SPOTS}
    return seed_to_team, record


def _find_playoff_result(ctx, week, team_a, team_b):
    for m in ctx.matchups:
        if m["week"] != week or not m["is_playoffs"]:
            continue
        if {m["home_team_id"], m["away_team_id"]} == {team_a, team_b}:
            winner_id, wscore, loser_id, lscore = _winner_loser(m)
            return {"winner": winner_id, "loser": loser_id, "winner_score": wscore, "loser_score": lscore}
    return None


def build_bracket(ctx, through_week=None):
    """Fixed single-elimination bracket for this league's real
    PLAYOFF_SPOTS=6 format - confirmed by tracing all 3 rounds of the
    actual 2025 postseason against this exact structure and matching
    the real champion, runner-up, 3rd, and 4th place teams exactly:

      Wild Card (seeds 1, 2 bye):  4 vs 5,  3 vs 6
      Semifinals (fixed slots):    1 vs (4v5 winner),  2 vs (3v6 winner)
      Championship:                semi winners
      3rd place game:              semi losers (this league treats this
        as a real, official placement game - unlike the parallel
        consolation-ladder games ESPN also schedules for teams 7-12
        under the same is_playoffs flag; see build_season_moments.py's
        compute_standings docstring for that same distinction).

    NOT dynamic reseeding (checked and ruled out - the semifinal
    pairings only make sense as fixed bracket slots, not "highest
    remaining seed vs lowest remaining seed").

    `through_week` caps which weeks' results get revealed - None means
    "everything available" (fine for a completed season, or for the
    Looking Ahead use, which only ever reads results from rounds already
    fully decided). But EACH WEEK'S OWN recap needs its own bracket
    snapshot capped at that week, or every playoff week's bracket field
    would show the exact same fully-resolved bracket regardless of which
    week it's attached to - caught exactly that bug testing this against
    the real 2025 season, where week 15's page was showing the eventual
    champion before the semifinals had even happened.
    """
    seed_to_team, frozen_record = compute_seeds(ctx)
    playoff_weeks = sorted({m["week"] for m in ctx.matchups if m["is_playoffs"] and m["week"] > ctx.num_regular_weeks})
    round_weeks = playoff_weeks[:3]  # this league's bracket is always exactly 3 rounds

    def week_for(round_idx):
        return round_weeks[round_idx] if round_idx < len(round_weeks) else None

    def revealed(week):
        return week and (through_week is None or week <= through_week)

    rounds = []

    game_4v5 = {"seeds": (4, 5), "team_ids": (seed_to_team.get(4), seed_to_team.get(5))}
    game_3v6 = {"seeds": (3, 6), "team_ids": (seed_to_team.get(3), seed_to_team.get(6))}
    r1_week = week_for(0)
    if revealed(r1_week) and all(game_4v5["team_ids"]):
        game_4v5["result"] = _find_playoff_result(ctx, r1_week, *game_4v5["team_ids"])
    if revealed(r1_week) and all(game_3v6["team_ids"]):
        game_3v6["result"] = _find_playoff_result(ctx, r1_week, *game_3v6["team_ids"])
    rounds.append({
        "week": r1_week, "name": "Wild Card",
        "games": [game_4v5, game_3v6],
        "byes": [seed_to_team.get(1), seed_to_team.get(2)],
    })

    winner_4v5 = game_4v5.get("result", {}).get("winner")
    winner_3v6 = game_3v6.get("result", {}).get("winner")
    semi_a = {"seeds": (1, None), "team_ids": (seed_to_team.get(1), winner_4v5)}
    semi_b = {"seeds": (2, None), "team_ids": (seed_to_team.get(2), winner_3v6)}
    r2_week = week_for(1)
    if revealed(r2_week) and all(semi_a["team_ids"]):
        semi_a["result"] = _find_playoff_result(ctx, r2_week, *semi_a["team_ids"])
    if revealed(r2_week) and all(semi_b["team_ids"]):
        semi_b["result"] = _find_playoff_result(ctx, r2_week, *semi_b["team_ids"])
    rounds.append({"week": r2_week, "name": "Semifinals", "games": [semi_a, semi_b], "byes": []})

    champ_a = semi_a.get("result", {}).get("winner")
    champ_b = semi_b.get("result", {}).get("winner")
    third_a = semi_a.get("result", {}).get("loser")
    third_b = semi_b.get("result", {}).get("loser")
    championship = {"seeds": (None, None), "team_ids": (champ_a, champ_b), "label": "Championship"}
    third_place = {"seeds": (None, None), "team_ids": (third_a, third_b), "label": "3rd Place"}
    r3_week = week_for(2)
    if revealed(r3_week) and all(championship["team_ids"]):
        championship["result"] = _find_playoff_result(ctx, r3_week, *championship["team_ids"])
    if revealed(r3_week) and all(third_place["team_ids"]):
        third_place["result"] = _find_playoff_result(ctx, r3_week, *third_place["team_ids"])
    rounds.append({"week": r3_week, "name": "Championship", "games": [championship, third_place], "byes": []})

    return {"seed_to_team": seed_to_team, "frozen_record": frozen_record, "rounds": rounds}


def build_playoff_looking_ahead(ctx, bracket, round_idx):
    """The next round's games - concrete team names where already
    determined (the round just completed is always fully known by the
    time we're building this), otherwise a conditional description
    naming the still-open game. Same "never peek at this round's own
    result" rule as the regular-season version - the round being
    previewed hasn't been played yet from this function's point of view.
    """
    next_idx = round_idx + 1
    if next_idx >= len(bracket["rounds"]):
        return None
    nxt = bracket["rounds"][next_idx]
    if not nxt["week"]:
        return None

    scores_by_week = _team_scores_by_week(ctx, ctx.num_regular_weeks)
    previews = []
    for game in nxt["games"]:
        a, b = game["team_ids"]
        label = game.get("label", nxt["name"])
        if a and b:
            a_label = ctx.team_with_meta(a, f"seed {bracket_seed(bracket, a)}")
            b_label = ctx.team_with_meta(b, f"seed {bracket_seed(bracket, b)}")
            text = f"{label}: {a_label} vs. {b_label}"
            aw, bw = hypothetical_h2h(scores_by_week, a, b)
            if aw + bw >= ALL_PLAY_MIN_WEEKS:
                text += (f"; over a full season of head-to-head, {ctx.owner_by_team_id[a]} would be "
                         f"{aw}-{bw} against {ctx.owner_by_team_id[b]}")
            previews.append({"team_ids": [a, b], "text": text})
        else:
            known = a or b
            known_label = ctx.team_with_meta(known, f"seed {bracket_seed(bracket, known)}") if known else None
            if known_label:
                text = f"{label}: {known_label} awaits the winner of this week's other game"
            else:
                text = f"{label}: set by this week's results"
            previews.append({"team_ids": [t for t in (a, b) if t], "text": text})
    return {"week": nxt["week"], "round_name": nxt["name"], "matchups": previews}


def bracket_seed(bracket, team_id):
    for seed, tid in bracket["seed_to_team"].items():
        if tid == team_id:
            return seed
    return None


def _championship_features(ctx, week, rnd, week_box):
    """The championship + 3rd place results, unconditionally featured
    (never competing with each other or anything else for "closest
    margin") - the championship always leads, gets the lineup breakdown;
    3rd place gets a short mention with no lineup, since it's real but
    not the marquee.
    """
    rng = random.Random(week)
    championship_game, third_place_game = rnd["games"]
    features = []

    champ_result = championship_game.get("result")
    if champ_result:
        cw, cl = champ_result["winner"], champ_result["loser"]
        features.append({
            "type": "championship",
            "team_ids": [cw, cl],
            "text": rng.choice(CHAMPIONSHIP_TEMPLATES).format(
                winner=ctx.team_short(cw), loser=ctx.team_short(cl),
                wscore=f"{champ_result['winner_score']:.1f}", lscore=f"{champ_result['loser_score']:.1f}",
            ),
            "lineups": {str(cw): build_lineup(week_box, cw), str(cl): build_lineup(week_box, cl)},
        })

    third_result = third_place_game.get("result")
    if third_result:
        tw, tl = third_result["winner"], third_result["loser"]
        features.append({
            "type": "third_place",
            "team_ids": [tw, tl],
            "text": rng.choice(THIRD_PLACE_TEMPLATES).format(
                winner=ctx.team_short(tw), loser=ctx.team_short(tl),
                wscore=f"{third_result['winner_score']:.1f}", lscore=f"{third_result['loser_score']:.1f}",
            ),
        })

    return features


def build_playoff_week_recap(ctx, round_idx, week):
    # A fresh bracket snapshot capped at THIS week, not one shared object
    # reused across every playoff week - see build_bracket()'s docstring
    # for the real bug this fixes (every week showing the same final,
    # fully-resolved bracket regardless of which week it's attached to).
    bracket = build_bracket(ctx, through_week=week)
    rnd = bracket["rounds"][round_idx]
    if not rnd["week"]:
        return None

    all_week_matchups = [m for m in ctx.matchups if m["week"] == week and m["is_playoffs"]]
    if not all_week_matchups:
        return None

    bracket_team_ids = {tid for g in rnd["games"] for tid in g["team_ids"] if tid}
    bracket_matchups = [
        m for m in all_week_matchups
        if m["home_team_id"] in bracket_team_ids and m["away_team_id"] in bracket_team_ids
    ]

    entering_rank, frozen_record = standings_through_week(ctx, ctx.num_regular_weeks)
    week_box = ctx.boxscores[str(week)]
    # Game of the Week / Stud / etc. only look at the real bracket games
    # for a playoff week - a consolation-bracket blowout shouldn't
    # upstage an actual semifinal. Briefs (below) still cover everything.
    stud = _week_stud({str(tid): week_box.get(str(tid), []) for tid in bracket_team_ids}) if bracket_matchups else None
    features = build_week_features(ctx, week, bracket_matchups, entering_rank, stud, week_box) if bracket_matchups else []

    if rnd["name"] == "Championship":
        # The closest-margin "Game of the Week" pick doesn't belong here -
        # checked against real 2025 data and it picked the 3rd-place game
        # over the actual title game, because the consolation game
        # happened to be closer. The championship is unconditionally the
        # marquee feature on this week regardless of margin; swap it in
        # ahead of whatever build_week_features picked.
        features = [f for f in features if f["type"] not in ("game_of_the_week", "blowout_of_the_week")]
        features = _championship_features(ctx, week, rnd, week_box) + features

    return {
        "week": week,
        "is_playoffs": True,
        "round_name": rnd["name"],
        "features": features,
        "briefs": build_week_briefs(ctx, all_week_matchups, frozen_record),
        "looking_ahead": build_playoff_looking_ahead(ctx, bracket, round_idx),
        "bracket": bracket,
    }


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


def _week_is_decided(ctx, week):
    """Whether any real result exists for this week yet. matchups.json
    holds the FULL season schedule from day one (generate_data.py pulls
    it straight from ESPN's own schedule endpoint, which returns every
    matchup period up front, not just played ones) - so a future week's
    games already exist as entries here, just with winner unset and 0
    scores. Without this check, a mid-2026-season run would "recap"
    weeks that haven't happened yet.
    """
    return any(m["week"] == week and m["winner"] in ("HOME", "AWAY") for m in ctx.matchups)


def main(season):
    ctx = RecapContext(season)
    played_weeks = sorted({
        m["week"] for m in ctx.matchups
        if not m["is_playoffs"] and _week_is_decided(ctx, m["week"])
    })

    weekly_recap = [r for r in (build_week_recap(ctx, week) for week in played_weeks) if r]

    # build_bracket() seeds off the FULL regular season - meaningless (and
    # actively misleading) to compute before it's actually finished, so
    # skip playoff processing entirely until then. This particular call
    # is only to learn the round/week structure (fixed and knowable in
    # advance regardless of results) - build_playoff_week_recap() builds
    # its OWN properly-capped bracket snapshot for each week's results.
    if _week_is_decided(ctx, ctx.num_regular_weeks):
        structural_bracket = build_bracket(ctx)
        for round_idx, rnd in enumerate(structural_bracket["rounds"]):
            if not rnd["week"] or not _week_is_decided(ctx, rnd["week"]):
                continue
            r = build_playoff_week_recap(ctx, round_idx, rnd["week"])
            if r:
                weekly_recap.append(r)

    out_path = DOCS_DATA / str(season) / "weekly_recap.json"
    out_path.write_text(json.dumps(weekly_recap, indent=2))
    print(f"Wrote weekly_recap.json ({len(weekly_recap)} weeks, season {season})")


if __name__ == "__main__":
    import sys

    main(int(sys.argv[1]) if len(sys.argv) > 1 else 2026)
