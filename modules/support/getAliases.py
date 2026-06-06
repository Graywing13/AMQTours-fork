from itertools import combinations
import json
import os
import pandas as pd

def getAliases(ALIAS_PATH):
    """Deprecated function"""
    aliases = {}
    with open(ALIAS_PATH, 'r', encoding='utf-8') as f:
        # tab-separated list of aliases, where every line has all names of one player 
        # first of each line should be the main name (current bot name)
        for line in f:
            alias_list = line.split('\t')
            main_name = alias_list[0].strip().lower()
            for alias in alias_list:
                aliases[alias.strip().lower()] = main_name
        
    return aliases

def getAliasesDF(idtable):
    if not os.path.exists(idtable) and os.path.basename(os.path.dirname(idtable)) == "usual_house":
        directory = os.path.dirname(idtable)
        elos_path = os.path.join(directory, "elos.json")
        aliases_path = os.path.join(os.path.dirname(os.path.dirname(directory)), "aliases.txt")
        if os.path.exists(elos_path):
            with open(elos_path, encoding="utf-8") as f:
                elo_names = [name.strip().lower() for name in json.load(f)]
            name_to_id = {name: idx for idx, name in enumerate(elo_names, 1)}
            rows = [{"Player Name": name, "Player ID": player_id} for name, player_id in name_to_id.items()]
            seen_names = set(elo_names)

            if os.path.exists(aliases_path):
                with open(aliases_path, encoding="utf-8") as f:
                    for line in f:
                        alias_group = [alias.strip().lower() for alias in line.split("\t") if alias.strip()]
                        primary_name = next((alias for alias in alias_group if alias in name_to_id), None)
                        if primary_name:
                            for alias in alias_group:
                                if alias not in seen_names:
                                    rows.append({"Player Name": alias, "Player ID": name_to_id[primary_name]})
                                    seen_names.add(alias)

            return pd.DataFrame(rows)
    alias_df = pd.read_csv(idtable)
    return alias_df

def getAliasesID(idtable, player_key):
    idtable["Player Name"] = idtable["Player Name"].str.strip().str.lower()
    alias_to_id = dict(zip(idtable["Player Name"], idtable["Player ID"]))

    return alias_to_id.get(player_key.strip().lower())

def getAliasesFirstName(idtable, player_id):
    id_to_primary_name = idtable.groupby("Player ID")["Player Name"].first().to_dict()

    return id_to_primary_name.get(player_id)

def getAliasesAllNames(idtable, player_id):
    idtable["Player Name"] = idtable["Player Name"].str.strip()
    id_to_all_names = idtable.groupby("Player ID")["Player Name"].apply(list).to_dict()
    
    return id_to_all_names.get(player_id, [])
