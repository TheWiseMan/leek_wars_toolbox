import requests
import time
import sys
import getpass
import os
import json
import argparse

API_URL = "https://leekwars.com/api"
REQUEST_DELAY = 1
FOLDER_SEPARATOR = "/"
BACKUP_FOLDER = "./__backups__"

# -------------------------------------------------------
# Config loading
# -------------------------------------------------------
def load_config(path: str) -> dict:
    with open(path, "r") as f:
        return json.load(f)


# -------------------------------------------------------
# Hyperlink formatting
# -------------------------------------------------------
def format_hyperlink(uri: str, label: str | None = None) -> str:
    if sys.platform.startswith("win"):
        if label:
            return f"{label} ({uri})"
        return uri
    if label:
        return f"\033]8;;{uri}\033\\{label}\033]8;;\033\\"
    return uri


def format_farmer(session: requests.Session, farmer_id: str) -> str:
    url = f"{API_URL}/farmer/get/{farmer_id}"
    response = session.get(url).json()
    farmer = response["farmer"]
    farmer_url = f"https://leekwars.com/farmer/{farmer_id}"
    farmer_name = farmer["name"]
    farmer_level = farmer["total_level"]
    farmer_talent = farmer["talent"]
    farmer_ranking = farmer["ranking"]
    name_formatted = format_hyperlink(farmer_url, farmer_name)
    return f"{name_formatted} - {farmer_level} ({farmer_talent} ^{farmer_ranking})"

def format_leek(session: requests.Session, leek_id: str) -> str:
    url = f"{API_URL}/leek/get/{leek_id}"
    response = session.get(url).json()
    leek = response
    leek_url = f"https://leekwars.com/leek/{leek_id}"
    leek_name = leek["name"]
    leek_level = leek["level"]
    leek_talent = leek["talent"]
    leek_ranking = leek["ranking"]
    name_formatted = format_hyperlink(leek_url, leek_name)
    return f"{name_formatted} - {leek_level} ({leek_talent} ^{leek_ranking})"

def format_compo(session: requests.Session, compo_id: str) -> str:
    url = f"{API_URL}/team/composition-rich-tooltip/{compo_id}"
    response = session.get(url).json()
    team_id = response["team"]["id"]
    team_url = f"https://leekwars.com/team/{team_id}"
    team_name = response["team"]["name"]
    team_formatted = format_hyperlink(team_url, team_name)
    compo_name = response["name"]
    compo_talent = response["talent"]
    compo_leeks_n = len(response["leeks"])
    compo_level = response["total_level"]
    return f"{team_formatted}/{compo_name} - {compo_level}/{compo_leeks_n} ({compo_talent})"


# -------------------------------------------------------
# Leek Wars API helpers
# -------------------------------------------------------
def get_session_token(username: str, password: str):
    session = requests.Session()
    response = session.post(
        f"{API_URL}/farmer/login-token",
        data={"login": username, "password": password}
    )
    response.raise_for_status()
    return session, response.json()


def start_farmer_fight(session: requests.Session, opponent: int):
    url = f"{API_URL}/garden/start-farmer-fight"
    response = session.post(url, data={"target_id": opponent})
    response.raise_for_status()
    return response.json()


def start_solo_fight(session: requests.Session, leekid: int, opponent: int):
    url = f"{API_URL}/garden/start-solo-fight"
    response = session.post(url, data={"leek_id": leekid, "target_id": opponent})
    response.raise_for_status()
    return response.json()

def start_team_fight(session: requests.Session, compoid: int, opponent: int):
    url = f"{API_URL}/garden/start-team-fight"
    response = session.post(url, data={"composition_id": compoid, "target_id": opponent})
    response.raise_for_status()
    return response.json()


# -------------------------------------------------------
# Automated fights
# -------------------------------------------------------
def auto_farmer_fight(session, amount, sorter):
    for i in range(amount):
        opponents = session.get(
            f"{API_URL}/garden/get-farmer-opponents"
        ).json()["opponents"]

        sorted_opponents = sorter(opponents)
        best = sorted_opponents[0]
        best_id = best["id"]

        farmer_profile = format_farmer(session, best_id)
        print(f"Farmer fight {i+1}/{amount} {farmer_profile}")

        start_farmer_fight(session, best["id"])
        time.sleep(1)


def auto_leek_fight(session, leekid, amount, sorter):
    for i in range(amount):
        opponents = session.get(
           f"{API_URL}/garden/get-leek-opponents/{leekid}"
        ).json()["opponents"]

        sorted_opponents = sorter(opponents)
        best = sorted_opponents[0]
        best_id = best["id"]

        leek_profile = format_leek(session, best_id)
        print(f"Leek fight {i+1}/{amount} {leek_profile}")

        start_solo_fight(session, leekid, best_id)
        time.sleep(1)

def auto_composition_fight(session, compoid, amount, sorter):
    for i in range(amount):
        opponents = session.get(
           f"{API_URL}/garden/get-composition-opponents/{compoid}"
        ).json()["opponents"]

        sorted_opponents = sorter(opponents)
        best = sorted_opponents[0]
        best_id = best["id"]

        compo_profile = format_compo(session, best_id)
        print(f"Team fight {i+1}/{amount} {compo_profile}")

        start_team_fight(session, compoid, best_id)
        time.sleep(1)


# -------------------------------------------------------
# Backups
# -------------------------------------------------------
def backup_farmer_ais(session):
    response = session.get(f"{API_URL}/ai/get-farmer-ais").json()
    folders = response["folders"]
    folder_dict = {}
    folder_path = {}
    for folder in folders:
        folder_dict[folder["id"]] = folder
    for folder in folders:
        _path = [folder["name"]]
        _parent_id = folder["folder"]
        while _parent_id != 0:
            _parent = folder_dict[_parent_id]
            _parent_id = _parent["folder"]
            _path = [_parent["name"]] + _path
        folder_path[folder["id"]] = BACKUP_FOLDER + FOLDER_SEPARATOR + FOLDER_SEPARATOR.join(_path)
    folder_path[0] = BACKUP_FOLDER
    for folder in folders:
        _id = folder["id"]
        backup_path = folder_path[_id]
        if not os.path.exists(backup_path):
            os.makedirs(backup_path)

    ais = response["ais"]
    L = len(ais)
    i = 0
    for _ai in ais:
        time.sleep(REQUEST_DELAY)
        print(f"backing up ais : {i}/{L}")
        _id = _ai["id"]
        _name = _ai["name"]
        _folder = _ai["folder"]
        _path = folder_path[_folder] + FOLDER_SEPARATOR + _name + ".leekscript"
        code = session.get(f"{API_URL}/ai/get/{_id}").json()["ai"]["code"]
        with open(_path, "w") as f:
            f.write(code)
        i += 1


# -------------------------------------------------------
# Program
# -------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LeekWars automation script")
    parser.add_argument(
        "config",
        nargs="?",
        help="Path to a JSON config file (optional; falls back to interactive prompts)"
    )
    args = parser.parse_args()

    config = {}
    if args.config:
        config = load_config(args.config)
        print(f"Loaded config from {args.config}")
        print(f"{config}")

    # --- Credentials ---
    if "password" in config:
        print("Warning: 'password' found in config file and will be ignored. Passwords are always prompted.")
    username = config.get("username") or input("Username: ")
    password = getpass.getpass("Password: ")

    session, data = get_session_token(username, password)
    farmer = data["farmer"]
    farmer_id = farmer["id"]
    farmer_fights = farmer["fights"]
    team_fights = farmer["team_fights"]

    print("Logged in as", format_farmer(session, farmer_id))
    print(f"{farmer_fights}+{team_fights} fights")

    # --- Backup ---
    if "backup_ais" in config:
        do_backup = config["backup_ais"]
    else:
        do_backup = input("Backup ais ? (y/n) ") == "y"

    if do_backup:
        backup_farmer_ais(session)

    # --- Farmer fights ---
    if "farmer_fights" in config:
        farmer_fight_count = config["farmer_fights"]
    else:
        farmer_fight_count = int(input("Farmer fights: "))

    # --- Leek fights ---
    leeks = list(farmer["leeks"].keys())
    leeks_profiles = [format_leek(session, leek_id) for leek_id in leeks]

    config_leek_fights = config.get("leek_fights", [])
    leek_fight_counts = []
    for i, leek_id in enumerate(leeks):
        if i < len(config_leek_fights):
            count = config_leek_fights[i]
            print(f"{leeks_profiles[i]}\t: {count}")
        else:
            count = int(input(f"{leeks_profiles[i]} fights\t: "))
        leek_fight_counts.append(count)

    # --- Composition fights ---
    compositions = list(session.get(f"{API_URL}/team-composition/get-farmer-compositions").json().keys())
    compositions_profiles = [format_compo(session, compo_id) for compo_id in compositions]

    config_compo_fights = config.get("compo_fights", [])
    compo_fight_counts = []
    for i, compo_id in enumerate(compositions):
        if i < len(config_compo_fights):
            count = config_compo_fights[i]
            print(f"{compositions_profiles[i]}\t: {count}")
        else:
            count = int(input(f"{compositions_profiles[i]} fights\t: "))
        compo_fight_counts.append(count)

    # --- Run ---
    sorter = lambda arr: sorted(arr, key=lambda x: x["talent"])

    print("\t---------------")

    auto_farmer_fight(session, farmer_fight_count, sorter)

    for leek_id, count in zip(leeks, leek_fight_counts):
        auto_leek_fight(session, leek_id, count, sorter)

    for compo_id, count in zip(compositions, compo_fight_counts):
        auto_composition_fight(session, compo_id, count, sorter)

    print("done.")
    print("\t===", format_farmer(session, farmer_id), "===")