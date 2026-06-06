from pathlib import Path


def find_project_root(start) -> Path:
    path = Path(start).resolve()
    if path.is_file():
        path = path.parent

    for candidate in (path, *path.parents):
        if (candidate / "config" / "tours.json").exists():
            return candidate

    return path.parent
