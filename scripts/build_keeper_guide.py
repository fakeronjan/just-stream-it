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

DOCS_DATA = Path(__file__).parent.parent / "docs" / "data"
NUM_TEAMS = 12


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

        # Suggested keeper spread: one premium (costs round 1-2), one mid
        # (round 3-6), one cheap flier (round 7+), each the best-value
        # (highest vig) candidate available in that price band. This is a
        # portfolio heuristic, not a rule - won't always have a fit in every
        # band, and doesn't override the round-1-exclusivity conflicts above
        # (each band only ever contributes at most one recommended keeper,
        # so it can't recommend two players who'd both need the round-1 slot).
        def best_in_band(lo, hi):
            band = [c for c in candidates if c["vig"] is not None and lo <= c["keeper_cost_round_2026"] <= hi]
            return max(band, key=lambda c: c["vig"]) if band else None

        best_overall = best_in_band(1, 99)
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
                    "premium": best_in_band(1, 2),
                    "mid": best_in_band(3, 6),
                    "value": best_in_band(7, 99),
                },
            }
        )

    guide.sort(key=lambda g: " & ".join(g["owners"]))
    (DOCS_DATA / "keeper_guide_2026.json").write_text(json.dumps(guide, indent=2))
    print(f"Wrote keeper_guide_2026.json for {len(guide)} teams")


if __name__ == "__main__":
    main()
