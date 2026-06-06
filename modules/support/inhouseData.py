from __future__ import annotations

from collections import OrderedDict

from dateutil import parser as dp


SHEET_NAME = "NGM Stats Export v2"
WORKSHEET_NAME = "inhouseData"
VERSION = "1"
HEADERS = [
    "version",
    "inhouse_type",
    "event_id",
    "time",
    "round",
    "team1_id",
    "team1_display",
    "team2_id",
    "team2_display",
    "winner_id",
    "loser_id",
    "team1_score",
    "team2_score",
]


def inhouse_worksheet(directory):
    from modules.support.readCredentials import readCredentials

    gc = readCredentials(directory)
    sheet = gc.open(SHEET_NAME)
    try:
        wks = sheet.worksheet(WORKSHEET_NAME)
    except Exception:
        wks = sheet.add_worksheet(title=WORKSHEET_NAME, rows=1000, cols=len(HEADERS))
    ensure_headers(wks)
    return wks


def ensure_headers(wks):
    values = wks.get_all_values()
    if not values or not any(values[0]):
        for column, header in enumerate(HEADERS, start=1):
            wks.update_cell(1, column, header)
        return

    headers = values[0]
    missing = [header for header in HEADERS if header not in headers]
    for offset, header in enumerate(missing, start=len(headers) + 1):
        wks.update_cell(1, offset, header)


def append_inhouse_event(directory, event):
    wks = inhouse_worksheet(directory)
    rows = rows_for_event(event)
    if not rows:
        return 0
    try:
        wks.append_rows(rows, value_input_option="RAW")
    except TypeError:
        wks.append_rows(rows)
    return len(rows)


def rows_for_event(event):
    rows = []
    teams = event["teams"]
    for match in event["matches"]:
        team1_id = match["team1_id"]
        team2_id = match["team2_id"]
        rows.append([
            VERSION,
            event["inhouse_type"],
            event["tour_id"],
            event["time"],
            match["round"],
            team1_id,
            teams[team1_id]["display_name"],
            team2_id,
            teams[team2_id]["display_name"],
            match.get("winner"),
            match.get("loser"),
            match.get("team1_score", ""),
            match.get("team2_score", ""),
        ])
    return rows


def load_inhouse_tours(directory, inhouse_type):
    wks = inhouse_worksheet(directory)
    values = wks.get_all_values()
    if not values:
        return []

    headers = values[0]
    header_index = {header: headers.index(header) for header in HEADERS if header in headers}
    events = OrderedDict()
    for row in values[1:]:
        if cell(row, header_index, "version") != VERSION:
            continue
        if cell(row, header_index, "inhouse_type") != inhouse_type:
            continue

        event_id = cell(row, header_index, "event_id")
        if not event_id:
            continue
        event = events.setdefault(event_id, {
            "tour_id": event_id,
            "tour_url": "",
            "time": dp.parse(cell(row, header_index, "time")),
            "matches_by_round": OrderedDict(),
        })

        round_number = int(cell(row, header_index, "round"))
        team1_id = cell(row, header_index, "team1_id")
        team2_id = cell(row, header_index, "team2_id")
        match = {
            "round": round_number,
            "player1": {
                "id": team1_id,
                "display_name": cell(row, header_index, "team1_display"),
            },
            "player2": {
                "id": team2_id,
                "display_name": cell(row, header_index, "team2_display"),
            },
            "winner_id": empty_to_none(cell(row, header_index, "winner_id")),
            "loser_id": empty_to_none(cell(row, header_index, "loser_id")),
            "scores": {
                team1_id: cell(row, header_index, "team1_score"),
                team2_id: cell(row, header_index, "team2_score"),
            },
        }
        event["matches_by_round"].setdefault(str(round_number), []).append(match)
    return list(events.values())


def cell(row, header_index, name):
    index = header_index.get(name)
    if index is None or index >= len(row):
        return ""
    return row[index]


def empty_to_none(value):
    return None if value == "" else value
