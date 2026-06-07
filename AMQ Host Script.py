from __future__ import annotations

import importlib.util
import csv
import hashlib
import json
import re
import shutil
import subprocess
import sys
import threading
import asyncio
import tkinter as tk
import traceback
import webbrowser
from datetime import datetime, timezone
from pathlib import Path
from tkinter import ttk

PROJECT_ROOT = Path(__file__).resolve().parent
DATA_ROOT = PROJECT_ROOT / "data"
if str(DATA_ROOT) not in sys.path:
    sys.path.insert(0, str(DATA_ROOT))
REQUIREMENTS_PATH = DATA_ROOT / "requirements.txt"

PACKAGE_IMPORTS = {
    "trueskill": "trueskill",
    "beautifulsoup4": "bs4",
    "mpmath": "mpmath",
    "python-dateutil": "dateutil",
    "lxml": "lxml",
    "curl-cffi": "curl_cffi",
    "PuLP": "pulp",
    "pandas": "pandas",
    "gspread": "gspread",
    "numpy": "numpy",
}


def ensure_dependencies():
    if not REQUIREMENTS_PATH.exists():
        return
    missing = [package for package, module in PACKAGE_IMPORTS.items() if importlib.util.find_spec(module) is None]
    if missing:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", str(REQUIREMENTS_PATH)])


ensure_dependencies()

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
from modules.support.handleCodes import handleCodes
from tour_config import TOURS


LINKS = {
    "Stats Sheet": "https://docs.google.com/spreadsheets/d/1Fm6pMyXv7qhOQkLah4yX9HNow4WaDR4HJuAVMukQl34/edit?gid=2023469160#gid=2023469160",
    "Add Aliases": "https://docs.google.com/spreadsheets/d/1xEUK1U6FtCGE80gOk0JCRC1eLJF9ALgz4T4KuK-9vYc/edit?gid=1861712941#gid=1861712941",
    "Add Stall Minutes": "https://docs.google.com/spreadsheets/d/1xEUK1U6FtCGE80gOk0JCRC1eLJF9ALgz4T4KuK-9vYc/edit?gid=1279191862#gid=1279191862",
}
UI_SETTINGS_PATH = PROJECT_ROOT / "config" / "ui_settings.json"
SETUP_CODES_PATH = PROJECT_ROOT / "config" / "setup_codes.json"
SETUP_TOURS = {"usual": "random", "watched": "watched"}


def load_setup_codes():
    try:
        with SETUP_CODES_PATH.open(encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


SETUP_CODES = load_setup_codes()

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

PLAYER_PATTERN = re.compile(r"^(.*?)\s*(?:\(([^()]*)\))?\s*$")


class MissingRatingsError(ValueError):
    def __init__(self, names):
        self.names = names
        super().__init__("Missing rating for: " + ", ".join(names))


def guess_gr(thresholds, avg_gr):
    if avg_gr:
        for threshold, result in thresholds:
            if avg_gr >= threshold:
                return result
    return "x"


def player_average_gr(name, player_stats, idtable):
    import pandas as pd

    try:
        alias_df = pd.read_csv(idtable)
        alias_df["Player Name"] = alias_df["Player Name"].str.strip().str.lower()
        player_id = alias_df.loc[alias_df["Player Name"] == name, "Player ID"].iloc[0]
        avg_gr = player_stats.loc[player_stats["Player ID"] == player_id, "Guess rate"].mean()
        if pd.isna(avg_gr):
            avg_gr = None
    except IndexError:
        avg_gr = None
    return avg_gr


def get_guess_watched_ui(name, player_stats, idtable, oneg, twog, threeg, fourg):
    avg_gr = player_average_gr(name, player_stats, idtable)
    return guess_gr([(fourg, "5"), (threeg, "4"), (twog, "3"), (oneg, "2"), (-float("inf"), "1")], avg_gr)


def get_guess_random_ui(name, player_stats, idtable, oneg, twog, threeg):
    avg_gr = player_average_gr(name, player_stats, idtable)
    return guess_gr([(threeg, "4"), (twog, "3"), (oneg, "2"), (-float("inf"), "1")], avg_gr)


def get_guess_watched_28_ui(name, player_stats, idtable, zerog, oneg, twog, threeg, fourg):
    avg_gr = player_average_gr(name, player_stats, idtable)
    return guess_gr([(fourg, "5"), (threeg, "4"), (twog, "3"), (oneg, "2"), (zerog, "1"), (-float("inf"), "0")], avg_gr)


GUESS_HANDLERS = {
    "random": get_guess_random_ui,
    "watched": get_guess_watched_ui,
    "watched_28": get_guess_watched_28_ui,
}


class AMQTourUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("AMQ Host Script")
        self.geometry("1180x760")
        self.minsize(980, 640)

        self.selected_tour_id = "usual"
        self.selected_category = "Random"
        self.category_buttons: dict[str, ttk.Button] = {}
        self.tour_buttons: dict[str, ttk.Button] = {}
        self.players_placeholder = "name (Rank), name (Rank), ..."
        self.players_placeholder_active = False
        self.solver_running = False
        self.rank_vars: dict[str, tk.StringVar] = {}
        self.startup_eloscrape_done = threading.Event()
        self.startup_eloscrape_running = False
        self.startup_eloscrape_errors = []
        self.ui_settings = self.load_ui_settings()
        self.dark_mode = tk.BooleanVar(value=bool(self.ui_settings.get("dark_mode", False)))
        self.tk_text_widgets: list[tk.Text] = []
        self.tk_list_widgets: list[tk.Listbox] = []
        self.setup_guess_time = tk.StringVar()
        self.setup_difficulty = tk.StringVar()
        self.setup_quagsual = tk.BooleanVar(value=False)
        self.setup_fey_watched = tk.BooleanVar(value=False)
        self.setup_active_key = None
        self.current_setup_code = ""
        self.challonge_items = []
        self.mvp_running = False
        self.update_elos_running = False
        self.recalculate_running = False
        self.latest_inhouse_teams = {}
        self.inhouse_result_rows = []
        self.inhouse_logging = False
        self.elos_search_var = tk.StringVar()

        self._configure_style()
        self._build_layout()
        self.select_category("Random")
        self.select_tour("usual")
        self.after(300, self.start_startup_eloscrape)

    def _configure_style(self):
        self.colors = self._theme_colors()
        self.configure(bg=self.colors["bg"])
        self.style = ttk.Style(self)
        self.style.theme_use("clam")
        self.style.configure("TFrame", background=self.colors["bg"])
        self.style.configure("Panel.TFrame", background=self.colors["panel"])
        self.style.configure("TLabel", background=self.colors["bg"], foreground=self.colors["text"], font=("Segoe UI", 10))
        self.style.configure("Panel.TLabel", background=self.colors["panel"], foreground=self.colors["text"], font=("Segoe UI", 10))
        self.style.configure("Title.TLabel", background=self.colors["bg"], foreground=self.colors["title"], font=("Segoe UI", 18, "bold"))
        self.style.configure("Subtle.TLabel", background=self.colors["panel"], foreground=self.colors["muted"], font=("Segoe UI", 9))
        self.style.configure("TButton", font=("Segoe UI", 10), padding=(10, 6), background=self.colors["button"], foreground=self.colors["text"], bordercolor=self.colors["border"])
        self.style.configure("Selected.TButton", font=("Segoe UI", 10), padding=(10, 6), background=self.colors["selected"], foreground=self.colors["selected_text"], bordercolor=self.colors["selected"])
        self.style.configure("Tool.TButton", font=("Segoe UI", 10), padding=(12, 7), background=self.colors["button"], foreground=self.colors["text"], bordercolor=self.colors["border"])
        self.style.configure(
            "TCheckbutton",
            background=self.colors["bg"],
            foreground=self.colors["text"],
            fieldbackground=self.colors["field"],
            indicatorbackground=self.colors["field"],
            indicatorforeground=self.colors["text"],
            indicatorcolor=self.colors["field"],
            focuscolor=self.colors["bg"],
            font=("Segoe UI", 10),
        )
        self.style.configure("TEntry", fieldbackground=self.colors["field"], foreground=self.colors["text"], bordercolor=self.colors["border"])
        self.style.configure("TCombobox", fieldbackground=self.colors["field"], foreground=self.colors["text"], background=self.colors["button"], bordercolor=self.colors["border"], arrowcolor=self.colors["text"])
        self.style.configure("TSpinbox", fieldbackground=self.colors["field"], foreground=self.colors["text"], bordercolor=self.colors["border"])
        self.style.configure("TNotebook", background=self.colors["bg"], borderwidth=0, tabmargins=(0, 0, 0, 0))
        self.style.configure("TNotebook.Tab", padding=(14, 8), width=18, font=("Segoe UI", 10), background=self.colors["button"], foreground=self.colors["text"], borderwidth=1)
        self.style.configure("Horizontal.TProgressbar", troughcolor=self.colors["progress_track"], background=self.colors["accent"], bordercolor=self.colors["border"], lightcolor=self.colors["accent"], darkcolor=self.colors["accent"])
        self.style.configure("Treeview", background=self.colors["field"], fieldbackground=self.colors["field"], foreground=self.colors["text"], bordercolor=self.colors["border"])
        self.style.configure("Treeview.Heading", background=self.colors["button"], foreground=self.colors["text"], font=("Segoe UI", 10, "bold"))
        self.style.map("TButton", background=[("active", self.colors["button_active"])])
        self.style.map("Selected.TButton", background=[("active", self.colors["selected"])])
        self.style.map(
            "TCheckbutton",
            background=[
                ("active", self.colors["bg"]),
                ("pressed", self.colors["bg"]),
                ("selected", self.colors["bg"]),
                ("!selected", self.colors["bg"]),
            ],
            foreground=[
                ("active", self.colors["text"]),
                ("pressed", self.colors["text"]),
                ("selected", self.colors["text"]),
                ("!selected", self.colors["text"]),
            ],
            indicatorbackground=[
                ("active", self.colors["field"]),
                ("pressed", self.colors["field"]),
                ("selected", self.colors["accent"]),
                ("!selected", self.colors["field"]),
            ],
            indicatorcolor=[
                ("active", self.colors["field"]),
                ("pressed", self.colors["field"]),
                ("selected", self.colors["accent"]),
                ("!selected", self.colors["field"]),
            ],
        )
        self.style.map(
            "TCombobox",
            fieldbackground=[("readonly", self.colors["field"])],
            foreground=[("readonly", self.colors["text"])],
            background=[("readonly", self.colors["button"]), ("active", self.colors["button_active"])],
            selectbackground=[("readonly", self.colors["field"])],
            selectforeground=[("readonly", self.colors["text"])],
        )
        self.style.map(
            "TNotebook.Tab",
            background=[("selected", self.colors["panel"]), ("active", self.colors["button_active"])],
            padding=[("selected", (14, 8)), ("!selected", (14, 8))],
            expand=[("selected", [0, 0, 0, 0]), ("!selected", [0, 0, 0, 0])],
        )
        self.style.map("Treeview", background=[("selected", self.colors["accent"])], foreground=[("selected", self.colors["selected_text"])])
        self.option_add("*TCombobox*Listbox.background", self.colors["field"])
        self.option_add("*TCombobox*Listbox.foreground", self.colors["text"])
        self.option_add("*TCombobox*Listbox.selectBackground", self.colors["accent"])
        self.option_add("*TCombobox*Listbox.selectForeground", self.colors["selected_text"])

    def _theme_colors(self):
        if self.dark_mode.get():
            return {
                "bg": "#0f172a",
                "panel": "#182235",
                "field": "#111827",
                "text": "#e5e7eb",
                "title": "#f8fafc",
                "muted": "#94a3b8",
                "placeholder": "#64748b",
                "border": "#334155",
                "button": "#223047",
                "button_active": "#2d3d59",
                "selected": "#38bdf8",
                "selected_text": "#082f49",
                "accent": "#38bdf8",
                "progress_track": "#273449",
            }
        return {
            "bg": "#f4f6f8",
            "panel": "#ffffff",
            "field": "#ffffff",
            "text": "#1f2933",
            "title": "#111827",
            "muted": "#64748b",
            "placeholder": "#94a3b8",
            "border": "#cbd5e1",
            "button": "#f8fafc",
            "button_active": "#e2e8f0",
            "selected": "#2563eb",
            "selected_text": "#ffffff",
            "accent": "#2563eb",
            "progress_track": "#dbe4ee",
        }

    def toggle_theme(self):
        self.save_ui_settings()
        self._configure_style()
        self.apply_widget_theme()

    def load_ui_settings(self):
        try:
            with UI_SETTINGS_PATH.open(encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            return {}

    def save_ui_settings(self):
        self.ui_settings["dark_mode"] = self.dark_mode.get()
        UI_SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
        with UI_SETTINGS_PATH.open("w", encoding="utf-8") as f:
            json.dump(self.ui_settings, f, indent=2)

    def apply_widget_theme(self):
        for widget in getattr(self, "tk_text_widgets", []):
            widget.configure(
                background=self.colors["field"],
                foreground=self.colors["text"],
                insertbackground=self.colors["text"],
                highlightbackground=self.colors["border"],
                highlightcolor=self.colors["accent"],
            )
            widget.tag_configure("placeholder", foreground=self.colors["placeholder"])
        for widget in getattr(self, "tk_list_widgets", []):
            widget.configure(
                background=self.colors["field"],
                foreground=self.colors["text"],
                selectbackground=self.colors["accent"],
                selectforeground=self.colors["selected_text"],
                highlightbackground=self.colors["border"],
                highlightcolor=self.colors["accent"],
            )

    def _build_layout(self):
        root = ttk.Frame(self, padding=16)
        root.pack(fill="both", expand=True)
        root.columnconfigure(1, weight=1)
        root.rowconfigure(1, weight=1)

        header = ttk.Frame(root)
        header.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 12))
        header.columnconfigure(0, weight=1)
        ttk.Label(header, text="AMQ Host Script", style="Title.TLabel").grid(row=0, column=0, sticky="w")
        for index, (label, url) in enumerate(LINKS.items(), start=1):
            ttk.Button(header, text=label, command=lambda u=url: webbrowser.open(u)).grid(row=0, column=index, sticky="e", padx=(8, 0))
        ttk.Checkbutton(header, text="Dark Mode", variable=self.dark_mode, command=self.toggle_theme).grid(row=0, column=len(LINKS) + 1, sticky="e", padx=(14, 0))
        self.elo_status_var = tk.StringVar(value="Eloscrape: waiting to start")
        ttk.Label(header, textvariable=self.elo_status_var).grid(row=1, column=0, columnspan=5, sticky="w", pady=(4, 0))
        progress_row = ttk.Frame(header)
        progress_row.grid(row=2, column=0, columnspan=5, sticky="ew", pady=(6, 0))
        progress_row.columnconfigure(0, weight=1)
        self.elo_progress_var = tk.DoubleVar(value=0)
        self.elo_progress_text_var = tk.StringVar(value="0%")
        self.elo_progress = ttk.Progressbar(progress_row, mode="determinate", maximum=100, variable=self.elo_progress_var)
        self.elo_progress.grid(row=0, column=0, sticky="ew")
        ttk.Label(progress_row, textvariable=self.elo_progress_text_var).grid(row=0, column=1, sticky="e", padx=(10, 0))

        sidebar = ttk.Frame(root, style="Panel.TFrame", padding=12)
        sidebar.grid(row=1, column=0, sticky="nsw", padx=(0, 14))
        sidebar.configure(width=190)
        sidebar.grid_propagate(False)
        sidebar.columnconfigure(0, weight=1)
        sidebar.rowconfigure(8, weight=1)
        ttk.Label(sidebar, text="Categories", style="Panel.TLabel", font=("Segoe UI", 11, "bold")).grid(row=0, column=0, sticky="w", pady=(0, 8))

        for index, category in enumerate(["Random", "Watched", "Speed", "Inhouse"], start=1):
            button = ttk.Button(sidebar, text=category, width=18, command=lambda c=category: self.select_category(c))
            button.grid(row=index, column=0, sticky="ew", pady=3)
            self.category_buttons[category] = button

        ttk.Separator(sidebar).grid(row=5, column=0, sticky="ew", pady=12)
        ttk.Label(sidebar, text="Tour Types", style="Panel.TLabel", font=("Segoe UI", 11, "bold")).grid(row=6, column=0, sticky="w", pady=(0, 8))

        self.tour_list = ttk.Frame(sidebar, style="Panel.TFrame")
        self.tour_list.grid(row=7, column=0, sticky="new")
        self.tour_list.columnconfigure(0, weight=1, minsize=166)

        self.recalculate_button = ttk.Button(sidebar, text="Recalculate All", width=18, command=self.confirm_recalculate_all)
        self.recalculate_button.grid(row=9, column=0, sticky="sew", pady=(12, 0))

        content = ttk.Frame(root)
        content.grid(row=1, column=1, sticky="nsew")
        content.columnconfigure(0, weight=1)
        content.rowconfigure(1, weight=1)

        self.tour_title = ttk.Label(content, text="", style="Title.TLabel")
        self.tour_title.grid(row=0, column=0, sticky="w", pady=(0, 12))

        self.main_notebook = ttk.Notebook(content)
        self.main_notebook.grid(row=1, column=0, sticky="nsew")

        self.setup_tab = ttk.Frame(self.main_notebook, padding=14)
        self.solver_tab = ttk.Frame(self.main_notebook, padding=14)
        self.update_tab = ttk.Frame(self.main_notebook, padding=14)
        self.elos_tab = ttk.Frame(self.main_notebook, padding=14)

        self._build_setup_tab()
        self._build_solver_tab()
        self._build_update_tab()
        self._build_elos_tab()

    def _build_setup_tab(self):
        self.setup_tab.columnconfigure(1, weight=1)
        self.setup_tab.rowconfigure(3, weight=1)

        ttk.Label(self.setup_tab, text="Guess Time").grid(row=0, column=0, sticky="w", pady=(0, 8))
        self.setup_guess_combo = ttk.Combobox(self.setup_tab, textvariable=self.setup_guess_time, state="readonly", width=12)
        self.setup_guess_combo.grid(row=0, column=1, sticky="w", pady=(0, 8))
        self.setup_guess_combo.bind("<<ComboboxSelected>>", self.on_setup_changed)

        ttk.Label(self.setup_tab, text="Difficulty").grid(row=1, column=0, sticky="w", pady=(0, 8))
        self.setup_difficulty_combo = ttk.Combobox(self.setup_tab, textvariable=self.setup_difficulty, state="readonly", width=12)
        self.setup_difficulty_combo.grid(row=1, column=1, sticky="w", pady=(0, 8))
        self.setup_difficulty_combo.bind("<<ComboboxSelected>>", self.on_setup_changed)

        self.setup_quagsual_check = ttk.Checkbutton(self.setup_tab, text="Quagsual", variable=self.setup_quagsual, command=self.on_setup_changed)
        self.setup_quagsual_check.grid(row=2, column=0, columnspan=2, sticky="w", pady=(0, 10))
        self.setup_fey_watched_check = ttk.Checkbutton(self.setup_tab, text="Fey Watched", variable=self.setup_fey_watched, command=self.on_setup_changed)
        self.setup_fey_watched_check.grid(row=2, column=0, columnspan=2, sticky="w", pady=(0, 10))

        self.setup_note = ttk.Label(self.setup_tab, text="", style="Subtle.TLabel")
        self.setup_note.grid(row=3, column=0, columnspan=2, sticky="nw", pady=(2, 0))

    def _build_solver_tab(self):
        self.solver_tab.columnconfigure(1, weight=1)
        self.solver_tab.rowconfigure(2, weight=1)
        self.solver_tab.rowconfigure(6, weight=1)

        controls = ttk.Frame(self.solver_tab)
        controls.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 12))
        controls.columnconfigure(3, weight=1)

        ttk.Label(controls, text="Team Size").grid(row=0, column=0, sticky="w")
        self.team_size = tk.StringVar(value="4")
        ttk.Spinbox(controls, from_=1, to=12, width=6, textvariable=self.team_size).grid(row=0, column=1, padx=(8, 24), sticky="w")

        self.separate_t1 = tk.BooleanVar(value=False)
        ttk.Checkbutton(controls, text="Separate T1s", variable=self.separate_t1).grid(row=0, column=2, padx=(0, 24), sticky="w")

        self.split_tour = tk.BooleanVar(value=False)
        ttk.Checkbutton(controls, text="Split Tour", variable=self.split_tour).grid(row=0, column=3, sticky="w")

        ttk.Label(self.solver_tab, text="Players", font=("Segoe UI", 11, "bold")).grid(row=1, column=0, sticky="w")
        ttk.Label(self.solver_tab, text="Whitelist", font=("Segoe UI", 11, "bold")).grid(row=1, column=1, sticky="w", padx=(14, 0))

        self.players_text = tk.Text(self.solver_tab, height=12, wrap="word", borderwidth=1, relief="solid", font=("Segoe UI", 10))
        self.players_text.grid(row=2, column=0, sticky="nsew", pady=(6, 12), padx=(0, 14))
        self.players_text.tag_configure("placeholder", foreground="#94a3b8")
        self.tk_text_widgets.append(self.players_text)
        self.show_players_placeholder()
        self.players_text.bind("<FocusIn>", self.on_players_focus_in)
        self.players_text.bind("<FocusOut>", self.on_players_focus_out)
        self.players_text.bind("<<Modified>>", self.on_players_modified)

        whitelist_panel = ttk.Frame(self.solver_tab)
        whitelist_panel.grid(row=2, column=1, sticky="nsew", pady=(6, 12))
        whitelist_panel.columnconfigure(0, weight=1)
        whitelist_panel.columnconfigure(1, weight=1)
        whitelist_panel.rowconfigure(2, weight=1)
        self.whitelist_a = ttk.Combobox(whitelist_panel, values=[])
        self.whitelist_b = ttk.Combobox(whitelist_panel, values=[])
        self.whitelist_a.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        self.whitelist_b.grid(row=0, column=1, sticky="ew", padx=(6, 0))
        ttk.Button(whitelist_panel, text="Add Pair", command=self.add_whitelist_pair).grid(row=1, column=0, columnspan=2, sticky="ew", pady=8)
        list_frame = ttk.Frame(whitelist_panel)
        list_frame.grid(row=2, column=0, columnspan=2, sticky="nsew")
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)
        self.whitelist_list = tk.Listbox(list_frame, height=6, activestyle="none")
        self.whitelist_list.grid(row=0, column=0, sticky="nsew")
        self.tk_list_widgets.append(self.whitelist_list)
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.whitelist_list.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.whitelist_list.configure(yscrollcommand=scrollbar.set)
        self.remove_pair_button = ttk.Button(whitelist_panel, text="Remove Selected Pair", command=self.remove_whitelist_pair)
        self.remove_pair_button.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(8, 0))

        actions = ttk.Frame(self.solver_tab)
        actions.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(0, 12))
        self.solver_button = ttk.Button(actions, text="Make Teams", style="Tool.TButton", command=self.run_solver)
        self.solver_button.pack(side="left")
        ttk.Button(actions, text="Copy Codes", command=lambda: self.clipboard_from_text(self.codes_text)).pack(side="left")

        self.rank_assignment_frame = ttk.Frame(self.solver_tab)
        self.rank_assignment_frame.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(0, 12))
        self.rank_assignment_frame.columnconfigure(0, weight=1)
        self.rank_assignment_header = ttk.Label(self.rank_assignment_frame, text="", font=("Segoe UI", 11, "bold"))
        self.rank_assignment_header.grid(row=0, column=0, sticky="w", pady=(0, 6))
        self.rank_fields = ttk.Frame(self.rank_assignment_frame)
        self.rank_fields.grid(row=1, column=0, sticky="ew")
        self.rank_assignment_note = ttk.Label(self.rank_assignment_frame, text="Enter numeric ratings for these players, then press Make Teams again.", style="Subtle.TLabel")
        self.rank_assignment_note.grid(row=2, column=0, sticky="w", pady=(6, 0))
        self.rank_assignment_frame.grid_remove()

        ttk.Label(self.solver_tab, text="Codes", font=("Segoe UI", 11, "bold")).grid(row=5, column=0, columnspan=2, sticky="w")
        self.codes_text = tk.Text(self.solver_tab, height=10, wrap="word", borderwidth=1, relief="solid", font=("Consolas", 10))
        self.codes_text.grid(row=6, column=0, columnspan=2, sticky="nsew", pady=(6, 0))
        self.tk_text_widgets.append(self.codes_text)
        self.apply_widget_theme()

    def _build_update_tab(self):
        self.update_tab.columnconfigure(0, weight=1)
        self.update_tab.columnconfigure(1, weight=1)
        self.update_tab.rowconfigure(4, weight=1)

        self.update_elos_button = ttk.Button(self.update_tab, text="Update Elos", style="Tool.TButton", command=self.run_update_elos)
        self.update_elos_button.grid(row=2, column=0, sticky="w")

        self.challonge_label = ttk.Label(self.update_tab, text="Challonge Link")
        self.challonge_label.grid(row=1, column=0, sticky="w", pady=(18, 4))
        self.challonge_input_row = ttk.Frame(self.update_tab)
        self.challonge_input_row.grid(row=2, column=0, sticky="ew", padx=(0, 12))
        self.challonge_input_row.columnconfigure(0, weight=1)
        self.challonge_link = ttk.Entry(self.challonge_input_row)
        self.challonge_link.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.challonge_run_button = ttk.Button(self.challonge_input_row, text="Run Eloscrape", command=self.run_manual_eloscrape)
        self.challonge_run_button.grid(row=0, column=1, sticky="e")

        self.selected_challonge_var = tk.StringVar(value="Select a Challonge")
        self.selected_challonge_label = ttk.Label(self.update_tab, textvariable=self.selected_challonge_var, font=("Segoe UI", 11, "bold"))
        self.selected_challonge_label.grid(row=1, column=1, sticky="w", pady=(18, 4))
        self.changelog_action_row = ttk.Frame(self.update_tab)
        self.changelog_action_row.grid(row=2, column=1, sticky="w")
        self.mvp_run_button = ttk.Button(self.changelog_action_row, text="Run MVPs", command=self.run_mvp_for_selected)
        self.mvp_run_button.pack(side="left")
        self.download_changelog_button = ttk.Button(self.changelog_action_row, text="Download", command=self.download_selected_changelog)
        self.download_changelog_button.pack(side="left", padx=(8, 0))
        self.download_mvps_button = ttk.Button(self.changelog_action_row, text="Save MVPs + Changelog", command=self.download_dry_outputs)
        self.download_mvps_button.pack(side="left", padx=(8, 0))

        self.history_heading_label = ttk.Label(self.update_tab, text="Challonges", font=("Segoe UI", 11, "bold"))
        self.history_heading_label.grid(row=3, column=0, sticky="w", pady=(18, 6))
        self.mvp_heading_label = ttk.Label(self.update_tab, text="MVPs", font=("Segoe UI", 11, "bold"))
        self.mvp_heading_label.grid(row=3, column=1, sticky="w", pady=(18, 6))

        self.results_frame = ttk.Frame(self.update_tab)
        self.results_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(8, 10))
        self.results_frame.columnconfigure(4, weight=1)
        ttk.Label(self.results_frame, text="Rounds").grid(row=0, column=0, sticky="w")
        self.inhouse_round_count = tk.StringVar(value="")
        ttk.Spinbox(self.results_frame, from_=1, to=50, width=6, textvariable=self.inhouse_round_count).grid(row=0, column=1, sticky="w", padx=(8, 14))
        ttk.Button(self.results_frame, text="Build Result Rows", command=self.build_inhouse_result_rows).grid(row=0, column=2, sticky="w", padx=(0, 8))
        self.inhouse_log_button = ttk.Button(self.results_frame, text="Log Results", style="Tool.TButton", command=self.run_log_inhouse_results)
        self.inhouse_log_button.grid(row=0, column=3, sticky="w")
        self.inhouse_team_summary = ttk.Label(self.results_frame, text="", style="Subtle.TLabel")
        self.inhouse_team_summary.grid(row=1, column=0, columnspan=5, sticky="w", pady=(8, 4))
        self.inhouse_rows_frame = ttk.Frame(self.results_frame)
        self.inhouse_rows_frame.grid(row=2, column=0, columnspan=5, sticky="ew")
        self.results_frame.grid_remove()

        self.left_panel = ttk.Frame(self.update_tab)
        self.left_panel.grid(row=4, column=0, sticky="nsew", padx=(0, 12))
        self.left_panel.columnconfigure(0, weight=1)
        self.left_panel.rowconfigure(0, weight=1)
        self.challonge_list = tk.Listbox(self.left_panel, height=12, activestyle="none")
        self.challonge_list.grid(row=0, column=0, sticky="nsew")
        self.challonge_list.bind("<<ListboxSelect>>", self.on_challonge_selected)
        self.tk_list_widgets.append(self.challonge_list)
        challonge_scrollbar = ttk.Scrollbar(self.left_panel, orient="vertical", command=self.challonge_list.yview)
        challonge_scrollbar.grid(row=0, column=1, sticky="ns")
        self.challonge_list.configure(yscrollcommand=challonge_scrollbar.set)

        self.update_info = tk.Text(self.update_tab, height=12, wrap="word", borderwidth=1, relief="solid", font=("Segoe UI", 10))
        self.update_info.grid(row=4, column=1, sticky="nsew")
        self.tk_text_widgets.append(self.update_info)
        self.apply_widget_theme()

    def _build_elos_tab(self):
        self.elos_tab.columnconfigure(0, weight=1)
        self.elos_tab.rowconfigure(1, weight=1)
        elos_controls = ttk.Frame(self.elos_tab)
        elos_controls.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        elos_controls.columnconfigure(2, weight=1)
        ttk.Button(elos_controls, text="Refresh Elos", command=self.refresh_elos).grid(row=0, column=0, sticky="w")
        ttk.Label(elos_controls, text="Search").grid(row=0, column=1, sticky="w", padx=(14, 6))
        self.elos_search_entry = ttk.Entry(elos_controls, textvariable=self.elos_search_var, width=28)
        self.elos_search_entry.grid(row=0, column=2, sticky="w")
        self.elos_search_entry.bind("<KeyRelease>", lambda _event: self.refresh_elos())
        self.elos_table = ttk.Treeview(self.elos_tab, columns=("player", "elo"), show="headings", height=20)
        self.elos_table.heading("player", text="Player")
        self.elos_table.heading("elo", text="Elo")
        self.elos_table.column("player", width=320, anchor="w")
        self.elos_table.column("elo", width=120, anchor="e")
        self.elos_table.grid(row=1, column=0, sticky="nsew")

    def select_category(self, category: str):
        self.selected_category = category
        for name, button in self.category_buttons.items():
            button.configure(style="Selected.TButton" if name == category else "TButton")

        for child in self.tour_list.winfo_children():
            child.destroy()
        self.tour_buttons.clear()

        for row, (label, tour_id) in enumerate(CATEGORIES[category]):
            if tour_id and tour_id in TOURS:
                button = ttk.Button(self.tour_list, text=label, width=18, command=lambda tid=tour_id: self.select_tour(tid))
                button.grid(row=row, column=0, sticky="ew", pady=3)
                self.tour_buttons[tour_id] = button
            else:
                button = ttk.Button(self.tour_list, text=f"{label}  (soon)", width=18, state="disabled")
                button.grid(row=row, column=0, sticky="ew", pady=3)

        first_tour = next((tour_id for _, tour_id in CATEGORIES[category] if tour_id in TOURS), None)
        if first_tour:
            self.select_tour(first_tour)

    def select_tour(self, tour_id: str):
        self.selected_tour_id = tour_id
        tour = TOURS[tour_id]
        self.tour_title.configure(text=tour["label"])
        for key, button in self.tour_buttons.items():
            button.configure(style="Selected.TButton" if key == tour_id else "TButton")

        self._show_tour_tabs()
        self._set_update_tab_title(tour)
        self.refresh_setup_tab()
        self.update_challonge_input_visibility(tour)
        self.update_elos_button_visibility()
        self.refresh_elos()
        self.refresh_update_info()
        self.set_status(f"Selected {tour['label']}.")

    def _show_tour_tabs(self):
        tabs = self.main_notebook.tabs()
        for tab in tabs:
            self.main_notebook.forget(tab)
        if self.current_setup_key():
            self.main_notebook.add(self.setup_tab, text="Setup")
        self.main_notebook.add(self.solver_tab, text="Make Teams")
        self.main_notebook.add(self.update_tab, text="Eloscrape")
        self.main_notebook.add(self.elos_tab, text="Elos")

    def _set_update_tab_title(self, tour):
        update_title = "Results" if tour.get("supports_inhouse") else ("MVPs / Changelog" if tour.get("dry_elo") else "Eloscrape")
        if str(self.update_tab) in self.main_notebook.tabs():
            self.main_notebook.tab(str(self.update_tab), text=update_title)

    def refresh_setup_tab(self):
        setup_key = self.current_setup_key()
        self.setup_active_key = setup_key
        if not setup_key:
            self.current_setup_code = ""
            self.setup_note.configure(text="")
            return

        config = SETUP_CODES.get(setup_key, {})
        self.setup_guess_combo.configure(values=config.get("guess_times", []))
        self.setup_difficulty_combo.configure(values=config.get("difficulties", []))

        self.setup_guess_time.set(config.get("default_guess_time", ""))
        self.setup_difficulty.set(config.get("default_difficulty", ""))
        self.setup_quagsual.set(False)
        self.setup_fey_watched.set(False)

        if setup_key == "random":
            self.setup_quagsual_check.grid()
        else:
            self.setup_quagsual_check.grid_remove()
        if setup_key == "watched":
            self.setup_fey_watched_check.grid()
        else:
            self.setup_fey_watched_check.grid_remove()
        self.refresh_setup_code()

    def on_setup_changed(self, _event=None):
        self.refresh_setup_code()

    def refresh_setup_code(self):
        setup_key = self.setup_active_key
        self.current_setup_code = self.selected_setup_code()
        self.update_setup_control_states()
        config = SETUP_CODES.get(setup_key or "", {})
        difficulty = self.setup_difficulty.get()
        elo_difficulties = set(config.get("elo_difficulties", []))
        if setup_key == "random" and self.setup_quagsual.get():
            self.setup_note.configure(text="Counts for elo.")
        elif setup_key == "watched" and self.setup_fey_watched.get():
            self.setup_note.configure(text="Counts for elo.")
        elif difficulty in elo_difficulties:
            self.setup_note.configure(text="Counts for elo.")
        elif setup_key in {"random", "watched"}:
            self.setup_note.configure(text="Does not count for elo.")
        else:
            self.setup_note.configure(text="")

    def current_setup_key(self):
        return SETUP_TOURS.get(self.selected_tour_id)

    def selected_setup_code(self):
        setup_key = self.setup_active_key
        config = SETUP_CODES.get(setup_key or "", {})
        if setup_key == "random" and self.setup_quagsual.get():
            return config.get("quagsual", "")
        if setup_key == "watched" and self.setup_fey_watched.get():
            return config.get("fey_watched", "")
        return config.get("codes", {}).get(self.setup_guess_time.get(), {}).get(self.setup_difficulty.get(), "")

    def update_setup_control_states(self):
        if (
            (self.setup_active_key == "random" and self.setup_quagsual.get())
            or (self.setup_active_key == "watched" and self.setup_fey_watched.get())
        ):
            self.setup_guess_combo.configure(state="disabled")
            self.setup_difficulty_combo.configure(state="disabled")
            return
        self.setup_guess_combo.configure(state="readonly")
        self.setup_difficulty_combo.configure(state="readonly")

    def update_challonge_input_visibility(self, tour):
        widgets = (self.challonge_label, self.challonge_input_row)
        if tour.get("supports_inhouse"):
            for widget in widgets:
                widget.grid_remove()
            self.update_elos_button.grid_remove()
            self.selected_challonge_label.grid_remove()
            self.changelog_action_row.grid_remove()
            self.mvp_heading_label.configure(text="Log")
            self.results_frame.grid()
            self.refresh_inhouse_results_ui(tour)
            return

        self.selected_challonge_label.grid()
        self.changelog_action_row.grid()
        self.results_frame.grid_remove()
        self.download_changelog_button.pack_forget()
        self.download_mvps_button.pack_forget()
        if tour.get("dry_elo"):
            self.mvp_run_button.configure(text="Run MVPs", command=self.run_mvp_for_selected)
            self.download_mvps_button.pack(side="left", padx=(8, 0))
            self.mvp_heading_label.configure(text="MVPs")
            for widget in widgets:
                widget.grid_remove()
            self.update_elos_button.grid()
            return
        self.mvp_run_button.configure(text="View Changelog", command=self.run_view_changelog)
        self.download_changelog_button.pack(side="left", padx=(8, 0))
        self.mvp_heading_label.configure(text="Changelog")
        self.update_elos_button.grid_remove()
        self.challonge_label.grid()
        self.challonge_input_row.grid()

    def update_elos_button_visibility(self):
        tour = TOURS[self.selected_tour_id]
        if not tour.get("dry_elo"):
            self.update_elos_button.grid_remove()
            return
        self.update_elos_button.grid()

    def show_players_placeholder(self):
        self.players_placeholder_active = True
        self.players_text.delete("1.0", "end")
        self.players_text.insert("1.0", self.players_placeholder, "placeholder")
        self.players_text.edit_modified(False)

    def on_players_focus_in(self, _event=None):
        if self.players_placeholder_active:
            self.players_placeholder_active = False
            self.players_text.delete("1.0", "end")
            self.players_text.edit_modified(False)

    def on_players_focus_out(self, _event=None):
        if not self.players_text.get("1.0", "end").strip():
            self.show_players_placeholder()

    def on_players_modified(self, _event=None):
        if not self.players_text.edit_modified():
            return
        self.players_text.edit_modified(False)
        if self.players_placeholder_active:
            return
        self.after_idle(lambda: self.refresh_player_selects(show_status=False))

    def refresh_player_selects(self, show_status=True):
        players = [name for name, _rank in self.parse_player_entries(allow_placeholder=True)]
        self.whitelist_a.configure(values=players)
        self.whitelist_b.configure(values=players)
        if show_status:
            self.set_status(f"Loaded {len(players)} players into whitelist selectors.")

    def parse_player_entries(self, allow_placeholder=False):
        if self.players_placeholder_active:
            return [] if allow_placeholder else self.fail("Add players first.")

        raw = self.players_text.get("1.0", "end").replace("\n", ",")
        players = []
        for item in raw.split(","):
            item = item.strip()
            if not item:
                continue
            match = PLAYER_PATTERN.match(item)
            if not match:
                raise ValueError(f"Could not read player entry: {item}")
            name = match.group(1).strip().lower()
            rank = self.parse_pasted_rank(match.group(2))
            if name and name not in [player_name for player_name, _ in players]:
                players.append((name, rank))
        return players

    def parse_pasted_rank(self, rank_text):
        if rank_text is None:
            return None
        rank_text = rank_text.strip()
        try:
            return float(rank_text)
        except ValueError:
            return None

    def fail(self, message):
        raise ValueError(message)

    def add_whitelist_pair(self):
        player_a = self.whitelist_a.get().strip()
        player_b = self.whitelist_b.get().strip()
        if not player_a or not player_b:
            self.set_status("Pick two players first.")
            return
        self.whitelist_list.insert("end", f"{player_a} + {player_b}")

    def remove_whitelist_pair(self):
        selected = list(self.whitelist_list.curselection())
        for index in reversed(selected):
            self.whitelist_list.delete(index)

    def whitelist_pairs(self):
        pairs = []
        for index in range(self.whitelist_list.size()):
            value = self.whitelist_list.get(index)
            if " + " in value:
                player_a, player_b = value.split(" + ", 1)
                pairs.append([player_a.strip().lower(), player_b.strip().lower()])
        return pairs

    def manual_ratings(self):
        ratings = {}
        for name, var in self.rank_vars.items():
            value = var.get().strip()
            if not value:
                continue
            try:
                ratings[name] = float(value)
            except ValueError as exc:
                raise ValueError(f"Rating for {name} must be numeric.") from exc
        return ratings

    def show_rank_assignment(self, missing):
        for child in self.rank_fields.winfo_children():
            child.destroy()

        self.rank_assignment_header.configure(text="Assign Missing Ratings")
        current_values = {name: var.get() for name, var in self.rank_vars.items()}
        self.rank_vars = {}

        for index, name in enumerate(missing):
            row = index // 3
            col = (index % 3) * 2
            ttk.Label(self.rank_fields, text=name).grid(row=row, column=col, sticky="w", padx=(0, 6), pady=3)
            var = tk.StringVar(value=current_values.get(name, ""))
            ttk.Entry(self.rank_fields, textvariable=var, width=10).grid(row=row, column=col + 1, sticky="w", padx=(0, 18), pady=3)
            self.rank_vars[name] = var

        self.rank_assignment_frame.grid()

    def hide_rank_assignment(self):
        self.rank_assignment_frame.grid_remove()

    def run_solver(self):
        if self.solver_running:
            return
        try:
            snapshot = self.solver_snapshot()
        except Exception as exc:
            self.finish_solver(error=f"{type(exc).__name__}: {exc}")
            return
        self.solver_running = True
        self.solver_button.configure(state="disabled")
        self.codes_text.delete("1.0", "end")
        self.codes_text.insert("1.0", "Solving...\n")
        self.set_status("Solving...")
        threading.Thread(target=self.solve_in_background, args=(snapshot,), daemon=True).start()

    def solver_snapshot(self):
        return {
            "tour_id": self.selected_tour_id,
            "team_size": int(self.team_size.get()),
            "separate_t1": self.separate_t1.get(),
            "split_tour": self.split_tour.get(),
            "player_entries": self.parse_player_entries(),
            "whitelist_pairs": self.whitelist_pairs(),
            "manual_ratings": self.manual_ratings(),
            "setup_code": self.current_setup_code,
        }

    def solve_in_background(self, snapshot):
        try:
            self.wait_for_startup_eloscrape()
            final_code = self.solve_selected_tour(snapshot)
        except MissingRatingsError as exc:
            missing_names = exc.names
            self.after(0, lambda names=missing_names: self.finish_solver(missing=names))
            return
        except Exception as exc:
            details = traceback.format_exc()
            self.after(0, lambda: self.finish_solver(error=f"{type(exc).__name__}: {exc}\n\n{details}"))
            return
        self.after(0, lambda: self.finish_solver(final_code=final_code))

    def wait_for_startup_eloscrape(self):
        if not self.startup_eloscrape_done.is_set():
            self.after(0, lambda: self.set_status("Waiting for startup eloscrape..."))
            self.after(0, lambda: self.codes_text.insert("end", "Waiting for startup eloscrape to finish...\n"))
            self.startup_eloscrape_done.wait()

    def finish_solver(self, final_code=None, error=None, missing=None):
        self.solver_running = False
        self.solver_button.configure(state="normal")
        self.codes_text.delete("1.0", "end")
        if missing:
            self.show_rank_assignment(missing)
            self.codes_text.insert("1.0", "Some players need ratings before teams can be made.\n")
            self.set_status("Assign missing ratings.")
        elif error:
            self.codes_text.insert("1.0", error)
            self.set_status("Solver failed.")
        else:
            self.hide_rank_assignment()
            self.codes_text.insert("1.0", final_code)
            tour = TOURS[self.selected_tour_id]
            if tour.get("supports_inhouse"):
                self.refresh_inhouse_results_ui(tour)
            self.set_status("Solver finished.")

    def solve_selected_tour(self, snapshot):
        tour = TOURS[snapshot["tour_id"]]
        solver_cfg = tour["solver"]
        team_size = snapshot["team_size"]
        if team_size <= 0:
            raise ValueError("Team size must be at least 1.")

        if tour.get("dry_elo"):
            from modules.support.mvpGenerator import update_dry_elos_for_tour

            update_dry_elos_for_tour(tour)

        players = self.resolve_player_ratings(tour, snapshot["player_entries"], snapshot["manual_ratings"])
        if not players:
            raise ValueError("Add players first.")
        if len(players) % team_size != 0:
            raise ValueError(f"{len(players)} players cannot be divided into teams of {team_size}.")

        if solver_cfg.get("sync_ids"):
            from utils import sync_ids_from_sheet

            sync_ids_from_sheet(tour["state_path"], sheetName=tour["sheet"]["name"], tabIDs=tour["sheet"]["tab_ids"])

        if snapshot["split_tour"] and tour.get("supports_inhouse"):
            raise ValueError("Split Tour is not supported for in-house result logging yet.")

        if snapshot["split_tour"] and len(players) >= 32:
            players = sorted(players, key=lambda item: item[1], reverse=True)
            if (len(players) / 2) % 8 == 0:
                separator = len(players) // 2
            else:
                separator = max(0, len(players) // 2 - 4)
            higher_players = players[:separator]
            lower_players = players[separator:]
            return (
                "# First Tour\n"
                + self.solve_player_group(tour, lower_players, team_size, snapshot)
                + "\n\n# Second Tour\n"
                + self.solve_player_group(tour, higher_players, team_size, snapshot)
            )

        return self.solve_player_group(tour, players, team_size, snapshot)

    def resolve_player_ratings(self, tour, player_entries, manual_ratings):
        from utils import get_elos

        ratings = {name.lower(): float(rating) for name, rating in get_elos(tour["state_path"]).items()}
        alias_ratings = self.build_alias_ratings(ratings)
        players = []
        missing = []
        for name, pasted_rank in player_entries:
            resolved = self.resolve_rating_name(name, ratings, alias_ratings)
            if resolved:
                rating_name, rating = resolved
            elif pasted_rank is not None:
                rating_name = name
                rating = pasted_rank
            elif name in manual_ratings:
                rating_name = name
                rating = manual_ratings[name]
            else:
                missing.append(name)
                continue
            players.append((rating_name, float(rating)))

        if missing:
            raise MissingRatingsError(missing)
        return players

    def build_alias_ratings(self, ratings):
        alias_ratings = {}
        aliases_path = DATA_ROOT / "aliases.txt"
        if aliases_path.exists():
            for line in aliases_path.read_text(encoding="utf-8").splitlines():
                names = [name.strip().lower() for name in line.split("\t") if name.strip()]
                resolved_name = next((name for name in names if name in ratings), None)
                if resolved_name:
                    for alias in names:
                        alias_ratings[alias] = (resolved_name, ratings[resolved_name])

        normalized = {}
        for name, rating in ratings.items():
            key = self.normalize_alias_key(name)
            if key not in normalized:
                normalized[key] = (name, rating)
            else:
                normalized[key] = None

        for key, value in normalized.items():
            if value is not None:
                alias_ratings.setdefault(key, value)

        return alias_ratings

    def resolve_rating_name(self, name, ratings, alias_ratings):
        if name in ratings:
            return name, ratings[name]
        if name in alias_ratings:
            return alias_ratings[name]

        normalized_name = self.normalize_alias_key(name)
        if normalized_name in alias_ratings:
            return alias_ratings[normalized_name]
        return None

    def normalize_alias_key(self, name):
        return re.sub(r"[^a-z0-9]", "", name.lower())

    def solve_player_group(self, tour, players, team_size, snapshot):
        from utils import create_teams, get_blacklist, get_player_stats

        solver_cfg = tour["solver"]
        teams_number = len(players) // team_size
        p_values = {name: rating for name, rating in players}
        teams = create_teams(
            tour["state_path"],
            players,
            team_size,
            snapshot["whitelist_pairs"],
            get_blacklist(),
            snapshot["separate_t1"],
        )
        player_stats, idtable = get_player_stats(
            path=tour["state_path"],
            tabStats=solver_cfg["stats_tab"],
            tabIDs=tour["sheet"]["tab_ids"],
            type=solver_cfg["stats_type"],
        )
        final_code = handleCodes(
            foundSolutions=teams,
            p_values=p_values,
            k=teams_number,
            get_guesses=GUESS_HANDLERS[solver_cfg["guess_mode"]],
            kwargs_guesses=self.guess_kwargs(tour, player_stats, idtable),
            get_codes=CODE_GENERATORS[solver_cfg["code_generator"]],
            gamemode=solver_cfg.get("gamemode"),
            gr_based=True,
        )
        final_code = self.apply_setup_code(final_code, snapshot.get("setup_code", ""))
        codes_path = Path(tour["state_path"]) / "codes.txt"
        codes_path.write_text(final_code, encoding="utf-8")
        if tour.get("supports_inhouse"):
            self.save_latest_inhouse_teams(tour, teams[0], p_values, teams_number)
        return final_code

    def save_latest_inhouse_teams(self, tour, solution, p_values, teams_number):
        team_map = [[] for _ in range(teams_number)]
        for name, team_index in solution.items():
            team_map[team_index].append((name, p_values[name]))

        teams = {}
        for index, members in enumerate(team_map, start=1):
            team_id = f"team{index}"
            sorted_members = sorted(members, key=lambda item: item[1], reverse=True)
            top_player = sorted_members[0][0] if sorted_members else f"Team {index}"
            teams[team_id] = {
                "label": top_player,
                "display_name": " ".join(f"{name} ({rating:.3f})" for name, rating in sorted_members),
                "players": [{"name": name, "rating": round(float(rating), 3)} for name, rating in sorted_members],
            }

        snapshot = {"tour_id": tour["id"], "inhouse_type": tour["inhouse"]["inhouse_type"], "teams": teams}
        self.latest_inhouse_teams[tour["id"]] = snapshot
        path = Path(tour["state_path"]) / "latest_inhouse_teams.json"
        path.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")

    def apply_setup_code(self, final_code, setup_code):
        if not setup_code:
            return final_code
        replacement = f"```{setup_code}```"
        if re.search(r"```.*?```", final_code, flags=re.S):
            return re.sub(r"```.*?```", replacement, final_code, count=1, flags=re.S)
        return f"{replacement}\n\n{final_code}"

    def guess_kwargs(self, tour, player_stats, idtable):
        thresholds = tour["solver"]["thresholds"]
        kwargs = {"player_stats": player_stats, "idtable": idtable}
        if tour["solver"]["guess_mode"] == "watched_28":
            kwargs.update({
                "zerog": thresholds["zero"],
                "oneg": thresholds["one"],
                "twog": thresholds["two"],
                "threeg": thresholds["three"],
                "fourg": thresholds["four"],
            })
        elif tour["solver"]["guess_mode"] == "watched":
            kwargs.update({
                "oneg": thresholds["one"],
                "twog": thresholds["two"],
                "threeg": thresholds["three"],
                "fourg": thresholds["four"],
            })
        else:
            kwargs.update({
                "oneg": thresholds["one"],
                "twog": thresholds["two"],
                "threeg": thresholds["three"],
            })
        return kwargs

    def run_manual_eloscrape(self):
        tour = TOURS[self.selected_tour_id]
        link = self.challonge_link.get().strip()
        if not link:
            self.set_status("Add a Challonge link first.")
            return
        if not tour.get("eloscrape"):
            self.set_status("This tour does not use manual Challonge eloscrape.")
            return
        self.challonge_run_button.configure(state="disabled")
        self.set_status("Running eloscrape...")
        threading.Thread(target=self.manual_eloscrape_in_background, args=(tour, link), daemon=True).start()

    def save_tourlist_link(self, tour, link):
        normalized_link = link.rstrip("/")
        tourlist_path = Path(tour["state_path"]) / "tourlist.txt"
        current_links = []
        if tourlist_path.exists():
            current_links = [line.strip().rstrip("/") for line in tourlist_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        updated_links = [normalized_link] + [current_link for current_link in current_links if current_link.lower() != normalized_link.lower()]
        tourlist_path.write_text("\n".join(updated_links) + "\n", encoding="utf-8")

    def manual_eloscrape_in_background(self, tour, link):
        try:
            if not self.startup_eloscrape_done.is_set():
                self.after(0, lambda: self.set_status("Waiting for startup eloscrape..."))
                self.startup_eloscrape_done.wait()
            self.sync_tour_from_sheet(tour)
            self.save_tourlist_link(tour, link)
            self.clear_eloscrape_local_state(tour)

            def progress_callback(percent, message):
                status = f"Eloscrape: {tour['label']} - {message}" if message else f"Eloscrape: {tour['label']}"
                self.after(0, lambda p=percent, s=status: self.update_eloscrape_progress(p, s))

            self.run_tour_eloscrape(
                tour,
                progress_callback,
                force_refresh_tour_ids=[self.tour_id_from_link(link)],
                force_refresh_tour_urls=[link],
            )
        except Exception as exc:
            details = traceback.format_exc()
            self.after(0, lambda: self.finish_manual_eloscrape(error=f"{type(exc).__name__}: {exc}\n\n{details}"))
            return
        self.after(0, lambda: self.finish_manual_eloscrape(tour=tour, selected_tour_id=self.tour_id_from_link(link)))

    def finish_manual_eloscrape(self, tour=None, selected_tour_id=None, error=None):
        self.challonge_run_button.configure(state="normal")
        if error:
            self.write_update_text(error)
            self.set_status("Eloscrape failed.")
            return
        self.update_eloscrape_progress(100, "Eloscrape finished")
        self.refresh_elos()
        if tour and not tour.get("dry_elo"):
            self.refresh_challonge_list(tour)
            if selected_tour_id:
                self.select_challonge_by_tour_id(selected_tour_id)
            try:
                self.write_update_text(self.selected_changelog_text(tour, selected_tour_id or self.selected_changelog_tour_id()))
                self.set_status("Changelog loaded.")
            except Exception as exc:
                self.write_update_text(f"{type(exc).__name__}: {exc}")
                self.set_status("Changelog failed.")
            return
        self.refresh_update_info()

    def start_startup_eloscrape(self):
        if self.startup_eloscrape_running or self.startup_eloscrape_done.is_set():
            return
        self.startup_eloscrape_running = True
        threading.Thread(target=self.run_startup_eloscrape, daemon=True).start()

    def confirm_recalculate_all(self):
        if self.recalculate_running:
            return
        dialog = tk.Toplevel(self)
        dialog.title("Recalculate All")
        dialog.configure(bg=self.colors["bg"])
        dialog.transient(self)
        dialog.grab_set()
        dialog.resizable(False, False)

        frame = ttk.Frame(dialog, padding=16)
        frame.grid(row=0, column=0, sticky="nsew")
        ttk.Label(
            frame,
            text="Pressing Confirm will run eloscrape for all gamemodes from scratch. Continue?",
            wraplength=360,
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 14))

        def close():
            dialog.grab_release()
            dialog.destroy()

        def confirm():
            close()
            self.run_recalculate_all()

        ttk.Button(frame, text="Cancel", command=close).grid(row=1, column=0, sticky="e", padx=(0, 8))
        ttk.Button(frame, text="Confirm", style="Tool.TButton", command=confirm).grid(row=1, column=1, sticky="e")
        dialog.protocol("WM_DELETE_WINDOW", close)
        dialog.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width() - dialog.winfo_width()) // 2
        y = self.winfo_rooty() + (self.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{max(x, 0)}+{max(y, 0)}")

    def run_recalculate_all(self):
        if self.recalculate_running:
            return
        self.recalculate_running = True
        self.recalculate_button.configure(state="disabled")
        if self.startup_eloscrape_running and not self.startup_eloscrape_done.is_set():
            self.update_eloscrape_progress(0, "Waiting for current eloscrape before recalculating")
            threading.Thread(target=self.wait_then_recalculate_all, daemon=True).start()
            return
        self.start_recalculate_all_thread()

    def wait_then_recalculate_all(self):
        self.startup_eloscrape_done.wait()
        self.start_recalculate_all_thread()

    def start_recalculate_all_thread(self):
        self.startup_eloscrape_running = True
        self.startup_eloscrape_done.clear()
        self.after(0, lambda: self.update_eloscrape_progress(0, "Eloscrape: recalculating all modes from scratch"))
        threading.Thread(target=self.recalculate_all_in_background, daemon=True).start()

    def recalculate_all_in_background(self):
        tours = [tour for tour in TOURS.values() if tour.get("eloscrape") or tour.get("inhouse") or tour.get("dry_elo")]
        total = len(tours)
        try:
            for index, tour in enumerate(tours, start=1):
                base_progress = 100 * (index - 1) / total if total else 0
                progress_span = 100 / total if total else 100

                def progress_callback(percent, message, t=tour, base=base_progress, span=progress_span):
                    overall = base + (span * percent / 100)
                    status = f"Recalculating: {t['label']} - {message}" if message else f"Recalculating: {t['label']}"
                    self.after(0, lambda p=overall, s=status: self.update_eloscrape_progress(p, s))

                self.after(0, lambda t=tour, p=base_progress: self.update_eloscrape_progress(p, f"Recalculating: {t['label']}"))
                try:
                    self.sync_tour_from_sheet(tour)
                    if tour.get("dry_elo"):
                        if progress_callback:
                            progress_callback(10, "Refreshing stats and elos")
                        from modules.support.mvpGenerator import update_dry_elos_for_tour

                        update_dry_elos_for_tour(tour)
                        if progress_callback:
                            progress_callback(100, "Dry elo updated")
                    else:
                        self.clear_eloscrape_local_state(tour)
                        self.run_tour_eloscrape(
                            tour,
                            progress_callback,
                            use_local_cache=False,
                            ignore_sheet_cache=True,
                        )
                    completed_progress = 100 * index / total if total else 100
                    self.after(0, lambda p=completed_progress, t=tour: self.update_eloscrape_progress(p, f"Recalculating: {t['label']} done"))
                except Exception as exc:
                    error_message = f"{tour['label']}: {type(exc).__name__}: {exc}"
                    self.startup_eloscrape_errors.append(error_message)
                    completed_progress = 100 * index / total if total else 100
                    self.after(0, lambda p=completed_progress, e=error_message: self.update_eloscrape_progress(p, f"Recalculate failed: {e}"))
            self.after(0, lambda: self.update_eloscrape_progress(100, "Eloscrape finished"))
        finally:
            self.recalculate_running = False
            self.startup_eloscrape_running = False
            self.startup_eloscrape_done.set()
            self.after(0, self.finish_recalculate_all)

    def clear_eloscrape_local_state(self, tour):
        state_path = Path(tour["state_path"])
        for filename in ("eloscrape_state.json", "eloscrape_cache.json"):
            path = state_path / filename
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass

    def finish_recalculate_all(self):
        self.recalculate_button.configure(state="normal")
        self.refresh_elos()
        self.refresh_update_info()
        self.set_status("Eloscrape recalculation finished.")

    def run_startup_eloscrape(self):
        tours = [tour for tour in TOURS.values() if tour.get("eloscrape") or tour.get("inhouse") or tour.get("dry_elo")]
        total = len(tours)
        try:
            self.after(0, lambda: self.update_eloscrape_progress(0, "Sync: checking all tour modes"))
            for index, tour in enumerate(tours, start=1):
                base_progress = 100 * (index - 1) / total if total else 0
                progress_span = 100 / total if total else 100

                def progress_callback(percent, message, t=tour, base=base_progress, span=progress_span):
                    overall = base + (span * percent / 100)
                    status = f"Sync: {t['label']} - {message}" if message else f"Sync: {t['label']}"
                    self.after(0, lambda p=overall, s=status: self.update_eloscrape_progress(p, s))

                self.after(0, lambda t=tour, p=base_progress: self.update_eloscrape_progress(p, f"Sync: {t['label']}"))
                try:
                    self.sync_tour_mode_on_boot(tour, progress_callback)
                    completed_progress = 100 * index / total if total else 100
                    self.after(0, lambda p=completed_progress, t=tour: self.update_eloscrape_progress(p, f"Sync: {t['label']} done"))
                except Exception as exc:
                    error_message = f"{tour['label']}: {type(exc).__name__}: {exc}"
                    self.startup_eloscrape_errors.append(error_message)
                    completed_progress = 100 * index / total if total else 100
                    self.after(0, lambda p=completed_progress, e=error_message: self.update_eloscrape_progress(p, f"Sync failed: {e}"))
            self.after(0, lambda: self.update_eloscrape_progress(100, "Sync finished"))
        finally:
            self.startup_eloscrape_running = False
            self.startup_eloscrape_done.set()
            self.after(0, self.refresh_elos)
            self.after(0, self.refresh_update_info)

    def sync_tour_mode_on_boot(self, tour, progress_callback):
        if tour.get("eloscrape") or tour.get("inhouse"):
            self.sync_tour_from_sheet(tour)
            self.run_tour_eloscrape(tour, progress_callback, use_local_cache=True)
            return
        if tour.get("dry_elo"):
            if progress_callback:
                progress_callback(10, "Refreshing stats and elos")
            from modules.support.mvpGenerator import update_dry_elos_for_tour

            update_dry_elos_for_tour(tour)
            if progress_callback:
                progress_callback(100, "Dry elo updated")

    def sync_tour_from_sheet(self, tour):
        self.sync_ids_from_sheet_if_available(tour)
        if tour.get("eloscrape"):
            self.sync_tourlist_from_sheet(tour)

    def sync_ids_from_sheet_if_available(self, tour):
        sheet_cfg = tour.get("sheet", {})
        if not sheet_cfg.get("tab_ids"):
            return
        from utils import sync_ids_from_sheet

        sync_ids_from_sheet(
            tour["state_path"],
            sheetName=sheet_cfg.get("name", "NGM Stats Export v2"),
            tabIDs=sheet_cfg["tab_ids"],
        )

    def sync_tourlist_from_sheet(self, tour):
        from modules.support.readCredentials import readCredentials

        scrape_cfg = tour["eloscrape"]
        tourlist_cell = scrape_cfg.get("tourlist_cell")
        if not tourlist_cell:
            return

        sheet_name = scrape_cfg.get("sheet_name", tour["sheet"]["name"])
        storage_gid = scrape_cfg.get("elo_storage_gid", tour["sheet"]["elo_storage_gid"])
        gc = readCredentials(tour["state_path"])
        sheet = gc.open(sheet_name)
        wks = sheet.get_worksheet_by_id(storage_gid)
        values = wks.get_values(tourlist_cell)
        sheet_text = values[0][0] if values and values[0] else ""
        links = []
        seen = set()
        for line in sheet_text.splitlines():
            link = line.strip().rstrip("/")
            if not link:
                continue
            key = link.lower()
            if key in seen:
                continue
            links.append(link)
            seen.add(key)

        tourlist_path = Path(tour["state_path"]) / "tourlist.txt"
        tourlist_path.write_text(("\n".join(links) + "\n") if links else "", encoding="utf-8")

    def run_tour_eloscrape(
            self,
            tour,
            progress_callback=None,
            use_local_cache=False,
            force_refresh_tour_ids=None,
            force_refresh_tour_urls=None,
            ignore_sheet_cache=False,
        ):
        from modules.main.eloscrape import EloScrape

        cache_signature = self.eloscrape_cache_signature(tour)
        if use_local_cache:
            if self.eloscrape_cache_is_current(tour, cache_signature):
                if progress_callback:
                    progress_callback(100, "Local cache up to date")
                return "cached"
            if tour.get("eloscrape") or tour.get("inhouse"):
                self.clear_eloscrape_local_state(tour)

        if tour.get("eloscrape"):
            scrape_cfg = tour["eloscrape"]
            eloscraper = EloScrape(
                directory=tour["state_path"],
                tabEloStorage=scrape_cfg.get("elo_storage_gid", tour["sheet"]["elo_storage_gid"]),
                tabEloStorageCell=scrape_cfg.get("elo_storage_cell", tour["sheet"]["elo_storage_cell"]),
                sheetName=scrape_cfg.get("sheet_name", tour["sheet"]["name"]),
                cache_mode=scrape_cfg.get("cache_mode"),
                **scrape_cfg["trueskill"],
            )
            asyncio.run(eloscraper.eloscrape(
                tourlist_cell=scrape_cfg["tourlist_cell"],
                progress_callback=progress_callback,
                force_refresh_tour_ids=force_refresh_tour_ids,
                force_refresh_tour_urls=force_refresh_tour_urls,
                ignore_sheet_cache=ignore_sheet_cache,
            ))
            self.write_eloscrape_cache_manifest(tour, cache_signature)
            return "updated"

        if tour.get("inhouse"):
            inhouse_cfg = tour["inhouse"]
            eloscraper = EloScrape(
                directory=tour["state_path"],
                tabEloStorage=tour["sheet"]["elo_storage_gid"],
                tabEloStorageCell=tour["sheet"]["elo_storage_cell"],
                sheetName=tour["sheet"]["name"],
                cache_mode=inhouse_cfg.get("cache_mode"),
                inhouse_type=inhouse_cfg.get("inhouse_type"),
                **inhouse_cfg["trueskill"],
            )
            asyncio.run(eloscraper.eloscrape(
                backlog_cell=inhouse_cfg.get("backlog_cell"),
                progress_callback=progress_callback,
                ignore_sheet_cache=ignore_sheet_cache,
            ))
            self.write_eloscrape_cache_manifest(tour, cache_signature)
            return "updated"

    def eloscrape_cache_signature(self, tour):
        payload = {
            "version": 3,
            "tour_id": tour["id"],
            "cache_mode": tour.get("eloscrape", {}).get("cache_mode") or tour.get("inhouse", {}).get("cache_mode"),
            "trueskill": tour.get("eloscrape", {}).get("trueskill") or tour.get("inhouse", {}).get("trueskill"),
        }

        if tour.get("eloscrape"):
            payload["source"] = "tourlist"
            payload["tourlist"] = self.tourlist_links(tour)
        elif tour.get("inhouse"):
            payload["source"] = "inhouseData"
            payload["events"] = self.inhouse_signature_events(tour)
            if payload["events"] is None:
                payload["unavailable_at"] = datetime.now(timezone.utc).isoformat()

        text = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
        return {
            "version": payload["version"],
            "source": payload.get("source"),
            "hash": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "payload": payload,
        }

    def inhouse_signature_events(self, tour):
        try:
            from modules.support.inhouseData import load_inhouse_tours

            events = load_inhouse_tours(tour["state_path"], tour["inhouse"]["inhouse_type"])
        except Exception:
            return None
        simplified = []
        for event in events:
            matches = []
            for round_key, round_matches in sorted(event.get("matches_by_round", {}).items(), key=lambda item: str(item[0])):
                for match in round_matches:
                    matches.append({
                        "round": round_key,
                        "p1": match.get("player1", {}).get("id"),
                        "p2": match.get("player2", {}).get("id"),
                        "winner": match.get("winner_id"),
                        "loser": match.get("loser_id"),
                        "scores": match.get("scores", {}),
                    })
            simplified.append({
                "tour_id": event.get("tour_id"),
                "time": str(event.get("time")),
                "matches": matches,
            })
        return simplified

    def eloscrape_cache_is_current(self, tour, signature):
        state_path = Path(tour["state_path"])
        if not (state_path / "elos.json").exists():
            return False
        if not (state_path / "eloscrape_state.json").exists():
            return False
        if tour.get("eloscrape") and self.tourlist_links(tour) and not (state_path / "elo_history.json").exists():
            return False
        if tour.get("eloscrape") and self.tourlist_links(tour) and not (state_path / "elo_history_latest.json").exists():
            return False

        manifest_path = state_path / "eloscrape_cache.json"
        if not manifest_path.exists():
            return False
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return False
        return manifest.get("hash") == signature.get("hash")

    def write_eloscrape_cache_manifest(self, tour, signature):
        manifest = {
            "hash": signature.get("hash"),
            "source": signature.get("source"),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        path = Path(tour["state_path"]) / "eloscrape_cache.json"
        path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    def update_eloscrape_progress(self, percent, message):
        percent = max(0, min(100, percent))
        self.elo_progress_var.set(percent)
        self.elo_progress_text_var.set(f"{percent:.0f}%")
        self.set_eloscrape_status(message)

    def set_eloscrape_status(self, message):
        self.elo_status_var.set(message)
        self.set_status(message)

    def refresh_update_info(self):
        tour = TOURS[self.selected_tour_id]
        self.refresh_challonge_list(tour)
        self.write_update_text(self.default_update_text(tour))

    def refresh_challonge_list(self, tour):
        self.challonge_items = []
        self.challonge_list.delete(0, "end")
        if tour.get("supports_inhouse"):
            self.history_heading_label.configure(text="Events")
            self.selected_challonge_var.set("In-house Results")
            self.refresh_inhouse_event_list(tour)
            return
        if tour.get("dry_elo"):
            self.refresh_previous_tour_list(tour)
            return

        self.history_heading_label.configure(text="Challonges")
        links = self.tourlist_links(tour)
        dates = self.tour_history_dates(tour)
        rows = []
        for fallback_index, link in enumerate(links):
            tour_id = self.tour_id_from_link(link)
            tour_time = dates.get(tour_id, "")
            date_label = tour_time[:10] if tour_time else "No date"
            rows.append((tour_time, fallback_index, date_label, link, tour_id))

        rows.sort(key=lambda item: (self.history_sort_value(item[0]), -item[1]), reverse=True)
        self.challonge_items = rows
        for _tour_time, _fallback_index, date_label, link, _tour_id in rows:
            self.challonge_list.insert("end", f"{date_label}  {link}")

        if rows:
            self.challonge_list.selection_set(0)
            self.on_challonge_selected()
        else:
            self.selected_challonge_var.set("No Challonge selected")

    def refresh_previous_tour_list(self, tour):
        self.history_heading_label.configure(text="Previous Tours")
        rows = self.previous_tour_rows(tour)
        self.challonge_items = rows
        for timestamp, fallback_index, date_label, detail, tour_key in rows:
            self.challonge_list.insert("end", f"{date_label}  {detail}")

        if rows:
            self.challonge_list.selection_set(0)
            self.on_challonge_selected()
        else:
            self.selected_challonge_var.set("No previous tour selected")

    def previous_tour_rows(self, tour):
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

    def default_update_text(self, tour):
        if tour.get("dry_elo"):
            return self.dry_elo_report_text(tour)
        if tour.get("supports_inhouse"):
            return "Make teams, build result rows, then log the finished rounds."
        return ""

    def dry_elo_report_text(self, tour, mvp_text=None, intro=None):
        sections = []
        if intro:
            sections.append(intro)
        if mvp_text is not None:
            sections.append(mvp_text.strip())
        else:
            mvps = self._read_text(tour, "mvps.txt", "").strip()
            if mvps:
                sections.append(mvps)

        changelog = self._read_text(tour, "changelog.txt", "").strip()
        if not changelog:
            changelog = "No rating changes >= 0.15."
        sections.append("# Changelog\n" + changelog)
        return "\n\n".join(sections)

    def mvp_report_text(self, tour, mvp_text):
        if tour and tour.get("dry_elo"):
            return self.dry_elo_report_text(tour, mvp_text=mvp_text)
        return mvp_text.strip()

    def load_latest_inhouse_teams(self, tour):
        if tour["id"] in self.latest_inhouse_teams:
            return self.latest_inhouse_teams[tour["id"]]
        path = Path(tour["state_path"]) / "latest_inhouse_teams.json"
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        self.latest_inhouse_teams[tour["id"]] = data
        return data

    def refresh_inhouse_results_ui(self, tour):
        if not hasattr(self, "inhouse_team_summary"):
            return
        data = self.load_latest_inhouse_teams(tour)
        if not data:
            self.inhouse_team_summary.configure(text="Make teams first, then come back here to record results.")
            self.clear_inhouse_result_rows()
            return
        self.clear_inhouse_result_rows()
        self.inhouse_team_summary.configure(text="Select teams by their T1 names, enter scores, then log results.")

    def clear_inhouse_result_rows(self):
        if not hasattr(self, "inhouse_rows_frame"):
            return
        for child in self.inhouse_rows_frame.winfo_children():
            child.destroy()
        self.inhouse_result_rows = []

    def build_inhouse_result_rows(self):
        tour = TOURS[self.selected_tour_id]
        data = self.load_latest_inhouse_teams(tour)
        self.clear_inhouse_result_rows()
        if not data:
            return
        teams = data.get("teams", {})
        team_labels = [team["label"] for team in teams.values()]
        if len(team_labels) < 2:
            self.inhouse_team_summary.configure(text="At least two teams are needed to log in-house results.")
            return
        team_id_by_label = {team["label"]: team_id for team_id, team in teams.items()}
        rounds_text = self.inhouse_round_count.get().strip()
        if not rounds_text:
            self.inhouse_team_summary.configure(text="Enter the number of rounds, then click Build Result Rows.")
            return
        rounds = int(rounds_text)
        if rounds <= 0:
            raise ValueError("Rounds must be at least 1.")

        headers = ["Round", "Team A", "Score", "Team B", "Score"]
        for column, label in enumerate(headers):
            ttk.Label(self.inhouse_rows_frame, text=label, font=("Segoe UI", 9, "bold")).grid(row=0, column=column, sticky="w", padx=(0, 8), pady=(0, 4))

        self.inhouse_result_rows = []
        for round_number in range(1, rounds + 1):
            row_index = round_number
            team1_var = tk.StringVar(value=team_labels[0])
            team2_var = tk.StringVar(value=team_labels[1])
            team1_score = tk.StringVar(value="")
            team2_score = tk.StringVar(value="")

            ttk.Label(self.inhouse_rows_frame, text=str(round_number)).grid(row=row_index, column=0, sticky="w", padx=(0, 8), pady=2)
            ttk.Combobox(self.inhouse_rows_frame, textvariable=team1_var, values=team_labels, state="readonly", width=18).grid(row=row_index, column=1, sticky="ew", padx=(0, 8), pady=2)
            ttk.Entry(self.inhouse_rows_frame, textvariable=team1_score, width=6).grid(row=row_index, column=2, sticky="w", padx=(0, 8), pady=2)
            ttk.Combobox(self.inhouse_rows_frame, textvariable=team2_var, values=team_labels, state="readonly", width=18).grid(row=row_index, column=3, sticky="ew", padx=(0, 8), pady=2)
            ttk.Entry(self.inhouse_rows_frame, textvariable=team2_score, width=6).grid(row=row_index, column=4, sticky="w", padx=(0, 8), pady=2)
            self.inhouse_result_rows.append({
                "round": round_number,
                "team1": team1_var,
                "team2": team2_var,
                "team1_score": team1_score,
                "team2_score": team2_score,
                "team_id_by_label": team_id_by_label,
            })

    def run_log_inhouse_results(self):
        if self.inhouse_logging:
            return
        try:
            tour = TOURS[self.selected_tour_id]
            event = self.build_inhouse_event()
        except Exception as exc:
            self.write_update_text(f"{type(exc).__name__}: {exc}")
            self.set_status("Could not log in-house results.")
            return
        self.inhouse_logging = True
        self.inhouse_log_button.configure(state="disabled")
        self.write_update_text("Logging in-house results...")
        self.set_status("Logging in-house results...")
        threading.Thread(target=self.log_inhouse_results_background, args=(tour, event), daemon=True).start()

    def build_inhouse_event(self):
        tour = TOURS[self.selected_tour_id]
        data = self.load_latest_inhouse_teams(tour)
        if not data:
            raise ValueError("Make teams before logging results.")
        if not self.inhouse_result_rows:
            raise ValueError("Build result rows first.")

        event_time = datetime.now(timezone.utc)
        event_id = f"{tour['id']}_{event_time.strftime('%Y%m%d_%H%M%S')}"
        matches = []
        for row in self.inhouse_result_rows:
            team1_id = row["team_id_by_label"][row["team1"].get()]
            team2_id = row["team_id_by_label"][row["team2"].get()]
            if team1_id == team2_id:
                raise ValueError(f"Round {row['round']} uses the same team twice.")
            score1 = int(row["team1_score"].get())
            score2 = int(row["team2_score"].get())
            if score1 == score2:
                winner_id = None
                loser_id = None
            elif score1 > score2:
                winner_id = team1_id
                loser_id = team2_id
            else:
                winner_id = team2_id
                loser_id = team1_id
            matches.append({
                "round": row["round"],
                "team1_id": team1_id,
                "team2_id": team2_id,
                "team1_score": score1,
                "team2_score": score2,
                "winner": winner_id,
                "loser": loser_id,
            })

        return {
            "source": "inhouse",
            "inhouse_type": tour["inhouse"]["inhouse_type"],
            "tour_id": event_id,
            "time": event_time.isoformat(),
            "teams": data["teams"],
            "matches": matches,
        }

    def log_inhouse_results_background(self, tour, event):
        try:
            from modules.support.inhouseData import append_inhouse_event

            rows_written = append_inhouse_event(tour["state_path"], event)
            self.append_local_inhouse_event(tour, event)
            self.run_tour_eloscrape(tour)
        except Exception as exc:
            details = traceback.format_exc()
            self.after(0, lambda: self.finish_log_inhouse_results(error=f"{type(exc).__name__}: {exc}\n\n{details}"))
            return
        self.after(0, lambda: self.finish_log_inhouse_results(rows_written=rows_written))

    def append_local_inhouse_event(self, tour, event):
        path = Path(tour["state_path"]) / "inhouse_events.json"
        events = []
        if path.exists():
            try:
                events = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                events = []
        events.append(event)
        path.write_text(json.dumps(events, indent=2), encoding="utf-8")

    def finish_log_inhouse_results(self, rows_written=0, error=None):
        self.inhouse_logging = False
        self.inhouse_log_button.configure(state="normal")
        if error:
            self.write_update_text(error)
            self.set_status("In-house logging failed.")
            return
        self.write_update_text(f"Logged {rows_written} result rows to inhouseData and updated elos.")
        self.set_status("In-house results logged.")
        self.refresh_elos()
        self.refresh_challonge_list(TOURS[self.selected_tour_id])

    def refresh_inhouse_event_list(self, tour):
        path = Path(tour["state_path"]) / "inhouse_events.json"
        if not path.exists():
            return
        try:
            events = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return
        for index, event in enumerate(reversed(events)):
            label = f"{event.get('time', '')[:19]}  {len(event.get('matches', []))} rounds"
            self.challonge_list.insert("end", label)
            self.challonge_items.append((event.get("time", ""), index, event.get("time", "")[:10], label, event.get("tour_id", "")))

    def tourlist_links(self, tour):
        text = self._read_text(tour, "tourlist.txt", "")
        links = []
        for line in text.splitlines():
            line = line.strip()
            if line:
                links.append(line)
        return links

    def tour_history_dates(self, tour):
        history_path = Path(tour["state_path"]) / "elo_history.json"
        if not history_path.exists():
            return {}
        try:
            with history_path.open(encoding="utf-8") as f:
                history = json.load(f)
        except (OSError, json.JSONDecodeError):
            return {}
        return {str(entry.get("tour_id", "")).lower(): str(entry.get("time", "")) for entry in history if entry.get("tour_id")}

    def history_sort_value(self, value):
        if not value:
            return float("-inf")
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            return float("-inf")
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.timestamp()

    def tour_id_from_link(self, link):
        link = link.rstrip("/")
        return link.split("/")[-1].split("?")[0].lower()

    def on_challonge_selected(self, _event=None):
        selected = self.challonge_list.curselection()
        if not selected:
            return
        index = selected[0]
        if index >= len(self.challonge_items):
            return
        _tour_time, _fallback_index, date_label, link, _tour_id = self.challonge_items[index]
        self.selected_challonge_var.set(f"{date_label}  {link}")

    def select_challonge_by_tour_id(self, tour_id):
        selected_key = str(tour_id).strip().lower()
        for index, item in enumerate(self.challonge_items):
            if str(item[4]).strip().lower() == selected_key:
                self.challonge_list.selection_clear(0, "end")
                self.challonge_list.selection_set(index)
                self.challonge_list.see(index)
                self.on_challonge_selected()
                return True
        return False

    def run_update_elos(self):
        if self.update_elos_running:
            return
        tour = TOURS[self.selected_tour_id]
        if not tour.get("dry_elo"):
            self.set_status("This tour does not use dry elo updates.")
            return
        self.update_elos_running = True
        self.update_elos_button.configure(state="disabled")
        self.write_update_text("Updating elos...")
        self.set_status("Updating elos...")
        threading.Thread(target=self.update_elos_in_background, args=(tour,), daemon=True).start()

    def update_elos_in_background(self, tour):
        try:
            from modules.support.mvpGenerator import update_dry_elos_for_tour

            updated_elos = update_dry_elos_for_tour(tour)
        except Exception as exc:
            details = traceback.format_exc()
            self.after(0, lambda: self.finish_update_elos(error=f"{type(exc).__name__}: {exc}\n\n{details}"))
            return
        self.after(0, lambda: self.finish_update_elos(tour=tour, updated_count=len(updated_elos)))

    def finish_update_elos(self, tour=None, updated_count=0, error=None):
        self.update_elos_running = False
        self.update_elos_button.configure(state="normal")
        if error:
            self.write_update_text(error)
            self.set_status("Update elos failed.")
            return
        self.refresh_elos()
        self.write_update_text(self.dry_elo_report_text(tour, intro=f"Updated {updated_count} elo ratings."))
        self.set_status("Elos updated.")

    def run_view_changelog(self):
        if self.mvp_running:
            return
        tour = TOURS[self.selected_tour_id]
        if tour.get("dry_elo"):
            self.run_mvp_for_selected()
            return
        self.mvp_running = True
        self.mvp_run_button.configure(state="disabled")
        self.download_changelog_button.configure(state="disabled")
        message = "Waiting for eloscrape to finish..." if self.startup_eloscrape_running else "Loading changelog..."
        self.write_update_text(message)
        self.set_status(message)
        threading.Thread(target=self.changelog_in_background, args=(tour, self.selected_changelog_tour_id()), daemon=True).start()

    def changelog_in_background(self, tour, selected_tour_id=None):
        try:
            self.startup_eloscrape_done.wait()
            if tour.get("eloscrape"):
                self.sync_tour_from_sheet(tour)
                self.run_tour_eloscrape(tour, use_local_cache=True)
            changelog_text = self.selected_changelog_text(tour, selected_tour_id)
        except Exception as exc:
            details = traceback.format_exc()
            self.after(0, lambda: self.finish_view_changelog(error=f"{type(exc).__name__}: {exc}\n\n{details}"))
            return
        self.after(0, lambda: self.finish_view_changelog(tour=tour, changelog_text=changelog_text))

    def finish_view_changelog(self, tour=None, changelog_text=None, error=None):
        self.mvp_running = False
        self.mvp_run_button.configure(state="normal")
        self.download_changelog_button.configure(state="normal")
        if error:
            self.write_update_text(error)
            self.set_status("Changelog failed.")
            return
        self.write_update_text(changelog_text or "")
        self.set_status("Changelog loaded.")

    def latest_changelog_path(self, tour):
        return Path(tour["state_path"]) / "elo_history_latest.json"

    def selected_changelog_tour_id(self):
        selected = self.challonge_list.curselection()
        if selected:
            index = selected[0]
            if index < len(self.challonge_items):
                return self.challonge_items[index][4]
        return None

    def selected_changelog_entry(self, tour, selected_tour_id=None):
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
            raise ValueError(f"No changelog found for selected Challonge {selected_tour_id}.")

        changelog_path = self.latest_changelog_path(tour)
        if not changelog_path.exists():
            raise FileNotFoundError(f"No elo_history_latest.json found for {tour['label']}. Run eloscrape first.")
        try:
            return json.loads(changelog_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"Could not read elo_history_latest.json for {tour['label']}.") from exc

    def selected_changelog_text(self, tour, selected_tour_id=None):
        return json.dumps(self.selected_changelog_entry(tour, selected_tour_id), indent=2, ensure_ascii=False)

    def latest_changelog_text(self, tour):
        changelog_path = self.latest_changelog_path(tour)
        if not changelog_path.exists():
            raise FileNotFoundError(f"No elo_history_latest.json found for {tour['label']}. Run eloscrape first.")

        changelog_text = changelog_path.read_text(encoding="utf-8")
        try:
            return json.dumps(json.loads(changelog_text), indent=2, ensure_ascii=False)
        except json.JSONDecodeError:
            return changelog_text

    def download_selected_changelog(self):
        tour = TOURS[self.selected_tour_id]
        selected_tour_id = self.selected_changelog_tour_id()
        try:
            changelog_text = self.selected_changelog_text(tour, selected_tour_id)
        except Exception as exc:
            self.write_update_text(f"{type(exc).__name__}: {exc}")
            self.set_status("No changelog file found.")
            return
        safe_id = re.sub(r"[^A-Za-z0-9_-]+", "_", selected_tour_id or "latest").strip("_") or "latest"
        self.download_content_to_downloads(tour, f"{safe_id}_elo_history.json", changelog_text)

    def download_dry_outputs(self):
        tour = TOURS[self.selected_tour_id]
        missing = []
        for filename in ("mvps.txt", "changelog.txt"):
            if not (Path(tour["state_path"]) / filename).exists():
                missing.append(filename)
        if missing:
            self.write_update_text(f"Missing {', '.join(missing)}. Run MVPs and Update Elos first.")
            self.set_status("No file found.")
            return
        destinations = [
            self.download_file_to_downloads(tour, Path(tour["state_path"]) / "mvps.txt", announce=False),
            self.download_file_to_downloads(tour, Path(tour["state_path"]) / "changelog.txt", announce=False),
        ]
        self.set_status("Saved MVPs and changelog.")
        self.write_update_text("Saved files to:\n" + "\n".join(str(path) for path in destinations if path))

    def download_named_tour_file(self, tour, filename, missing_message):
        source = Path(tour["state_path"]) / filename
        if not source.exists():
            self.write_update_text(missing_message)
            self.set_status("No file found.")
            return
        self.download_file_to_downloads(tour, source)

    def download_content_to_downloads(self, tour, filename, content):
        downloads = Path.home() / "Downloads"
        downloads.mkdir(parents=True, exist_ok=True)
        source_name = Path(filename)
        destination = downloads / f"{tour['id']}_{source_name.name}"
        counter = 2
        while destination.exists():
            destination = downloads / f"{tour['id']}_{source_name.stem}_{counter}{source_name.suffix}"
            counter += 1
        try:
            destination.write_text(content, encoding="utf-8")
        except OSError as exc:
            self.write_update_text(f"Could not save file: {exc}")
            self.set_status("Download failed.")
            return None
        self.set_status(f"Downloaded {destination.name}.")
        self.write_update_text(f"Saved file to:\n{destination}")
        return destination

    def download_file_to_downloads(self, tour, source, announce=True):
        downloads = Path.home() / "Downloads"
        downloads.mkdir(parents=True, exist_ok=True)
        destination = downloads / f"{tour['id']}_{source.name}"
        counter = 2
        while destination.exists():
            destination = downloads / f"{tour['id']}_{source.stem}_{counter}{source.suffix}"
            counter += 1

        try:
            shutil.copyfile(source, destination)
        except OSError as exc:
            self.write_update_text(f"Could not save file: {exc}")
            self.set_status("Download failed.")
            return None

        if announce:
            self.set_status(f"Downloaded {destination.name}.")
            self.write_update_text(f"Saved file to:\n{destination}")
        return destination

    def run_mvp_for_selected(self):
        if self.mvp_running:
            return
        tour = TOURS[self.selected_tour_id]
        selected = self.challonge_list.curselection()
        selected_tour_id = None
        if selected:
            index = selected[0]
            if index < len(self.challonge_items):
                _tour_time, _fallback_index, date_label, link, selected_tour_id = self.challonge_items[index]
                self.selected_challonge_var.set(f"{date_label}  {link}")
        self.mvp_running = True
        self.mvp_run_button.configure(state="disabled")
        self.write_update_text("Generating MVPs...")
        self.set_status("Generating MVPs...")
        threading.Thread(target=self.mvp_in_background, args=(tour, selected_tour_id), daemon=True).start()

    def mvp_in_background(self, tour, selected_tour_id=None):
        try:
            from modules.support.mvpGenerator import generate_mvps_for_tour

            mvp_text = generate_mvps_for_tour(tour, selected_tour_id=selected_tour_id)
        except Exception as exc:
            details = traceback.format_exc()
            self.after(0, lambda: self.finish_mvp_generation(error=f"{type(exc).__name__}: {exc}\n\n{details}"))
            return
        self.after(0, lambda: self.finish_mvp_generation(tour=tour, mvp_text=mvp_text))

    def finish_mvp_generation(self, tour=None, mvp_text=None, error=None):
        self.mvp_running = False
        self.mvp_run_button.configure(state="normal")
        if error:
            self.write_update_text(error)
            self.set_status("MVP generation failed.")
            return
        self.write_update_text(self.mvp_report_text(tour, mvp_text))
        self.set_status("MVPs generated.")

    def write_update_text(self, text):
        self.update_info.configure(state="normal")
        self.update_info.delete("1.0", "end")
        self.update_info.insert("end", text)
        self.update_info.configure(state="disabled")

    def refresh_elos(self):
        for item in self.elos_table.get_children():
            self.elos_table.delete(item)

        tour = TOURS[self.selected_tour_id]
        elos_path = Path(tour["state_path"]) / "elos.json"
        if not elos_path.exists():
            self.set_status("No elos.json found for this tour.")
            return

        try:
            with elos_path.open(encoding="utf-8") as f:
                elos = json.load(f)
        except json.JSONDecodeError:
            self.set_status("Could not read elos.json.")
            return

        alias_names = self.elo_alias_names(tour, elos)
        query = self.normalize_alias_key(self.elos_search_var.get().strip())
        for player, elo in sorted(elos.items(), key=lambda item: item[1], reverse=True):
            if query and not self.elo_matches_search(player, alias_names.get(player, []), query):
                continue
            self.elos_table.insert("", "end", values=(player, elo))

    def elo_alias_names(self, tour, elos):
        names = {player: {player} for player in elos}
        idtable_path = Path(tour["state_path"]) / "ids.csv"
        if not idtable_path.exists():
            return names
        try:
            from modules.support.getAliases import getAliasesDF

            aliases = getAliasesDF(str(idtable_path))
            aliases["Player Name"] = aliases["Player Name"].astype(str).str.strip()
            aliases["_key"] = aliases["Player Name"].str.lower()
            aliases_by_id = aliases.groupby("Player ID")["Player Name"].apply(list).to_dict()
            id_by_name = dict(zip(aliases["_key"], aliases["Player ID"]))
        except Exception:
            return names

        for player in elos:
            player_id = id_by_name.get(player.lower())
            if player_id in aliases_by_id:
                names[player].update(aliases_by_id[player_id])
        return names

    def elo_matches_search(self, player, aliases, query):
        candidates = set(aliases)
        candidates.add(player)
        return any(query in self.normalize_alias_key(candidate) for candidate in candidates)

    def _read_text(self, tour: dict, filename: str, fallback: str) -> str:
        path = Path(tour["state_path"]) / filename
        if not path.exists():
            return fallback
        return path.read_text(encoding="utf-8")

    def clipboard_from_text(self, text_widget: tk.Text):
        text = text_widget.get("1.0", "end").strip()
        self.clipboard_clear()
        self.clipboard_append(text)
        self.set_status("Copied.")

    def set_status(self, message: str):
        self.title(f"AMQ Host Script - {message}")


def main():
    app = AMQTourUI()
    app.mainloop()


if __name__ == "__main__":
    main()
