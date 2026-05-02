# Name: Keagan Weinstock
# File: game_start.py

from db_init import initialize_game
from game_engine import GameEngine
from name_setup.ai_name_utils import pick_ai_names, store_player_name
import uuid

def start_game():
    choice = input("New game or load game? (new/load): ").strip().lower()  # TODO: Replace with a button selection (new/load)

    # ── New Game ─────────────────────────────────────────────────
    if choice == "new":
        game_id = str(uuid.uuid4())

        player_name = input("Player name: ")  # TODO: Replace with frontend text input field
        player_name = player_name.strip().title()
        ai_difficulty = input("AI difficulty (easy/medium/hard): ")  # TODO: Replace with frontend dropdown (easy/medium/hard)

        ai_1, ai_2 = pick_ai_names(player_name)

        config = {
            "player_name": player_name,
            "ai_difficulty": ai_difficulty,
            "ai_1": ai_1,
            "ai_2": ai_2
        }

        initialize_game(game_id, config)
        store_player_name(player_name)

        print(f"Game started: {game_id}") # TODO: Replace with frontend game lobby/loading screen
        print(f"Opponents: {player_name} vs {ai_1} vs {ai_2}") # TODO: Replace with frontend opponent display

        engine = GameEngine(game_id)
        engine.run()

    # ── Load Game ─────────────────────────────────────────────────
    elif choice == "load":
        game_id = input("Enter Game ID: ").strip()  # TODO: Replace with frontend text input or saved game picker

        engine = GameEngine(game_id)
        engine.run()

    # ── Invalid ───────────────────────────────────────────────────
    else:
        print("Invalid choice") # TODO: Replace with frontend validation (disable submission until valid option selected)


if __name__ == "__main__":
    start_game()