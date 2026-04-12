import random
import os

AI_FILE = "ai_names.txt"

def load_ai_names():
    if not os.path.exists(AI_FILE):
        return []

    with open(AI_FILE, "r") as f:
        names = [line.strip() for line in f if line.strip()]

    return names

def pick_ai_names(player_name):
    names = load_ai_names()

    if player_name in names:
        names.remove(player_name)

    # fallback if file is empty
    if len(names) < 2:
        return ["AI-1", "AI-2"]

    return random.sample(names, 2)

def store_player_name(name):
    names = load_ai_names()

    if name not in names:
        with open(AI_FILE, "a") as f:
            f.write(name + "\n")