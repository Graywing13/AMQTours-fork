from modules.support.readCredentials import readCredentials
import os

def saveElos(directory, sheetID, sheetName, cell, elos_path, tourlist_path=None, tourlist_cell=None, backlog_path=None, backlog_cell=None):
    gc = readCredentials(directory)
    sheet = gc.open(sheetName)
    wks = sheet.get_worksheet_by_id(sheetID)

    with open(elos_path) as f:
        data = f.read()
        wks.update_acell(cell, data)

    if backlog_path and backlog_cell:
        with open(backlog_path) as f:
            backlog_data = f.read()
            wks.update_acell(backlog_cell, backlog_data)

    if tourlist_path and tourlist_cell:
        with open(os.path.join(directory, "tourlist.txt")) as t:
            tourlist_data = t.read()
            wks.update_acell(tourlist_cell, tourlist_data)