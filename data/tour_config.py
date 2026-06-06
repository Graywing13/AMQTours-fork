from __future__ import annotations

import json
from pathlib import Path


DATA_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = DATA_ROOT.parent
TOURS_CONFIG_PATH = PROJECT_ROOT / "config" / "tours.json"


def _load_config() -> dict:
    with TOURS_CONFIG_PATH.open(encoding="utf-8") as f:
        tours = json.load(f)

    for tour_id, tour in tours.items():
        tour["id"] = tour_id
        tour["state_path"] = str(PROJECT_ROOT / tour["state_dir"])
    return tours


TOURS = _load_config()
TOURS_BY_TYPE = {tour["tour_type"]: tour for tour in TOURS.values()}
TOURS_BY_ROUTE = {tour["route"]: tour for tour in TOURS.values()}


def get_tour(tour_type: str) -> dict:
    try:
        return TOURS_BY_TYPE[tour_type]
    except KeyError as exc:
        raise KeyError(f"Unknown tour type: {tour_type}") from exc


def get_tour_by_route(route: str) -> dict:
    try:
        return TOURS_BY_ROUTE[route]
    except KeyError as exc:
        raise KeyError(f"Unknown tour route: {route}") from exc


def tours_for_nav() -> dict[str, list[dict]]:
    groups: dict[str, list[dict]] = {}
    for tour in TOURS.values():
        groups.setdefault(tour["group"], []).append(tour)
    return groups
