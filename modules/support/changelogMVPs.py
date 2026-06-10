from modules.support.readElos import normalize_player_id, normalize_player_name, parse_composite_key


def _elo_records(elos):
    records = []
    for key, value in elos.items():
        parsed = parse_composite_key(key)
        if parsed is None:
            player_id = None
            player_name = normalize_player_name(key)
        else:
            player_id, player_name = parsed
        try:
            elo = float(value)
        except (TypeError, ValueError):
            continue
        records.append({"id": normalize_player_id(player_id), "name": player_name, "elo": elo})
    return records


def _old_lookup(old_elos):
    by_id = {}
    by_name = {}
    for record in _elo_records(old_elos):
        if record["id"]:
            by_id[record["id"]] = record
        by_name[record["name"]] = record
    return by_id, by_name


def makeChangelog(rank_dict, old_elos, changelog_path):
    old_by_id, old_by_name = _old_lookup(old_elos)
    elo_diff = {}
    for new_record in _elo_records(rank_dict):
        old_record = None
        if new_record["id"]:
            old_record = old_by_id.get(new_record["id"])
        if old_record is None:
            old_record = old_by_name.get(new_record["name"])
        if old_record is None:
            continue

        diff = round(new_record["elo"] - old_record["elo"], 3)
        if abs(diff) < 0.15:
            continue
        elo_diff[new_record["name"]] = {
            "initial rank": round(old_record["elo"], 3),
            "new rank": round(new_record["elo"], 3),
            "rating_change": diff,
        }

    elo_diff_str = "\n".join(
        f"{player}, old rank: {data['initial rank']}, new rank: {data['new rank']}, diff: {data['rating_change']}"
        for player, data in sorted(elo_diff.items(), key=lambda item: -item[1]["rating_change"])
    )

    with open(changelog_path, "w", encoding="utf-8") as f:
        f.write(elo_diff_str)


def format_mvps(last_tour_dict, old_old_elos):
    old_by_id, old_by_name = _old_lookup(old_old_elos)
    diff = {}
    for record in _elo_records(last_tour_dict):
        old_record = None
        if record["id"]:
            old_record = old_by_id.get(record["id"])
        if old_record is None:
            old_record = old_by_name.get(record["name"])
        old_elo = old_record["elo"] if old_record else record["elo"]
        diff[record["name"]] = {
            "old": round(float(old_elo), 3),
            "new": round(record["elo"], 3),
            "diff": round(record["elo"] - float(old_elo), 3),
        }

    sorted_diff = sorted(diff.items(), key=lambda item: item[1]["diff"], reverse=True)
    lines = ["# Full PV List:"]
    for player, data in sorted_diff:
        lines.append(f"{player} played like a {data['new']}. (Current rank {data['old']}, Δ{data['diff']})")

    lines.append("")
    medals = [":first_place:", ":second_place:", ":third_place:"]
    for medal, (player, data) in zip(medals, sorted_diff[:3]):
        lines.append(f"{medal} {player}. Played like a {data['new']} rank (Current Rank: {data['old']}, Δ{data['diff']})")
    return "\n".join(lines) + "\n"


def makeMVPs(last_tour_dict, old_old_elos, mvps_path):
    with open(mvps_path, "w", encoding="utf-8") as f:
        f.write(format_mvps(last_tour_dict, old_old_elos))
