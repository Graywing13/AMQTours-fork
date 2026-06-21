import os

def find_codes_path(script_dir):
    parent_dir = os.path.abspath(os.path.join(script_dir, os.pardir))
    candidates = [
        os.path.join(script_dir, "codes.txt"),
        os.path.join(os.getcwd(), "codes.txt"),
        os.path.join(parent_dir, "codes.txt"),
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return candidates[0]


def read_codes_text(script_dir):
    codes_path = find_codes_path(script_dir)
    if not os.path.exists(codes_path):
        return ""
    with open(codes_path, "r", encoding="utf-8") as codes_file:
        return codes_file.read()