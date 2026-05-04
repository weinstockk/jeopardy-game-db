# Name: Keagan Weinstock
# File: db_init.py
# Initializes the database that we will use during gameplay

import os
import time
import random
import html
import requests
from datetime import datetime
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

client = MongoClient(os.getenv("MONGO_URI"))
db = client[os.getenv("DB_NAME")]

# JEOPARDY CONFIG
VALUES = [200, 400, 600, 800, 1000]

DIFFICULTY_MAP = {
    200: "easy",
    400: "easy",
    600: "medium",
    800: "medium",
    1000: "hard"
}

# API CALL WITH RETRY
def fetch_question(cat_id, difficulty, max_retries=8):
    """
    Reliable OpenTDB fetcher.
    Retries ONLY when response_code != 0.
    """

    url = (
        f"https://opentdb.com/api.php?"
        f"amount=1&category={cat_id}"
        f"&difficulty={difficulty}&type=multiple"
    )

    for attempt in range(max_retries):
        res = requests.get(url).json()

        if res.get("response_code") == 0 and res.get("results"):
            return res["results"][0]

        # IMPORTANT: wait before retrying (prevents API spam issues)
        time.sleep(0.2 * (attempt + 1))

    return None

# ASSIGN DAILY DOUBLES
def assign_daily_doubles(game_id):
    board = list(db.board.find({"game_id": game_id}))

    if len(board) < 2:
        raise Exception("Not enough board cells to assign Daily Doubles")

    dd_cells = random.sample(board, 2)

    for cell in dd_cells:
        db.board.update_one(
            {"_id": cell["_id"]},
            {"$set": {"is_daily_double": True}}
        )


# INITIALIZE GAME
def initialize_game(game_id: str, config: dict):

    print(f"\nInitializing game: {game_id}\n")

    # CLEAN ONLY THIS GAME
    db.categories.delete_many({"game_id": game_id})
    db.questions.delete_many({"game_id": game_id})
    db.board.delete_many({"game_id": game_id})
    db.players.delete_many({"game_id": game_id})
    db.bots.delete_many({"game_id": game_id})
    db.games.delete_many({"game_id": game_id})

    # 1. GET 5 CATEGORIES
    cat_data = requests.get(
        "https://opentdb.com/api_category.php"
    ).json()

    selected_categories = random.sample(
        cat_data["trivia_categories"], 5
    )

    category_map = {}

    for cat in selected_categories:
        res = db.categories.insert_one({
            "game_id": game_id,
            "name": cat["name"],
            "otdb_id": cat["id"]
        })

        category_map[cat["id"]] = {
            "db_id": res.inserted_id,
            "name": cat["name"]
        }

    # 2. BUILD 5x5 BOARD (CORE FIX)
    questions_docs = []
    board_docs = []

    for cat in selected_categories:
        for value in VALUES:

            difficulty = DIFFICULTY_MAP[value]

            q = fetch_question(cat["id"], difficulty)

            if not q:
                raise Exception(
                    f"Failed to fetch question for "
                    f"{cat['name']} - {difficulty}"
                )

            # QUESTION DOCUMENT
            question_doc = {
                "game_id": game_id,
                "category_id": category_map[cat["id"]]["db_id"],
                "category_name": cat["name"],

                "question": html.unescape(q["question"]),
                "correct_answer": html.unescape(q["correct_answer"]),
                "incorrect_answers": [
                    html.unescape(x) for x in q["incorrect_answers"]
                ],

                "difficulty": difficulty,
                "value": value
            }

            q_id = db.questions.insert_one(question_doc).inserted_id

            # BOARD DOCUMENT
            board_docs.append({
                "game_id": game_id,
                "category_id": category_map[cat["id"]]["db_id"],
                "category_name": cat["name"],
                "value": value,
                "question_id": q_id,
                "selected": False   # IMPORTANT for game engine
            })

    db.board.insert_many(board_docs)

    assign_daily_doubles(game_id)

    # 3. PLAYER
    player = db.players.insert_one({
        "game_id": game_id,
        "name": config["player_name"],
        "score": 0,
        "created_at": datetime.utcnow()
    })

    # 4. BOTS
    db.bots.insert_many([
        {
            "game_id": game_id,
            "name": config["ai_1"],
            "difficulty": config["ai_difficulty"],
            "score": 0
        },
        {
            "game_id": game_id,
            "name": config["ai_2"],
            "difficulty": config["ai_difficulty"],
            "score": 0
        }
    ])

    # 5. GAME STATE
    db.games.insert_one({
        "game_id": game_id,
        "status": "active",
        "turn": "player",
        "round": 1,
        "created_at": datetime.utcnow(),
        "player_id": player.inserted_id
    })

    # 6. FINAL JEOPARDY
    final_q = fetch_question(
        random.choice(selected_categories)["id"],
        "hard"
    )

    db.final_game.insert_one({
        "game_id": game_id,

        "question": html.unescape(final_q["question"]),
        "correct_answer": html.unescape(final_q["correct_answer"]),
        "incorrect_answers": [
            html.unescape(x) for x in final_q["incorrect_answers"]
        ],

        "status": "not_started",
        "wagers": {},
        "answers": {},
        "results": {}
    })

    print(f"Game {game_id} initialized successfully!")