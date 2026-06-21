import os, re

def discover_json_files(json_dir, regex):
    json_files = []
    if not os.path.isdir(json_dir):
        return json_files
    for file_name in os.listdir(json_dir):
        if not file_name.lower().endswith(".json"):
            continue
        songs_played = None
        if not file_name.startswith("amq_song_expoert"):
            reg_match = re.search(regex, file_name)
            if reg_match is not None:
                songs_played = int(reg_match.group(1))
        json_files.append((file_name, songs_played))
    return json_files