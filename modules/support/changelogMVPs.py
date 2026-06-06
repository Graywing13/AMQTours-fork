def makeChangelog(rank_dict, old_elos, changelog_path):
    elo_diff = {
        player: {
            "initial rank": round(float(old_elos[player]), 3),
            "new rank": round(float(rank_dict[player]), 3),
            "rating_change": round(float(rank_dict[player]) - float(old_elos[player]), 3),
        }
        for player in old_elos
        if player in rank_dict and abs(float(rank_dict[player]) - float(old_elos[player])) >= 0.15
    }

    elo_diff_str = "\n".join(
        f"{player}, old rank: {data['initial rank']}, new rank: {data['new rank']}, diff: {data['rating_change']}"
        for player, data in sorted(elo_diff.items(), key=lambda item: -item[1]["rating_change"])
    )

    with open(changelog_path, "w", encoding="utf-8") as f:
        f.write(elo_diff_str)


def format_mvps(last_tour_dict, old_old_elos):
    diff = {}
    for player, new_elo in last_tour_dict.items():
        old_elo = old_old_elos.get(player)
        if old_elo is None:
            old_elo = new_elo
        diff[player] = {
            "old": round(float(old_elo), 3),
            "new": round(float(new_elo), 3),
            "diff": round(float(new_elo) - float(old_elo), 3),
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
