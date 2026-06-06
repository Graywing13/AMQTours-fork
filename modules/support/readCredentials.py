import gspread
from modules.support.paths import find_project_root

def readCredentials(directory):
    project_root = find_project_root(directory)
    gc = gspread.oauth(
        credentials_filename=str(project_root / "credentials" / "credentials.json"),
        authorized_user_filename=str(project_root / "credentials" / "authorized_user.json")
    )
    return gc
