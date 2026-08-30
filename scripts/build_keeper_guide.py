"""Build a 2026 keeper guide for each owner, from league_rules/keeper_rules_extracted.txt:

  - Cost to keep a player = the draft round used to acquire them, minus one.
  - A round-1 pick costs a round-1 pick AND consumes a second keeper slot
    (so keeping a 1st-rounder caps you at 2 keepers total, not 3).
  - No team may keep both their round-1 and round-2 picks (both would cost a
    round-1 pick, but there's only one round-1 slot). Same logic extends to
    holding two round-1-drafted players via trade - only one can be kept.
  - Eligible: drafted in 2025 (waiver-only pickups don't count) and on the
    roster at end of 2025 season. Trades/waiver churn don't reset this - a
    player's cost basis is their ORIGINAL 2025 draft round, wherever they've
    ended up since.
  - If a team holds 2+ keeper candidates from the same original round (via
    trades/waiver churn) and wants to keep both, one gets the normal -1
    round, the other gets a -2 round escalator.

This is the league's first-ever keeper cycle (2025 -> 2026), so the "not
kept more than 2 years running" cap doesn't bind yet for anyone - every
2025 draftee still rostered is a fresh keeper candidate.

League is 0.5 PPR AND runs a QB + OP(superflex) roster slot, so plain
PPR/STANDARD rank or ADP would badly undervalue QBs. Points totals from
ESPN's `stats` field are already computed under this league's own 0.5-PPR
scoring rules (no extra adjustment needed there) - but rank/ADP uses
ESPN's separate SUPERFLEX-specific rank type, not the league's nominal
"PPR" rank-type setting (that setting only describes scoring, not the
2-QB-capable roster format that actually drives QB scarcity).

Position rank (2025 actual, 2026 projected) is computed against a ~600
player pool (full NFL fantasy-relevant universe, not just this league's
228 drafted players), so "RB4" means 4th-best RB in the NFL, not 4th-best
among players this league happened to draft.

Run after generate_data.py (needs docs/data/2025 and docs/data/2026).
"""

import json
from collections import defaultdict
from pathlib import Path

from config import CURRENT_SEASON, LEAGUE_ID
from espn_client import fetch_player_pool, fetch_players_by_id
from espn_maps import POSITION_MAP, PRO_TEAM_MAP

DOCS_DATA = Path(__file__).parent.parent / "docs" / "data"
LEAGUE_RULES = Path(__file__).parent.parent / "league_rules"
NUM_TEAMS = 12

# A couple of owners go by a nickname in league chatter/spreadsheets that
# isn't their ESPN account's first name.
OWNER_NICKNAMES = {
    "Michael Higgins": "Mike",
    "Joseph Sebranek": "Joe",
    "Karlos Abel": "Karl",
}


def owner_first_name(owners):
    full = owners[0] if owners else ""
    return OWNER_NICKNAMES.get(full, full.split()[0])


def load(season, name):
    return json.loads((DOCS_DATA / str(season) / name).read_text())


def to_round_pick(overall_pick, teams=NUM_TEAMS):
    """Overall pick number -> (round, pick_in_round), non-snake convention."""
    if overall_pick is None:
        return None, None
    round_num = (overall_pick - 1) // teams + 1
    pick_in_round = overall_pick - (round_num - 1) * teams
    return round_num, pick_in_round


def get_points(player, stat_source_id, season_id):
    """statSourceId: 0=actual, 1=projected. Season-total row (scoringPeriodId=0)."""
    for s in player.get("stats", []):
        if (
            s.get("statSourceId") == stat_source_id
            and s.get("statSplitTypeId") == 0
            and s.get("seasonId") == season_id
            and s.get("scoringPeriodId") == 0
        ):
            return s.get("appliedTotal")
    return None


def _load_league_rules_json(name):
    data = json.loads((LEAGUE_RULES / name).read_text())
    return {k: v for k, v in data.items() if not k.startswith("_")}


def mark_kept_2026(guide):
    """Stamp `kept_2026` onto each candidate and a `locked_keepers_2026`
    summary onto each team, from league_rules/keeper_selections_2026.json
    (the finalized picks, transcribed from the keeper board spreadsheet
    once everyone locked in - not derivable from the ESPN API).
    """
    selections = {k.lower(): v for k, v in _load_league_rules_json("keeper_selections_2026.json").items()}

    matched = set()
    for team in guide:
        first = owner_first_name(team["owners"])
        kept_names = selections.get(first.lower())
        if kept_names is None:
            raise ValueError(
                f"No keeper_selections_2026.json entry for owner '{first}' (team {team['team_name']!r})"
            )
        matched.add(first.lower())

        by_name = {c["name"]: c for c in team["candidates"]}
        locked = []
        for name in kept_names:
            cand = by_name.get(name)
            if cand is None:
                raise ValueError(
                    f"{first}: keeper selection {name!r} not found among "
                    f"{team['team_name']!r}'s candidates - check for a name mismatch"
                )
            cand["kept_2026"] = True
            locked.append(
                {
                    "player_id": cand["player_id"],
                    "name": cand["name"],
                    "position": cand["position"],
                    "pro_team": cand["pro_team"],
                    "keeper_cost_round_2026": cand["keeper_cost_round_2026"],
                }
            )
        for c in team["candidates"]:
            c.setdefault("kept_2026", False)
        locked.sort(key=lambda k: k["keeper_cost_round_2026"])
        team["locked_keepers_2026"] = locked

    unmatched = set(selections) - matched
    if unmatched:
        raise ValueError(f"keeper_selections_2026.json has owners with no matching team: {unmatched}")


ADP_CONTEXT_SKILL_POSITIONS = {"QB", "RB", "WR", "TE"}
ADP_CONTEXT_SIZE = 5
ADP_CONTEXT_MIN_POSITIONS = 3
ADP_CONTEXT_LOOKAHEAD = 20


def _pick_adp_context(pool, cursor):
    """The `ADP_CONTEXT_SIZE` players shown for one open pick, biased to
    cover at least `ADP_CONTEXT_MIN_POSITIONS` distinct skill positions
    rather than whatever the next N players by rank happen to be - a run
    of same-position ADP neighbors (common; RBs and WRs both go in
    streaks) would otherwise show a pick's context as e.g. 5 straight
    WRs, which undersells how open that pick actually is.

    Only QB/RB/WR/TE count toward the position-diversity floor. K/D-ST
    intentionally don't: real ~2026 ADP data has a hard ~60-player dead
    zone (rank ~142-205) that's ALL 32 D/ST then ALL kickers, zero
    skill positions in between - counting those toward diversity would
    make the floor trivially satisfiable there without actually
    reflecting draftable variety.

    For the ~12% of picks whose lookahead window has no way to reach 3
    skill positions (that same dead zone, landing around rounds 14-17
    of this draft) there's no good answer - showing a WR ranked 200
    spots below the window just to hit a quota would be a worse
    suggestion than an honest "here's what's actually next", so this
    falls back to a plain next-N-by-rank slice for exactly those picks.
    """
    window = pool[cursor : cursor + ADP_CONTEXT_LOOKAHEAD]

    secured = []
    seen_positions = set()
    for p in window:
        if p["position"] in ADP_CONTEXT_SKILL_POSITIONS and p["position"] not in seen_positions:
            secured.append(p)
            seen_positions.add(p["position"])
        if len(seen_positions) >= ADP_CONTEXT_MIN_POSITIONS:
            break

    if len(seen_positions) < ADP_CONTEXT_MIN_POSITIONS:
        return window[:ADP_CONTEXT_SIZE]

    secured_ids = {p["player_id"] for p in secured}
    fill = [p for p in window if p["player_id"] not in secured_ids][: ADP_CONTEXT_SIZE - len(secured)]
    chosen = secured + fill
    chosen.sort(key=lambda p: p["adjusted_rank"])
    return chosen


def build_draft_guide(guide, adp_unkept):
    """19-round x 12-team snake grid for the confirmed 2026 draft order,
    with each team's locked keepers pre-slotted into their cost round.

    This is a static reference, not a live tool - nobody can feed it real
    picks as the draft happens. So the ADP context has to carry the whole
    load per pick, not just per round: every OPEN pick gets its own window
    of `ADP_CONTEXT_SIZE` example players from `adp_unkept` (already
    excludes every kept player; see `_pick_adp_context` for how those
    players are actually chosen), advancing a single cursor through the
    ADP-sorted pool one player per open pick - in true overall-pick order,
    not reset each round. A round-level window would collapse pick 25 and
    pick 36 (huge ADP gap) into the same generic answer; keeper picks
    don't draw from the pool at all, so they don't advance the cursor
    either.
    """
    order_data = _load_league_rules_json("draft_order_2026.json")
    round1_order = order_data["round_1_order"]
    num_rounds = order_data["num_rounds"]

    by_first_name = {owner_first_name(t["owners"]).lower(): t for t in guide}
    missing = [o for o in round1_order if o.lower() not in by_first_name]
    if missing:
        raise ValueError(f"draft_order_2026.json names not found among teams: {missing}")
    teams_in_order = [by_first_name[o.lower()] for o in round1_order]

    rounds = []
    overall = 0
    open_cursor = 0
    for round_num in range(1, num_rounds + 1):
        order = teams_in_order if round_num % 2 == 1 else list(reversed(teams_in_order))
        picks = []
        for slot, team in enumerate(order, start=1):
            overall += 1
            keeper = next(
                (k for k in team["locked_keepers_2026"] if k["keeper_cost_round_2026"] == round_num),
                None,
            )
            adp_context = None
            if not keeper:
                adp_context = [
                    {
                        "name": p["name"],
                        "position": p["position"],
                        "pro_team": p["pro_team"],
                        "adjusted_rank": p["adjusted_rank"],
                    }
                    for p in _pick_adp_context(adp_unkept, open_cursor)
                ]
                open_cursor += 1
            picks.append(
                {
                    "overall_pick": overall,
                    "slot_in_round": slot,
                    "team_id": team["team_id"],
                    "team_name": team["team_name"],
                    "owners": team["owners"],
                    "logo": team.get("logo"),
                    "keeper": keeper,
                    "adp_context": adp_context,
                }
            )
        rounds.append({"round": round_num, "picks": picks})

    teams_summary = []
    for team in teams_in_order:
        kept_rounds = {k["keeper_cost_round_2026"] for k in team["locked_keepers_2026"]}
        teams_summary.append(
            {
                "team_id": team["team_id"],
                "team_name": team["team_name"],
                "owners": team["owners"],
                "logo": team.get("logo"),
                "locked_keepers_2026": team["locked_keepers_2026"],
                "open_rounds": [r for r in range(1, num_rounds + 1) if r not in kept_rounds],
            }
        )

    return {
        "num_rounds": num_rounds,
        "num_teams": len(teams_in_order),
        "round_1_order": round1_order,
        "rounds": rounds,
        "teams": teams_summary,
    }


def main():
    draft_2025 = load(2025, "draft.json")
    rosters_2025 = load(2025, "rosters.json")
    rosters_2026 = load(2026, "rosters.json")
    teams_2026 = {t["id"]: t for t in load(2026, "teams.json")}

    draft_info_by_pid = {
        p["player_id"]: p for p in draft_2025 if p["player_id"]
    }
    end_of_2025_pids = {p["player_id"] for players in rosters_2025.values() for p in players}

    # Figure out which player IDs we'll need stats for, up front.
    all_roster_pids = {p["player_id"] for players in rosters_2026.values() for p in players}

    pool = fetch_player_pool(LEAGUE_ID, CURRENT_SEASON, limit=600)
    missing = sorted(all_roster_pids - pool.keys())
    pool.update(fetch_players_by_id(LEAGUE_ID, CURRENT_SEASON, missing))

    # Position rank vs. the full pool (not just this league's draft pool).
    by_position_actual = defaultdict(list)
    by_position_projected = defaultdict(list)
    for pid, player in pool.items():
        pos = player["defaultPositionId"]
        actual = get_points(player, 0, 2025)
        projected = get_points(player, 1, 2026)
        if actual is not None:
            by_position_actual[pos].append((pid, actual))
        if projected is not None:
            by_position_projected[pos].append((pid, projected))

    rank_actual_2025 = {}
    for pos, lst in by_position_actual.items():
        lst.sort(key=lambda x: -x[1])
        for i, (pid, _) in enumerate(lst, 1):
            rank_actual_2025[pid] = i

    rank_projected_2026 = {}
    for pos, lst in by_position_projected.items():
        lst.sort(key=lambda x: -x[1])
        for i, (pid, _) in enumerate(lst, 1):
            rank_projected_2026[pid] = i

    guide = []
    for team_id_str, players in rosters_2026.items():
        team_id = int(team_id_str)
        team = teams_2026[team_id]

        candidates = []
        ineligible = []
        for p in players:
            pid = p["player_id"]
            draft_pick = draft_info_by_pid.get(pid)

            if draft_pick is None:
                ineligible.append({**p, "reason": "not drafted in 2025 (waiver/FA addition)"})
                continue
            if pid not in end_of_2025_pids:
                ineligible.append({**p, "reason": "not on any roster at end of 2025 season"})
                continue

            original_round = draft_pick["round"]
            original_pick_in_round = draft_pick["round_pick"]
            is_first_round = original_round == 1
            cost_round = 1 if is_first_round else original_round - 1
            cost_overall_estimate = (cost_round - 1) * NUM_TEAMS + original_pick_in_round

            player_pool_entry = pool.get(pid)
            superflex_rank = None
            if player_pool_entry:
                superflex_rank = (
                    player_pool_entry.get("draftRanksByRankType", {})
                    .get("SUPERFLEX", {})
                    .get("rank")
                )
            adp_round, adp_pick = to_round_pick(superflex_rank)

            vig = (cost_overall_estimate - superflex_rank) if superflex_rank else None

            candidates.append(
                {
                    **p,
                    "drafted_round_2025": original_round,
                    "drafted_pick_2025": f"{original_round}.{original_pick_in_round:02d}",
                    "drafted_overall_2025": draft_pick["overall_pick"],
                    "points_actual_2025": get_points(player_pool_entry, 0, 2025) if player_pool_entry else None,
                    "position_rank_actual_2025": rank_actual_2025.get(pid),
                    "points_projected_2026": get_points(player_pool_entry, 1, 2026) if player_pool_entry else None,
                    "position_rank_projected_2026": rank_projected_2026.get(pid),
                    "adp_superflex_rank": superflex_rank,
                    "adp_pick_estimate": f"{adp_round}.{adp_pick:02d}" if adp_round else None,
                    "keeper_cost_round_2026": cost_round,
                    "keeper_cost_pick_estimate": f"{cost_round}.{original_pick_in_round:02d}",
                    "is_first_round_pick": is_first_round,
                    "vig": vig,
                }
            )

        by_round = defaultdict(list)
        for c in candidates:
            by_round[c["drafted_round_2025"]].append(c["name"])
        for c in candidates:
            dupes = by_round[c["drafted_round_2025"]]
            c["shares_round_with"] = [n for n in dupes if n != c["name"]]

        round1_candidates = [c["name"] for c in candidates if c["drafted_round_2025"] == 1]
        has_round2 = any(c["drafted_round_2025"] == 2 for c in candidates)

        candidates.sort(key=lambda c: c["drafted_round_2025"])

        # Suggested keeper spread: shortlist of premium (costs round 1-2),
        # mid (round 3-6), and value (round 7+) candidates, best-value
        # (highest vig) first within each band. This is a portfolio
        # heuristic, not a rule - won't always have a fit in every band.
        #
        # Keepers are never mandatory - if nobody in a band is a good deal,
        # it's better to let those slots go back into the draft pool than
        # keep a bad price. So anything worse than a full round's overpay
        # (vig < -NUM_TEAMS picks) is excluded from the shortlist entirely.
        NEGATIVE_VIG_FLOOR = -NUM_TEAMS

        def shortlist_in_band(lo, hi, n=3):
            band = [
                c
                for c in candidates
                if c["vig"] is not None
                and c["vig"] >= NEGATIVE_VIG_FLOOR
                and lo <= c["keeper_cost_round_2026"] <= hi
            ]
            band.sort(key=lambda c: -c["vig"])
            return band[:n]

        premium = shortlist_in_band(1, 2)
        mid = shortlist_in_band(3, 6)
        value = shortlist_in_band(7, 99)

        qualifying = premium + mid + value
        best_overall = max(qualifying, key=lambda c: c["vig"]) if qualifying else None
        for c in candidates:
            c["is_top_value"] = bool(best_overall and c["player_id"] == best_overall["player_id"])

        guide.append(
            {
                "team_id": team_id,
                "team_name": team["name"],
                "owners": team["owners"],
                "logo": team.get("logo"),
                "candidates": candidates,
                "ineligible": ineligible,
                "cannot_keep_both_round1_and_round2": len(round1_candidates) == 1 and has_round2,
                "cannot_keep_multiple_round1": len(round1_candidates) > 1,
                "round1_candidates": round1_candidates,
                "suggested_plan": {
                    "premium": premium,
                    "mid": mid,
                    "value": value,
                },
            }
        )

    mark_kept_2026(guide)

    guide.sort(key=lambda g: " & ".join(g["owners"]))
    (DOCS_DATA / "keeper_guide_2026.json").write_text(json.dumps(guide, indent=2))
    print(f"Wrote keeper_guide_2026.json for {len(guide)} teams")

    adp = []
    for pid, player in pool.items():
        ranks = player.get("draftRanksByRankType", {})
        superflex_rank = ranks.get("SUPERFLEX", {}).get("rank")
        if superflex_rank is None:
            continue
        adp.append(
            {
                "player_id": pid,
                "name": player["fullName"],
                "position": POSITION_MAP.get(player["defaultPositionId"], player["defaultPositionId"]),
                "pro_team": PRO_TEAM_MAP.get(player["proTeamId"], player["proTeamId"]),
                "superflex_rank": superflex_rank,
                "standard_rank": ranks.get("STANDARD", {}).get("rank"),
            }
        )
    adp.sort(key=lambda p: p["superflex_rank"])

    kept_player_ids = {
        c["player_id"] for t in guide for c in t["candidates"] if c.get("kept_2026")
    }
    adp_unkept = [p for p in adp if p["player_id"] not in kept_player_ids]
    for i, p in enumerate(adp_unkept, 1):
        p["adjusted_rank"] = i
    (DOCS_DATA / "adp_unkept_2026.json").write_text(json.dumps(adp_unkept, indent=2))
    print(f"Wrote adp_unkept_2026.json ({len(adp_unkept)} players, {len(kept_player_ids)} kept players removed)")

    draft_guide = build_draft_guide(guide, adp_unkept)
    (DOCS_DATA / "draft_guide_2026.json").write_text(json.dumps(draft_guide, indent=2))
    print(f"Wrote draft_guide_2026.json ({draft_guide['num_rounds']} rounds x {draft_guide['num_teams']} teams)")


if __name__ == "__main__":
    main()
