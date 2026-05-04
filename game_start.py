# Name: Keagan Weinstock
# File: game_start.py
# Used to test the logic without the frontend

import uuid
from game_engine import GameEngine


def start_game():
    choice = input("New game or load game? (new/load): ").strip().lower()

    if choice == "new":
        player_name = input("Player name: ").strip().title()
        ai_difficulty = input("AI difficulty (easy/medium/hard): ").strip()
        game_id = str(uuid.uuid4())

        result = GameEngine.create(player_name, ai_difficulty, game_id)
        print(f"Game started: {result['game_id']}")
        print(f"Opponents: {result['player']} vs {result['ai_1']} vs {result['ai_2']}")

        GameEngine(game_id).run()

    elif choice == "load":
        game_id = input("Enter Game ID: ").strip()
        GameEngine(game_id).run()

    else:
        print("Invalid choice")


if __name__ == "__main__":
    start_game()