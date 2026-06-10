from __future__ import annotations

import csv
import json
import os
from pathlib import Path

from modules.support.mvpGenerator import update_dry_elos_for_tour
from modules.support.readCredentials import readCredentials
from modules.support.readElos import save_elos


class TierMaker:
    def __init__(
        self,
        directory,
        sheetName,
        tabStats,
        tabIDs,
        tabEloStorage,
        tabEloStorageCell,
        maxFallbackWindow,
        activeTours,
    ):
        self.directory = directory
        self.sheetName = sheetName
        self.tabStats = tabStats
        self.tabIDs = tabIDs
        self.tabEloStorage = tabEloStorage
        self.tabEloStorageCell = tabEloStorageCell
        self.maxFallbackWindow = maxFallbackWindow
        self.activeTours = activeTours

        self.ELOS = os.path.join(self.directory, "elos.json")
        self.IDTABLE = os.path.join(self.directory, "ids.csv")
        self.STATSTABLE = os.path.join(self.directory, "stats.csv")

    def _tour_config(self, alpha, midpoint, minRating, maxRating, tourType):
        return {
            "id": Path(self.directory).name,
            "label": Path(self.directory).name,
            "state_path": self.directory,
            "dry_elo": True,
            "tour_type": tourType,
            "solver": {
                "stats_type": tourType,
                "stats_tab": self.tabStats,
            },
            "sheet": {
                "name": self.sheetName,
                "tab_ids": self.tabIDs,
                "elo_storage_gid": self.tabEloStorage,
                "elo_storage_cell": self.tabEloStorageCell,
            },
            "tiermaker": {
                "alpha": alpha,
                "midpoint": midpoint,
                "min_rating": minRating,
                "max_rating": maxRating,
                "max_fallback_window": self.maxFallbackWindow,
                "active_tours": self.activeTours,
            },
        }

    def make_tiers(self, alpha, midpoint, minRating, maxRating, tourType, gui=False):
        return update_dry_elos_for_tour(
            self._tour_config(alpha, midpoint, minRating, maxRating, tourType)
        )

    def update_elos(self, tourlist_cell=None, backlog_cell=None):
        gc = readCredentials(self.directory)
        sheet = gc.open(self.sheetName)
        wks_elos = sheet.get_worksheet_by_id(self.tabEloStorage)
        elos = json.loads(wks_elos.get_values(self.tabEloStorageCell)[0][0])
        save_elos(elos, self.ELOS, self.IDTABLE, key_format="composite")

        if backlog_cell:
            inhouse_backlog = json.loads(wks_elos.get_values(backlog_cell)[0][0])
            with open(os.path.join(self.directory, "match_backlog.json"), "w", encoding="utf-8") as f:
                json.dump(inhouse_backlog, f, indent=4)

        if tourlist_cell:
            tourlist_file = os.path.join(self.directory, "tourlist.txt")
            with open(tourlist_file, "w", encoding="utf-8") as t:
                tourlist_content = wks_elos.get_values(tourlist_cell)[0][0]
                t.write(tourlist_content)

    def refresh_stats(self):
        gc = readCredentials(self.directory)
        sheet = gc.open(self.sheetName)
        wks = sheet.get_worksheet_by_id(self.tabStats)
        wks_ids = sheet.get_worksheet_by_id(self.tabIDs)

        with open(self.STATSTABLE, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerows(wks.get_all_values())
        with open(self.IDTABLE, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerows(wks_ids.get_all_values())
