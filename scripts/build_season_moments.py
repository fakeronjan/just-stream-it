"""Compute one-off "moments" superlatives for a season - upsets, weekly
extremes, bad bench decisions, injury burden. Pure local computation, no
new ESPN calls - everything here comes from matchups.json and
weekly_boxscores.json, which build_season_analytics.py already pulled.

Run after build_season_analytics.py (needs weekly_boxscores.json).
"""

import json
from collections import defaultdict
from pathlib import Path

DOCS_DATA = Path(__file__).parent.parent / "docs" / "data"


def load(season, name):
    return json.loads((DOCS_DATA / str(season) / name).read_text())


def team_label(teams_by_id, team_id):
    t = teams_by_id[team_id]
    return f"{' & '.join(t['owners'])} ({t['name']})"


def compute_upsets(matchups, teams_by_id):
    """Upset size = winner's final rank minus loser's final rank (final
    season standing as the "who was actually better" proxy) - positive and
    large means a weak team beat a strong one.
    """
    upsets = []
    for m in matchups:
        if m["winner"] not in ("HOME", "AWAY"):
            continue
        winner_id = m["home_team_id"] if m["winner"] == "HOME" else m["away_team_id"]
        loser_id = m["away_team_id"] if m["winner"] == "HOME" else m["home_team_id"]
        winner_score = m["home_score"] if m["winner"] == "HOME" else m["away_score"]
        loser_score = m["away_score"] if m["winner"] == "HOME" else m["home_score"]
        winner_rank = teams_by_id[winner_id]["final_rank"] or 99
        loser_rank = teams_by_id[loser_id]["final_rank"] or 99
        upsets.append(
            {
                "week": m["week"],
                "is_playoffs": m["is_playoffs"],
                "winner_team_id": winner_id,
                "loser_team_id": loser_id,
                "winner_final_rank": winner_rank,
                "loser_final_rank": loser_rank,
                "upset_size": winner_rank - loser_rank,
                "winner_score": winner_score,
                "loser_score": loser_score,
                "margin": round(winner_score - loser_score, 2),
            }
        )
    upsets.sort(key=lambda u: (-u["upset_size"], -u["margin"]))
    return upsets


def compute_weekly_team_extremes(matchups):
    all_scores = []
    for m in matchups:
        all_scores.append({"week": m["week"], "team_id": m["home_team_id"], "score": m["home_score"], "is_playoffs": m["is_playoffs"]})
        all_scores.append({"week": m["week"], "team_id": m["away_team_id"], "score": m["away_score"], "is_playoffs": m["is_playoffs"]})
    all_scores.sort(key=lambda s: -s["score"])
    return {
        "best_weeks": all_scores[:10],
        "worst_weeks": all_scores[::-1][:10],
    }


def compute_player_extremes(weekly_boxscores):
    performances = []
    for week, teams in weekly_boxscores.items():
        for team_id, players in teams.items():
            for p in players:
                if not p["started"]:
                    continue
                performances.append(
                    {
                        "week": int(week),
                        "team_id": int(team_id),
                        "player_id": p["player_id"],
                        "name": p["name"],
                        "position": p["position"],
                        "points": p["points"],
                    }
                )
    performances.sort(key=lambda p: -p["points"])
    return {
        "best_performances": performances[:10],
        "worst_performances": sorted(performances, key=lambda p: p["points"])[:10],
    }


def compute_bench_mistakes(weekly_boxscores):
    """For each team-week, the highest-scoring benched player (lineup slot
    BE specifically, not IR - an IR player usually wasn't a real "should've
    started them" choice) - both the single worst instance and each team's
    season-total points left on the bench.
    """
    instances = []
    season_totals = defaultdict(float)
    for week, teams in weekly_boxscores.items():
        for team_id, players in teams.items():
            benched = [p for p in players if not p["started"] and p["lineup_slot_id"] == 20]
            if not benched:
                continue
            best_benched = max(benched, key=lambda p: p["points"])
            instances.append(
                {
                    "week": int(week),
                    "team_id": int(team_id),
                    "player_id": best_benched["player_id"],
                    "name": best_benched["name"],
                    "position": best_benched["position"],
                    "points": best_benched["points"],
                }
            )
            season_totals[int(team_id)] += best_benched["points"]

    instances.sort(key=lambda i: -i["points"])
    season_totals_list = sorted(
        ({"team_id": tid, "points_left_on_bench": round(pts, 2)} for tid, pts in season_totals.items()),
        key=lambda x: -x["points_left_on_bench"],
    )
    return {"worst_single_instances": instances[:10], "season_totals": season_totals_list}


def build_arrival_timeline(draft_picks, transactions):
    """player_id -> sorted [(week, team_id, source), ...] - every event
    where a player joined a roster (draft, waiver/FA add, trade-in).
    """
    timeline = defaultdict(list)
    for p in draft_picks:
        if p["player_id"] is not None:
            timeline[p["player_id"]].append((1, p["team_id"], "DRAFT"))
    for t in transactions:
        if t["type"] in ("WAIVER", "FREEAGENT"):
            for item in t["items"]:
                if item["type"] == "ADD":
                    timeline[item["player_id"]].append((t["week"], item["to_team_id"], t["type"]))
        elif t["type"] == "TRADE_ACCEPT":
            for item in t["items"]:
                if item["type"] == "TRADE":
                    timeline[item["player_id"]].append((t["week"], item["to_team_id"], "TRADE"))
    for pid in timeline:
        timeline[pid].sort(key=lambda e: e[0])
    return timeline


def custody_points(timeline, weekly_boxscores, player_id, team_id, week_start, total_weeks):
    """Points this player scored (while started) for this team, from
    week_start up until the NEXT time they changed hands (or end of
    season) - so a trade/pickup's value doesn't keep accruing after the
    player left that team again.
    """
    events = timeline.get(player_id, [])
    later_weeks = [w for w, _, _ in events if w > week_start]
    week_end = min(later_weeks) if later_weeks else total_weeks + 1
    total = 0.0
    for week in range(week_start, week_end):
        for p in weekly_boxscores.get(str(week), {}).get(str(team_id), []):
            if p["player_id"] == player_id and p["started"]:
                total += p["points"] or 0.0
    return round(total, 2), week_end - 1


def build_player_lookup(weekly_boxscores):
    """player_id -> {name, position}, from any week/team they appear in -
    name and position don't change mid-season, so last-seen is fine.
    """
    lookup = {}
    for teams in weekly_boxscores.values():
        for players in teams.values():
            for p in players:
                lookup[p["player_id"]] = {"name": p["name"], "position": p["position"]}
    return lookup


def compute_acquisition_value(draft_picks, transactions, weekly_boxscores, total_weeks):
    timeline = build_arrival_timeline(draft_picks, transactions)
    player_lookup = build_player_lookup(weekly_boxscores)

    pickups = []
    for t in transactions:
        if t["type"] not in ("WAIVER", "FREEAGENT"):
            continue
        for item in t["items"]:
            if item["type"] != "ADD":
                continue
            points, week_end = custody_points(
                timeline, weekly_boxscores, item["player_id"], item["to_team_id"], t["week"], total_weeks
            )
            info = player_lookup.get(item["player_id"], {"name": "Unknown", "position": "?"})
            pickups.append(
                {
                    "player_id": item["player_id"],
                    "name": info["name"],
                    "position": info["position"],
                    "team_id": item["to_team_id"],
                    "week_added": t["week"],
                    "rostered_through_week": week_end,
                    "source": t["type"],
                    "points_while_rostered": points,
                }
            )
    pickups.sort(key=lambda x: -x["points_while_rostered"])

    trades = []
    for t in transactions:
        if t["type"] != "TRADE_ACCEPT":
            continue
        by_team = defaultdict(list)
        for item in t["items"]:
            if item["type"] == "TRADE":
                points, week_end = custody_points(
                    timeline, weekly_boxscores, item["player_id"], item["to_team_id"], t["week"], total_weeks
                )
                info = player_lookup.get(item["player_id"], {"name": "Unknown", "position": "?"})
                by_team[item["to_team_id"]].append(
                    {
                        "player_id": item["player_id"],
                        "name": info["name"],
                        "position": info["position"],
                        "points_while_rostered": points,
                        "rostered_through_week": week_end,
                    }
                )
        if not by_team:
            continue
        sides = [
            {
                "team_id": team_id,
                "players_received": players,
                "total_points": round(sum(p["points_while_rostered"] for p in players), 2),
            }
            for team_id, players in by_team.items()
        ]
        trades.append({"trade_id": t["id"], "week": t["week"], "sides": sides})

    return pickups, trades


def compute_rivalries(matchups):
    """Head-to-head pairs this season, closest average margin first. With
    only one season of history, "rivalry" really just means "closest
    series" - real multi-season rivalry tracking becomes possible once
    2026+ data exists.
    """
    pair_games = defaultdict(list)
    for m in matchups:
        if m["is_playoffs"] or m["winner"] not in ("HOME", "AWAY"):
            continue
        pair = tuple(sorted([m["home_team_id"], m["away_team_id"]]))
        margin = abs(m["home_score"] - m["away_score"])
        winner = m["home_team_id"] if m["winner"] == "HOME" else m["away_team_id"]
        pair_games[pair].append({"week": m["week"], "margin": round(margin, 2), "winner_team_id": winner})

    rivalries = []
    for pair, games in pair_games.items():
        wins = defaultdict(int)
        for g in games:
            wins[g["winner_team_id"]] += 1
        rivalries.append(
            {
                "team_ids": list(pair),
                "games": games,
                "avg_margin": round(sum(g["margin"] for g in games) / len(games), 2),
                "record": {pair[0]: wins.get(pair[0], 0), pair[1]: wins.get(pair[1], 0)},
            }
        )
    rivalries.sort(key=lambda r: r["avg_margin"])
    return rivalries


def compute_injury_burden(weekly_boxscores):
    """IR-slot usage as a proxy for injury burden (no true historical
    injury-status field is available - ESPN only exposes CURRENT status,
    not what it was during a past week - but a team using the IR slot is a
    reasonable signal they had a real injury to manage at the time).
    """
    weeks_on_ir = defaultdict(int)
    distinct_players_on_ir = defaultdict(set)
    for week, teams in weekly_boxscores.items():
        for team_id, players in teams.items():
            for p in players:
                if p["lineup_slot_id"] == 21:
                    weeks_on_ir[int(team_id)] += 1
                    distinct_players_on_ir[int(team_id)].add(p["name"])

    result = []
    for team_id in weeks_on_ir:
        result.append(
            {
                "team_id": team_id,
                "player_weeks_on_ir": weeks_on_ir[team_id],
                "distinct_players_on_ir": sorted(distinct_players_on_ir[team_id]),
            }
        )
    result.sort(key=lambda r: -r["player_weeks_on_ir"])
    return result


def main(season):
    teams = load(season, "teams.json")
    teams_by_id = {t["id"]: t for t in teams}
    matchups = load(season, "matchups.json")
    weekly_boxscores = load(season, "weekly_boxscores.json")
    draft_picks = load(season, "draft.json")
    transactions = load(season, "transactions.json")
    total_weeks = max(m["week"] for m in matchups)

    pickups, trades = compute_acquisition_value(draft_picks, transactions, weekly_boxscores, total_weeks)

    moments = {
        "upsets": compute_upsets(matchups, teams_by_id),
        "weekly_team_extremes": compute_weekly_team_extremes(matchups),
        "player_extremes": compute_player_extremes(weekly_boxscores),
        "bench_mistakes": compute_bench_mistakes(weekly_boxscores),
        "injury_burden": compute_injury_burden(weekly_boxscores),
        "best_waiver_pickups": pickups[:15],
        "trades": trades,
        "rivalries": compute_rivalries(matchups),
    }

    out_path = DOCS_DATA / str(season) / "season_moments.json"
    out_path.write_text(json.dumps(moments, indent=2))
    print(f"Wrote season_moments.json for {season}")


if __name__ == "__main__":
    import sys

    season = int(sys.argv[1]) if len(sys.argv) > 1 else 2025
    main(season)
