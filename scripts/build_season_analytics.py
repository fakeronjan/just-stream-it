"""Build season-level "how did this roster get built, and how did it score"
analytics for a completed season - the raw material for superlatives
(transaction counts, % of points by acquisition source, % by position,
luck vs. schedule). Run after generate_data.py (needs draft.json and
matchups.json for the season).

Data model:
  - docs/data/{season}/transactions.json   cleaned transaction log
  - docs/data/{season}/weekly_boxscores.json   per-week/team/player lineup+points
  - docs/data/{season}/team_analytics.json   aggregated per-team season stats

How a player's weekly points get attributed to Draft/Trade/Pickup:
  A player can be drafted, dropped, picked up, traded, etc. over a season.
  "Who gets credit" for their points in a given week is whoever currently
  rosters them that week (ground truth: the weekly box score), attributed
  to however THAT team most recently acquired them as of that week. This
  is built as a timeline per player (draft pick + every ADD/TRADE-in event,
  each tagged with the week it happened), and for a given week we just take
  the latest timeline entry at or before that week.
"""

import json
from collections import defaultdict
from pathlib import Path

from config import CURRENT_SEASON, LEAGUE_ID
from espn_client import fetch_boxscore_week, fetch_transactions
from espn_maps import POSITION_MAP, PRO_TEAM_MAP

DOCS_DATA = Path(__file__).parent.parent / "docs" / "data"

BENCH_IR_SLOTS = {20, 21}  # BE, IR - not "started"


def load(season, name):
    return json.loads((DOCS_DATA / str(season) / name).read_text())


def clean_transactions(raw):
    """Keep only real, executed roster moves - drop proposals/declines and
    the empty-shell TRADE_ACCEPT records ESPN emits as a companion to the
    real one (the actual trade always has a sibling record with the same
    scoringPeriodId whose `items` list is non-empty).
    """
    keep_types = {"WAIVER", "FREEAGENT", "ROSTER", "TRADE_ACCEPT"}
    cleaned = []
    for t in raw:
        if t.get("status") != "EXECUTED" or t.get("type") not in keep_types:
            continue
        if t["type"] == "TRADE_ACCEPT" and not t.get("items"):
            continue
        cleaned.append(
            {
                "id": t["id"],
                "type": t["type"],
                "team_id": t.get("teamId"),
                "week": t["scoringPeriodId"],
                "items": [
                    {
                        "player_id": i["playerId"],
                        "from_team_id": i.get("fromTeamId"),
                        "to_team_id": i.get("toTeamId"),
                        "type": i.get("type"),
                    }
                    for i in t.get("items", [])
                ],
            }
        )
    return cleaned


def build_ownership_timeline(draft_picks, transactions):
    """player_id -> sorted [(week, source), ...] arrival events."""
    timeline = defaultdict(list)

    for p in draft_picks:
        if p["player_id"] is not None:
            timeline[p["player_id"]].append((1, "DRAFT"))

    for t in transactions:
        if t["type"] in ("WAIVER", "FREEAGENT"):
            source = "PICKUP"
            for item in t["items"]:
                if item["type"] == "ADD":
                    timeline[item["player_id"]].append((t["week"], source))
        elif t["type"] == "TRADE_ACCEPT":
            for item in t["items"]:
                if item["type"] == "TRADE":
                    timeline[item["player_id"]].append((t["week"], "TRADE"))

    for pid in timeline:
        timeline[pid].sort(key=lambda x: x[0])
    return timeline


def attribution_for(timeline, player_id, week):
    events = timeline.get(player_id)
    if not events:
        return "UNKNOWN"  # e.g. a player added before week 1 with no captured event
    applicable = [e for e in events if e[0] <= week]
    if not applicable:
        return events[0][1]  # week-1 edge case, use earliest known event
    return applicable[-1][1]


# ESPN's numeric stat-category IDs, empirically confirmed against real
# games (raw count x standard scoring formula == the appliedStats point
# contribution ESPN reports for that category) rather than assumed from a
# public mapping - see conversation history for the cross-checks. Only
# covers QB/RB/WR/TE (passing/rushing/receiving) - the stat categories a
# skill-position player's box score actually needs; K/D-ST use a different,
# unverified set of IDs and are deliberately left out rather than guessed.
STAT_IDS = {
    "pass_yds": 3,
    "pass_td": 4,
    "pass_int": 20,
    "rush_yds": 24,
    "rush_td": 25,
    "rec": 53,
    "rec_yds": 42,
    "rec_td": 43,
}


def format_stat_line(raw_stats):
    """Human-readable "223 rush yds, 2 rush TD, 4 rec, 45 rec yds" line
    from a player's raw per-week stat dict - only the categories that are
    actually nonzero, in passing/rushing/receiving order.
    """
    if not raw_stats:
        return ""
    order = [
        ("pass_yds", "pass yds"), ("pass_td", "pass TD"), ("pass_int", "INT"),
        ("rush_yds", "rush yds"), ("rush_td", "rush TD"),
        ("rec", "rec"), ("rec_yds", "rec yds"), ("rec_td", "rec TD"),
    ]
    parts = []
    for key, label in order:
        val = raw_stats.get(str(STAT_IDS[key]))
        if val:
            parts.append(f"{round(val)} {label}")
    return ", ".join(parts)


def build_weekly_boxscores(season, num_weeks):
    weeks = {}
    for week in range(1, num_weeks + 1):
        data = fetch_boxscore_week(LEAGUE_ID, season, week)
        team_rosters = {}
        for m in data.get("schedule", []):
            if m.get("matchupPeriodId") != week:
                continue
            for side in ("home", "away"):
                side_data = m.get(side)
                if not side_data:
                    continue
                team_id = side_data["teamId"]
                roster = side_data.get("rosterForCurrentScoringPeriod", {}).get("entries", [])
                players = []
                for e in roster:
                    p = e["playerPoolEntry"]["player"]
                    actual_stats = next(
                        (s["stats"] for s in p.get("stats", []) if s.get("statSourceId") == 0 and s.get("scoringPeriodId") == week),
                        {},
                    )
                    players.append(
                        {
                            "player_id": e["playerId"],
                            "name": p["fullName"],
                            "position": POSITION_MAP.get(p["defaultPositionId"], p["defaultPositionId"]),
                            "pro_team": PRO_TEAM_MAP.get(p["proTeamId"], p["proTeamId"]),
                            "lineup_slot_id": e["lineupSlotId"],
                            "started": e["lineupSlotId"] not in BENCH_IR_SLOTS,
                            "points": e["playerPoolEntry"].get("appliedStatTotal", 0.0),
                            "stat_line": format_stat_line(actual_stats),
                        }
                    )
                team_rosters[team_id] = players
        weeks[week] = team_rosters
        print(f"  week {week}: {len(team_rosters)} teams")
    return weeks


def compute_team_analytics(season, teams, transactions, timeline, weekly_boxscores, regular_season_weeks):
    stats = {t["id"]: {
        "team_id": t["id"],
        "owners": t["owners"],
        "transactions_count": 0,
        "trades_count": 0,
        "waiver_pickups": 0,
        "free_agent_pickups": 0,
        "drops": 0,
        "started_points_total": 0.0,
        "started_points_by_source": defaultdict(float),
        "started_points_by_position": defaultdict(float),
        "players_started": set(),
        "weekly_rank_log": [],  # (week, rank_1_to_12, won_matchup)
    } for t in teams}

    # transaction counts
    trade_ids_by_team = defaultdict(set)
    for t in transactions:
        if t["type"] == "WAIVER":
            for item in t["items"]:
                if item["type"] == "ADD":
                    stats[t["team_id"]]["waiver_pickups"] += 1
                    stats[t["team_id"]]["transactions_count"] += 1
                elif item["type"] == "DROP":
                    stats[t["team_id"]]["drops"] += 1
        elif t["type"] == "FREEAGENT":
            stats[t["team_id"]]["free_agent_pickups"] += 1
            stats[t["team_id"]]["transactions_count"] += 1
        elif t["type"] == "ROSTER":
            for item in t["items"]:
                if item["type"] == "DROP":
                    stats[t["team_id"]]["drops"] += 1
                    stats[t["team_id"]]["transactions_count"] += 1
        elif t["type"] == "TRADE_ACCEPT":
            teams_in_trade = {i["to_team_id"] for i in t["items"] if i["type"] == "TRADE"}
            teams_in_trade |= {i["from_team_id"] for i in t["items"] if i["type"] == "TRADE"}
            for team_id in teams_in_trade:
                if team_id in stats:
                    trade_ids_by_team[team_id].add(t["id"])

    for team_id, trade_ids in trade_ids_by_team.items():
        stats[team_id]["trades_count"] = len(trade_ids)
        stats[team_id]["transactions_count"] += len(trade_ids)

    # weekly started points, by source and position. Deliberately spans
    # ALL weeks including weeks 15-17, not just the 14-week regular season -
    # this league runs a consolation ladder (consolationLadderDisabled:
    # false), so non-playoff teams keep playing real games too. That means
    # started_points_total will be HIGHER than ESPN's own team.points_for
    # (which is regular-season-only) for anyone who wasn't eliminated after
    # week 14 with no consolation games - confirmed not a bug: team 9's
    # weeks 1-14 sum matches points_for (1909.74) exactly, and weeks 15-17
    # add the consolation-bracket games on top (413.38).
    for week, team_rosters in weekly_boxscores.items():
        for team_id, players in team_rosters.items():
            if team_id not in stats:
                continue
            for p in players:
                if not p["started"]:
                    continue
                pts = p["points"] or 0.0
                source = attribution_for(timeline, p["player_id"], week)
                stats[team_id]["started_points_total"] += pts
                stats[team_id]["started_points_by_source"][source] += pts
                stats[team_id]["started_points_by_position"][p["position"]] += pts
                stats[team_id]["players_started"].add(p["player_id"])

    # weekly rank / luck (regular season only - all 12 teams play every week)
    matchups = load(season, "matchups.json")
    for week in range(1, regular_season_weeks + 1):
        week_matchups = [m for m in matchups if m["week"] == week]
        scores = {}
        for m in week_matchups:
            scores[m["home_team_id"]] = m["home_score"]
            scores[m["away_team_id"]] = m["away_score"]
        ranked = sorted(scores.items(), key=lambda x: -x[1])
        rank_by_team = {team_id: i + 1 for i, (team_id, _) in enumerate(ranked)}
        for m in week_matchups:
            home_won = m["winner"] == "HOME"
            if m["home_team_id"] in stats:
                stats[m["home_team_id"]]["weekly_rank_log"].append((week, rank_by_team[m["home_team_id"]], home_won))
            if m["away_team_id"] in stats:
                stats[m["away_team_id"]]["weekly_rank_log"].append((week, rank_by_team[m["away_team_id"]], not home_won))

    num_teams = len(teams)
    results = []
    for team_id, s in stats.items():
        rank_log = s["weekly_rank_log"]
        all_play_wins = sum(num_teams - r for _, r, _ in rank_log)  # teams they outscored that week
        all_play_games = len(rank_log) * (num_teams - 1)
        actual_wins = sum(1 for _, _, won in rank_log if won)
        expected_wins = (all_play_wins / all_play_games * len(rank_log)) if all_play_games else 0
        bad_luck_losses = [wk for wk, r, won in rank_log if r <= 3 and not won]
        good_luck_wins = [wk for wk, r, won in rank_log if r >= num_teams - 2 and won]

        started_points_total = s["started_points_total"]
        results.append(
            {
                "team_id": team_id,
                "owners": s["owners"],
                "transactions_count": s["transactions_count"],
                "trades_count": s["trades_count"],
                "waiver_pickups": s["waiver_pickups"],
                "free_agent_pickups": s["free_agent_pickups"],
                "drops": s["drops"],
                "players_started_count": len(s["players_started"]),
                "started_points_total": round(started_points_total, 2),
                "started_points_by_source": {k: round(v, 2) for k, v in s["started_points_by_source"].items()},
                "started_points_pct_by_source": {
                    k: round(v / started_points_total * 100, 1) for k, v in s["started_points_by_source"].items()
                } if started_points_total else {},
                "started_points_by_position": {k: round(v, 2) for k, v in s["started_points_by_position"].items()},
                "started_points_pct_by_position": {
                    k: round(v / started_points_total * 100, 1) for k, v in s["started_points_by_position"].items()
                } if started_points_total else {},
                "actual_wins": actual_wins,
                "all_play_wins": all_play_wins,
                "all_play_games": all_play_games,
                "expected_wins": round(expected_wins, 2),
                "luck_index": round(actual_wins - expected_wins, 2),
                "bad_luck_loss_weeks": bad_luck_losses,
                "good_luck_win_weeks": good_luck_wins,
            }
        )

    results.sort(key=lambda r: " & ".join(r["owners"]))
    return results


def main(season):
    print(f"Building season analytics for {season}...")
    teams = load(season, "teams.json")
    draft_picks = load(season, "draft.json")
    matchup_settings_weeks = max(m["week"] for m in load(season, "matchups.json") if not m["is_playoffs"])

    print("Fetching transactions...")
    raw_txns = fetch_transactions(LEAGUE_ID, season)
    transactions = clean_transactions(raw_txns)
    print(f"  {len(raw_txns)} raw -> {len(transactions)} cleaned")

    timeline = build_ownership_timeline(draft_picks, transactions)

    print("Fetching weekly box scores...")
    total_weeks = max(m["week"] for m in load(season, "matchups.json"))
    weekly_boxscores = build_weekly_boxscores(season, total_weeks)

    analytics = compute_team_analytics(
        season, teams, transactions, timeline, weekly_boxscores, matchup_settings_weeks
    )

    season_dir = DOCS_DATA / str(season)
    (season_dir / "transactions.json").write_text(json.dumps(transactions, indent=2))
    (season_dir / "weekly_boxscores.json").write_text(json.dumps(weekly_boxscores, indent=2))
    (season_dir / "team_analytics.json").write_text(json.dumps(analytics, indent=2))
    print(f"Wrote transactions.json, weekly_boxscores.json, team_analytics.json for {season}")


if __name__ == "__main__":
    import sys

    season = int(sys.argv[1]) if len(sys.argv) > 1 else 2025
    main(season)
