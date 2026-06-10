from __future__ import annotations

import csv
import json
import re
from datetime import datetime, timezone
from pathlib import Path


def tourlist_links(tour) -> list[str]:
    path = Path(tour["state_path"]) / "tourlist.txt"
    if not path.exists():
        return []
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def tour_history_dates(tour) -> dict[str, str]:
    history_path = Path(tour["state_path"]) / "elo_history.json"
    if not history_path.exists():
        return {}
    try:
        with history_path.open(encoding="utf-8") as f:
            history = json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}
    return {str(entry.get("tour_id", "")).lower(): str(entry.get("time", "")) for entry in history if entry.get("tour_id")}


def tour_history_entries(tour) -> list[dict]:
    history_path = Path(tour["state_path"]) / "elo_history.json"
    if not history_path.exists():
        return []
    try:
        with history_path.open(encoding="utf-8") as f:
            history = json.load(f)
    except (OSError, json.JSONDecodeError):
        return []
    return history if isinstance(history, list) else []


def history_sort_value(value) -> float:
    if not value:
        return float("-inf")
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return float("-inf")
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.timestamp()


def tour_id_from_link(link: str) -> str:
    link = link.rstrip("/")
    return link.split("/")[-1].split("?")[0].lower()


def previous_tour_rows(tour) -> list[tuple[str, int, str, str, str]]:
    stats_path = Path(tour["state_path"]) / "stats.csv"
    if not stats_path.exists():
        return []
    counts = {}
    try:
        with stats_path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                timestamp = (row.get("Timestamp") or "").strip()
                if timestamp:
                    counts[timestamp] = counts.get(timestamp, 0) + 1
    except OSError:
        return []

    rows = []
    for index, (timestamp, count) in enumerate(counts.items()):
        detail = f"{count} players"
        rows.append((timestamp, index, timestamp, detail, timestamp))
    rows.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return rows


def inhouse_history_rows(tour) -> list[tuple[str, int, str, str, str]]:
    rows = []
    for fallback_index, entry in enumerate(tour_history_entries(tour)):
        event_time = str(entry.get("time", ""))
        event_id = str(entry.get("tour_id", ""))
        if not event_id:
            continue
        date_label = event_time[:10] if event_time else "No date"
        teams = entry.get("teams", {})
        if isinstance(teams, dict) and teams:
            detail = f"{event_time[:19]}  {len(teams)} teams"
        else:
            detail = event_time[:19] if event_time else event_id
        rows.append((event_time, fallback_index, date_label, detail, event_id))
    rows.sort(key=lambda item: (history_sort_value(item[0]), item[1]), reverse=True)
    return rows


def latest_changelog_path(tour) -> Path:
    return Path(tour["state_path"]) / "elo_history_latest.json"


def selected_changelog_entry(tour, selected_tour_id=None):
    if selected_tour_id:
        history_path = Path(tour["state_path"]) / "elo_history.json"
        if not history_path.exists():
            raise FileNotFoundError(f"No elo_history.json found for {tour['label']}. Run eloscrape first.")
        try:
            history = json.loads(history_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"Could not read elo_history.json for {tour['label']}.") from exc
        selected_key = str(selected_tour_id).strip().lower()
        for entry in history:
            if str(entry.get("tour_id", "")).strip().lower() == selected_key:
                return entry
        raise ValueError(f"No changelog found for selected history item {selected_tour_id}.")

    changelog_path = latest_changelog_path(tour)
    if not changelog_path.exists():
        raise FileNotFoundError(f"No elo_history_latest.json found for {tour['label']}. Run eloscrape first.")
    try:
        return json.loads(changelog_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Could not read elo_history_latest.json for {tour['label']}.") from exc


def selected_changelog_text(tour, selected_tour_id=None) -> str:
    return json.dumps(selected_changelog_entry(tour, selected_tour_id), indent=2, ensure_ascii=False)


def latest_changelog_text(tour) -> str:
    changelog_path = latest_changelog_path(tour)
    if not changelog_path.exists():
        raise FileNotFoundError(f"No elo_history_latest.json found for {tour['label']}. Run eloscrape first.")

    changelog_text = changelog_path.read_text(encoding="utf-8")
    try:
        return json.dumps(json.loads(changelog_text), indent=2, ensure_ascii=False)
    except json.JSONDecodeError:
        return changelog_text


def safe_history_filename(selected_tour_id=None) -> str:
    safe_id = re.sub(r"[^A-Za-z0-9_-]+", "_", selected_tour_id or "latest").strip("_") or "latest"
    return f"{safe_id}_elo_history.json"
