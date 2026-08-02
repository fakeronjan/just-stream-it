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


def compute_standings(matchups, teams):
    """This league's own final_rank (ESPN's rankCalculatedFinal) is wrong for
    our purposes: ESPN derives it from placement games (a "3rd place game",
    a "9th place game", etc.) that this league doesn't treat as real -
    the actual rule is (a) playoff-bracket teams ranked by how far they got
    (order eliminated), tiebreak = regular-season record then points_for,
    and (b) everyone who didn't make the real championship bracket ranked
    purely by regular-season record then points_for, ignoring whatever
    consolation-ladder games ESPN also scheduled for them in weeks 15-17.

    The championship bracket itself isn't hardcoded to N teams - it's
    traced from the actual bracket tree, walking backward from the final
    each round to find that round's opponents, so byes (top seeds skip
    round 1) fall out naturally instead of needing special-casing.
    """
    teams_by_id = {t["id"]: t for t in teams}
    playoff_games = [m for m in matchups if m["is_playoffs"]]
    playoff_weeks = sorted({m["week"] for m in playoff_games})

    loss_counts = defaultdict(int)
    for m in playoff_games:
        loser_id = m["away_team_id"] if m["winner"] == "HOME" else m["home_team_id"]
        loss_counts[loser_id] += 1
    champ_id = next(t["id"] for t in teams if loss_counts.get(t["id"], 0) == 0)

    def opponent_in_week(team_id, week):
        game = next(
            (m for m in playoff_games if m["week"] == week and team_id in (m["home_team_id"], m["away_team_id"])),
            None,
        )
        if not game:
            return None
        return game["away_team_id"] if game["home_team_id"] == team_id else game["home_team_id"]

    tiers = [[champ_id]]  # tiers[0] = champion, [1] = runner-up, [2] = semifinal losers, ...
    alive_so_far = {champ_id}
    for week in reversed(playoff_weeks):
        new_tier = set()
        for team_id in [tid for tier in tiers for tid in tier]:
            opp_id = opponent_in_week(team_id, week)
            if opp_id is not None and opp_id not in alive_so_far:
                new_tier.add(opp_id)
        if new_tier:
            tiers.append(sorted(new_tier))
            alive_so_far |= new_tier

    def tiebreak_key(team_id):
        t = teams_by_id[team_id]
        return (-t["wins"], -t["points_for"])

    def status_for(tier_idx):
        if tier_idx == 0:
            return "champion"
        if tier_idx == 1:
            return "runner_up"
        return "playoff"

    standings = []
    for tier_idx, tier in enumerate(tiers):
        for team_id in sorted(tier, key=tiebreak_key):
            standings.append({
                "team_id": team_id,
                "status": status_for(tier_idx),
                "eliminated_round": None if tier_idx <= 1 else len(tiers) - tier_idx,
            })

    bracket_ids = alive_so_far
    non_bracket = sorted((t["id"] for t in teams if t["id"] not in bracket_ids), key=tiebreak_key)
    for team_id in non_bracket:
        standings.append({"team_id": team_id, "status": "non_playoff", "eliminated_round": None})

    for i, row in enumerate(standings):
        row["rank"] = i + 1
    return standings


def compute_upsets(matchups, rank_by_team):
    """Upset size = winner's corrected final rank minus loser's (see
    compute_standings) - positive and large means a weak team beat a
    strong one.
    """
    upsets = []
    for m in matchups:
        if m["winner"] not in ("HOME", "AWAY"):
            continue
        winner_id = m["home_team_id"] if m["winner"] == "HOME" else m["away_team_id"]
        loser_id = m["away_team_id"] if m["winner"] == "HOME" else m["home_team_id"]
        winner_score = m["home_score"] if m["winner"] == "HOME" else m["away_score"]
        loser_score = m["away_score"] if m["winner"] == "HOME" else m["home_score"]
        winner_rank = rank_by_team.get(winner_id, 99)
        loser_rank = rank_by_team.get(loser_id, 99)
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


def compute_player_extremes(weekly_boxscores, nfl_schedule):
    performances = []
    for week, teams in weekly_boxscores.items():
        week_schedule = nfl_schedule.get(week, {})
        for team_id, players in teams.items():
            for p in players:
                if not p["started"]:
                    continue
                game = week_schedule.get(p.get("pro_team"))
                performances.append(
                    {
                        "week": int(week),
                        "team_id": int(team_id),
                        "player_id": p["player_id"],
                        "name": p["name"],
                        "position": p["position"],
                        "points": p["points"],
                        "pro_team": p.get("pro_team"),
                        "pro_opponent": game["opponent"] if game else None,
                        "pro_home": game["home"] if game else None,
                        "pro_team_score": game["team_score"] if game else None,
                        "pro_opponent_score": game["opponent_score"] if game else None,
                        "stat_line": p.get("stat_line", ""),
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
    player left that team again. Also returns the number of games they
    actually started in that window, for a per-game rate alongside the total.
    """
    events = timeline.get(player_id, [])
    later_weeks = [w for w, _, _ in events if w > week_start]
    week_end = min(later_weeks) if later_weeks else total_weeks + 1
    total = 0.0
    games_started = 0
    for week in range(week_start, week_end):
        for p in weekly_boxscores.get(str(week), {}).get(str(team_id), []):
            if p["player_id"] == player_id and p["started"]:
                total += p["points"] or 0.0
                games_started += 1
    return round(total, 2), games_started, week_end - 1


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
            points, games_started, week_end = custody_points(
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
                    "games_started": games_started,
                    "points_per_game": round(points / games_started, 2) if games_started else 0.0,
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
                points, games_started, week_end = custody_points(
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
                        "games_started": games_started,
                        "points_per_game": round(points / games_started, 2) if games_started else 0.0,
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
    matchups = load(season, "matchups.json")
    weekly_boxscores = load(season, "weekly_boxscores.json")
    draft_picks = load(season, "draft.json")
    transactions = load(season, "transactions.json")
    nfl_schedule = load(season, "nfl_schedule.json")
    total_weeks = max(m["week"] for m in matchups)

    pickups, trades = compute_acquisition_value(draft_picks, transactions, weekly_boxscores, total_weeks)
    standings = compute_standings(matchups, teams)
    rank_by_team = {row["team_id"]: row["rank"] for row in standings}

    moments = {
        "standings": standings,
        "upsets": compute_upsets(matchups, rank_by_team),
        "weekly_team_extremes": compute_weekly_team_extremes(matchups),
        "player_extremes": compute_player_extremes(weekly_boxscores, nfl_schedule),
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
