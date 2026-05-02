# Name: Keagan Weinstock
# File: ia_name_utils.py

import random
import os

AI_FILE = "name_setup\\ai_names.txt"


def normalize_name(name):
    return name.strip().title()

def load_ai_names():
    if not os.path.exists(AI_FILE):
        return []

    with open(AI_FILE, "r") as f:
        return [normalize_name(line) for line in f if line.strip()]


def pick_ai_names(player_name):
    player_name = normalize_name(player_name)
    names = load_ai_names()
    names = [n for n in names if n.lower() != player_name.lower()]

    if len(names) < 2:
        return ["AI-1", "AI-2"]

    return random.sample(names, 2)


def store_player_name(name):
    name = normalize_name(name)
    names = load_ai_names()

    if name.lower() not in [n.lower() for n in names]:
        with open(AI_FILE, "a") as f:
            f.write(name + "\n")