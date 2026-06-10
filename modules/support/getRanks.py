from modules.support.getAliases import *
from modules.support.readElos import load_elos, normalize_player_id, parse_composite_key

def getRanks(RANKS_PATH, ELOS_PATH=None, ALIAS_PATH=None, returnFixup=False):
    ranks = {}
    raw_ranks = {}
    post_ranks_fixup = {}
    def process_rank(line):
        rank, rank_players = line.split(':', 2)
        rank = float(rank)
        rank_players = rank_players.strip().lower()
        for player in rank_players.split(','):
            if returnFixup:
                ranks[player.strip().lower()] = rank
                if player.strip() != '':
                    post_ranks_fixup[player.strip().lower()] = rank
            else:
                player_guesscount = player.rsplit(' [',2)
                playername = player_guesscount[0]
                ranks[playername.strip().lower()] = rank

    with open(RANKS_PATH, 'r') as file:
        for line in file.readlines():
            if not line.strip():
                continue
            process_rank(line)

    ranks = {player: rank for player, rank in ranks.items()}
    updated_elos = {}
    for player, rating in ranks.items():
        player_id = normalize_player_id(getAliasesID(ALIAS_PATH, player))
        updated_elos[player_id or player] = rating

    if ELOS_PATH:
        raw_ranks = load_elos(ELOS_PATH, key_format="raw")
        has_composite_keys = any(parse_composite_key(key) is not None for key in raw_ranks)
        cleaned_ranks_id = load_elos(ELOS_PATH, ids_path=None, key_format="id") if has_composite_keys else {}
        if not has_composite_keys:
            cleaned_ranks = {str(k).strip().lower(): v for k, v in raw_ranks.items()}
            cleaned_ranks_id = {}
            for player, rating in cleaned_ranks.items():
                player_id = normalize_player_id(getAliasesID(ALIAS_PATH, player))
                cleaned_ranks_id[player_id or player] = rating
        updated_elos.update(cleaned_ranks_id)

    if returnFixup:
        return updated_elos, raw_ranks, post_ranks_fixup
    else:
        return updated_elos
