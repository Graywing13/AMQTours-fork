from __future__ import annotations

import json
from pathlib import Path

from modules.support.generateCodes import (
    generate_codes_cl_gr,
    generate_codes_ed_gr,
    generate_codes_in_gr,
    generate_codes_op_gr,
    generate_codes_usual_gr,
    generate_codes_watched_2009_gr,
    generate_codes_watched_28_gr,
    generate_codes_watched_5s_gr,
    generate_codes_watched_ed_gr,
    generate_codes_watched_gr,
    generate_codes_watched_in_gr,
    generate_codes_watched_in_no_chanting_gr,
    generate_codes_watched_op_gr,
)


LINKS = {
    "Stats Sheet": "https://docs.google.com/spreadsheets/d/1Fm6pMyXv7qhOQkLah4yX9HNow4WaDR4HJuAVMukQl34/edit?gid=2023469160#gid=2023469160",
    "Add Aliases": "https://docs.google.com/spreadsheets/d/1xEUK1U6FtCGE80gOk0JCRC1eLJF9ALgz4T4KuK-9vYc/edit?gid=1861712941#gid=1861712941",
    "Add Stall Minutes": "https://docs.google.com/spreadsheets/d/1xEUK1U6FtCGE80gOk0JCRC1eLJF9ALgz4T4KuK-9vYc/edit?gid=1279191862#gid=1279191862",
}

SETUP_TOURS = {"usual": "random", "watched": "watched"}

CATEGORIES = {
    "Random": [
        ("Usual", "usual"),
        ("OP", "random_op"),
        ("ED", "random_ed"),
        ("IN", "random_ins"),
        ("OPED", "random_oped"),
        ("Chanting", "random_chanting"),
    ],
    "Watched": [
        ("Watched", "watched"),
        ("OP", "watched_op"),
        ("ED", "watched_ed"),
        ("IN", "watched_ins"),
        ("IN -Chanting", "watched_ins_no_chanting"),
        ("-2009", "watched_x_2009"),
    ],
    "Speed": [
        ("2+8", "watched_2_8"),
        ("5", "watched_5s"),
    ],
    "Inhouse": [
        ("Random", "usual_house"),
        ("Watched", "watched_house"),
    ],
}

CODE_GENERATORS = {
    "usual_gr": generate_codes_usual_gr,
    "op_gr": generate_codes_op_gr,
    "ed_gr": generate_codes_ed_gr,
    "in_gr": generate_codes_in_gr,
    "cl_gr": generate_codes_cl_gr,
    "watched_gr": generate_codes_watched_gr,
    "watched_in_gr": generate_codes_watched_in_gr,
    "watched_in_no_chanting_gr": generate_codes_watched_in_no_chanting_gr,
    "watched_5s_gr": generate_codes_watched_5s_gr,
    "watched_28_gr": generate_codes_watched_28_gr,
    "watched_2009_gr": generate_codes_watched_2009_gr,
    "watched_ed_gr": generate_codes_watched_ed_gr,
    "watched_op_gr": generate_codes_watched_op_gr,
}


def load_setup_codes(path: str | Path) -> dict:
    try:
        with Path(path).open(encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}
