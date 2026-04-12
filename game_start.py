from db_init import initialize_game
from name_setup.ai_name_utils import pick_ai_names, store_player_name
import uuid

def start_game():

    game_id = str(uuid.uuid4())

    player_name = input("Player name: ")
    ai_difficulty = input("AI difficulty (easy/medium/hard): ")

    ai_1, ai_2 = pick_ai_names(player_name)

    config = {
        "player_name": player_name,
        "ai_difficulty": ai_difficulty,
        "ai_1": ai_1,
        "ai_2": ai_2
    }

    initialize_game(game_id, config)
    store_player_name(player_name)

    print(f"Game started: {game_id}")
    print(f"Opponents: {player_name} vs {ai_1} vs {ai_2}")


if __name__ == "__main__":
    start_game()