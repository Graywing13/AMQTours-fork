from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd


SEPARATOR = "|"


def normalize_player_id(player_id: Any) -> str | None:
    if player_id is None:
        return None
    text = str(player_id).strip()
    if not text or text.lower() == "nan":
        return None
    try:
        number = float(text)
    except ValueError:
        return text
    if number.is_integer():
        return str(int(number))
    return text


def normalize_player_name(name: Any) -> str:
    return str(name).strip().lower()


def composite_key(player_id: Any, player_name: Any) -> str:
    normalized_id = normalize_player_id(player_id)
    if normalized_id is None:
        normalized_id = f"name:{normalize_player_name(player_name)}"
    return f"{normalized_id}{SEPARATOR}{normalize_player_name(player_name)}"


def parse_composite_key(key: Any) -> tuple[str, str] | None:
    if isinstance(key, tuple) and len(key) == 2:
        player_id, player_name = key
        normalized_id = normalize_player_id(player_id)
        if normalized_id is None:
            normalized_id = f"name:{normalize_player_name(player_name)}"
        return normalized_id, normalize_player_name(player_name)

    text = str(key)
    if SEPARATOR not in text:
        return None
    player_id, player_name = text.split(SEPARATOR, 1)
    normalized_id = normalize_player_id(player_id)
    if normalized_id is None or not player_name.strip():
        return None
    return normalized_id, normalize_player_name(player_name)


def load_json_dict(path: str | Path) -> dict:
    path = Path(path)
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, dict) else {}


def load_alias_table(ids_path: str | Path | None) -> pd.DataFrame:
    if not ids_path:
        return pd.DataFrame(columns=["Player Name", "Player ID"])
    path = Path(ids_path)
    if not path.exists():
        return pd.DataFrame(columns=["Player Name", "Player ID"])
    aliases = pd.read_csv(path)
    if "Player Name" not in aliases.columns or "Player ID" not in aliases.columns:
        return pd.DataFrame(columns=["Player Name", "Player ID"])
    aliases = aliases[["Player Name", "Player ID"]].copy()
    aliases["Player Name"] = aliases["Player Name"].astype(str).str.strip().str.lower()
    aliases["Player ID"] = aliases["Player ID"].map(normalize_player_id)
    aliases = aliases.dropna(subset=["Player ID"])
    aliases = aliases[aliases["Player Name"] != ""]
    return aliases


def alias_maps(ids_path: str | Path | None) -> tuple[dict[str, str], dict[str, str]]:
    aliases = load_alias_table(ids_path)
    if aliases.empty:
        return {}, {}
    name_to_id = dict(zip(aliases["Player Name"], aliases["Player ID"]))
    id_to_primary = aliases.groupby("Player ID")["Player Name"].first().to_dict()
    return name_to_id, id_to_primary


def dict_to_composite(data: dict, ids_path: str | Path | None = None) -> dict[tuple[str, str], float]:
    name_to_id, _id_to_primary = alias_maps(ids_path)
    result = {}
    for key, value in data.items():
        parsed = parse_composite_key(key)
        if parsed is None:
            player_name = normalize_player_name(key)
            player_id = name_to_id.get(player_name)
            parsed = (player_id or f"name:{player_name}", player_name)
        try:
            result[parsed] = float(value)
        except (TypeError, ValueError):
            continue
    return result


def dict_to_names(data: dict, ids_path: str | Path | None = None, prefer_primary: bool = True) -> dict[str, float]:
    _name_to_id, id_to_primary = alias_maps(ids_path)
    result = {}
    for key, value in data.items():
        parsed = parse_composite_key(key)
        if parsed is None:
            player_name = normalize_player_name(key)
        else:
            player_id, embedded_name = parsed
            player_name = id_to_primary.get(player_id, embedded_name) if prefer_primary else embedded_name
        try:
            result[player_name] = float(value)
        except (TypeError, ValueError):
            continue
    return result


def dict_to_ids(data: dict, ids_path: str | Path | None = None) -> dict[str, float]:
    name_to_id, _id_to_primary = alias_maps(ids_path)
    result = {}
    for key, value in data.items():
        parsed = parse_composite_key(key)
        if parsed is None:
            player_name = normalize_player_name(key)
            player_id = name_to_id.get(player_name) or player_name
        else:
            player_id, _player_name = parsed
        try:
            result[player_id] = float(value)
        except (TypeError, ValueError):
            continue
    return result


def load_elos(path: str | Path, ids_path: str | Path | None = None, key_format: str = "name") -> dict:
    data = load_json_dict(path)
    if key_format == "composite":
        return dict_to_composite(data, ids_path)
    if key_format == "id":
        return dict_to_ids(data, ids_path)
    if key_format == "raw":
        return data
    return dict_to_names(data, ids_path)


def save_elos(data: dict, path: str | Path, ids_path: str | Path | None = None, key_format: str = "composite") -> None:
    path = Path(path)
    if key_format == "name":
        payload = dict_to_names(data, ids_path)
    elif key_format == "raw":
        payload = data
    else:
        composite = dict_to_composite(data, ids_path)
        payload = {composite_key(player_id, player_name): value for (player_id, player_name), value in composite.items()}
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=4)


def save_composite_dict_to_json(data_dict: dict, file_path: str | Path) -> None:
    save_elos(data_dict, file_path, key_format="composite")


def load_composite_dict_from_json(file_path: str | Path) -> dict[tuple[str, str], float]:
    return load_elos(file_path, key_format="composite")


def rank_dict_from_frame(frame, elo_column: str = "ELO") -> dict[tuple[str, str], float]:
    return {
        (normalize_player_id(player_id) or f"name:{normalize_player_name(player_name)}", normalize_player_name(player_name)): round(float(elo), 3)
        for player_id, player_name, elo in zip(frame["Player ID"], frame["PlayerName"], frame[elo_column])
    }


def sheet_safe_json_text(elos_path: str | Path, ids_path: str | Path | None = None) -> str:
    return json.dumps(load_elos(elos_path, ids_path, key_format="name"), indent=4)
