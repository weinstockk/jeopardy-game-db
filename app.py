import os
import uuid
import json
import time
import html
import random
import requests
from datetime import datetime
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

client = MongoClient(os.getenv("MONGO_URI"))
db = client[os.getenv("DB_NAME")]

# -----------------------------
# JEOPARDY CONFIG
# -----------------------------
VALUES = [200, 400, 600, 800, 1000]
DIFFICULTY_MAP = {
    200: "easy",
    400: "easy",
    600: "medium",
    800: "medium",
    1000: "hard"
}

# -----------------------------
# HELPERS
# -----------------------------
def fetch_question(cat_id, difficulty, max_retries=8):
    url = (
        f"https://opentdb.com/api.php?"
        f"amount=1&category={cat_id}"
        f"&difficulty={difficulty}&type=multiple"
    )
    for attempt in range(max_retries):
        try:
            res = requests.get(url, timeout=5).json()
            if res.get("response_code") == 0 and res.get("results"):
                return res["results"][0]
        except:
            pass
        time.sleep(0.3 * (attempt + 1))
    return None

def load_ai_names():
    ai_file = os.path.join(os.path.dirname(__file__), "name_setup", "ai_names.txt")
    if not os.path.exists(ai_file):
        return ["Alex", "Watson", "HAL"]
    with open(ai_file, "r") as f:
        return [line.strip().title() for line in f if line.strip()]

def pick_ai_names(player_name):
    names = load_ai_names()
    names = [n for n in names if n.lower() != player_name.lower()]
    if len(names) < 2:
        return ["AI-1", "AI-2"]
    return random.sample(names, 2)

def store_player_name(name):
    ai_file = os.path.join(os.path.dirname(__file__), "name_setup", "ai_names.txt")
    names = load_ai_names()
    if name.lower() not in [n.lower() for n in names]:
        with open(ai_file, "a") as f:
            f.write(name + "\n")

# -----------------------------
# ROUTES
# -----------------------------
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/new-game", methods=["POST"])
def new_game():
    data = request.json
    player_name = data.get("player_name", "Player").strip().title()
    ai_difficulty = data.get("ai_difficulty", "medium")
    game_id = str(uuid.uuid4())

    ai_1, ai_2 = pick_ai_names(player_name)

    # Clean old data
    for col in ["categories", "questions", "board", "players", "bots", "games"]:
        db[col].delete_many({"game_id": game_id})

    # Get all categories and shuffle so we can swap bad ones
    try:
        cat_data = requests.get("https://opentdb.com/api_category.php", timeout=5).json()
        all_categories = cat_data["trivia_categories"]
        random.shuffle(all_categories)
    except:
        return jsonify({"error": "Failed to fetch categories. Check your internet connection."}), 500

    # Pick 5 working categories - swap out any that can't supply questions
    selected_categories = []
    used_ids = set()
    for cat in all_categories:
        if len(selected_categories) == 5:
            break
        if cat["id"] in used_ids:
            continue
        # Quick check: can this category supply an easy question?
        test_q = fetch_question(cat["id"], "easy", max_retries=2)
        if test_q:
            selected_categories.append(cat)
            used_ids.add(cat["id"])

    if len(selected_categories) < 5:
        return jsonify({"error": "Could not find enough working categories. Try again."}), 500

    category_map = {}
    for cat in selected_categories:
        res = db.categories.insert_one({
            "game_id": game_id,
            "name": cat["name"],
            "otdb_id": cat["id"]
        })
        category_map[cat["id"]] = {"db_id": res.inserted_id, "name": cat["name"]}

    # Build 5x5 board
    board_docs = []
    for cat in selected_categories:
        for value in VALUES:
            difficulty = DIFFICULTY_MAP[value]
            q = fetch_question(cat["id"], difficulty)
            # If a specific difficulty fails, fall back to any difficulty
            if not q:
                q = fetch_question(cat["id"], "easy")
            if not q:
                q = fetch_question(cat["id"], "medium")
            if not q:
                continue  # Skip rather than crash

            question_doc = {
                "game_id": game_id,
                "category_id": category_map[cat["id"]]["db_id"],
                "category_name": cat["name"],
                "question": html.unescape(q["question"]),
                "correct_answer": html.unescape(q["correct_answer"]),
                "incorrect_answers": [html.unescape(x) for x in q["incorrect_answers"]],
                "difficulty": difficulty,
                "value": value
            }
            q_id = db.questions.insert_one(question_doc).inserted_id

            board_docs.append({
                "game_id": game_id,
                "category_id": category_map[cat["id"]]["db_id"],
                "category_name": cat["name"],
                "value": value,
                "question_id": q_id,
                "selected": False
            })

    db.board.insert_many(board_docs)

    player = db.players.insert_one({
        "game_id": game_id,
        "name": player_name,
        "score": 0,
        "created_at": datetime.utcnow()
    })

    db.bots.insert_many([
        {"game_id": game_id, "name": ai_1, "difficulty": ai_difficulty, "score": 0},
        {"game_id": game_id, "name": ai_2, "difficulty": ai_difficulty, "score": 0}
    ])

    db.games.insert_one({
        "game_id": game_id,
        "status": "active",
        "turn": "player",
        "round": 1,
        "created_at": datetime.utcnow(),
        "player_id": player.inserted_id
    })

    store_player_name(player_name)

    return jsonify({"game_id": game_id, "player": player_name, "ai_1": ai_1, "ai_2": ai_2})

@app.route("/api/game/<game_id>", methods=["GET"])
def get_game(game_id):
    game = db.games.find_one({"game_id": game_id})
    if not game:
        return jsonify({"error": "Game not found"}), 404

    player = db.players.find_one({"game_id": game_id})
    bots = list(db.bots.find({"game_id": game_id}))
    board = list(db.board.find({"game_id": game_id}))

    categories = {}
    for item in board:
        cat = item["category_name"]
        if cat not in categories:
            categories[cat] = {}
        categories[cat][item["value"]] = item["selected"]

    return jsonify({
        "game_id": game_id,
        "round": game.get("round", 1),
        "player": {"name": player["name"], "score": player["score"]},
        "bots": [{"name": b["name"], "score": b["score"], "difficulty": b["difficulty"]} for b in bots],
        "board": categories,
        "remaining": db.board.count_documents({"game_id": game_id, "selected": False})
    })

@app.route("/api/question/<game_id>", methods=["POST"])
def get_question(game_id):
    data = request.json
    category = data.get("category")
    value = int(data.get("value"))

    board_item = db.board.find_one({
        "game_id": game_id,
        "category_name": category,
        "value": value,
        "selected": False
    })

    if not board_item:
        return jsonify({"error": "Question already used or not found"}), 400

    question = db.questions.find_one({"_id": board_item["question_id"]})

    all_answers = question["incorrect_answers"] + [question["correct_answer"]]
    random.shuffle(all_answers)

    return jsonify({
        "question": question["question"],
        "answers": all_answers,
        "correct_answer": question["correct_answer"],
        "value": value,
        "category": category
    })

@app.route("/api/answer/<game_id>", methods=["POST"])
def submit_answer(game_id):
    data = request.json
    category = data.get("category")
    value = int(data.get("value"))
    player_answer = data.get("answer", "").strip()

    board_item = db.board.find_one({
        "game_id": game_id,
        "category_name": category,
        "value": value,
        "selected": False
    })

    if not board_item:
        return jsonify({"error": "Invalid question"}), 400

    question = db.questions.find_one({"_id": board_item["question_id"]})
    correct = question["correct_answer"]
    player_correct = player_answer.strip().lower() == correct.strip().lower()

    bots = list(db.bots.find({"game_id": game_id}))
    bot_results = []

    for b in bots:
        difficulty = b["difficulty"]
        if difficulty == "easy":
            buzz_time = random.uniform(1.2, 2.0)
            accuracy = 3
        elif difficulty == "medium":
            buzz_time = random.uniform(0.7, 1.3)
            accuracy = 2
        else:
            buzz_time = random.uniform(0.2, 0.8)
            accuracy = 1

        pool = question["incorrect_answers"][:accuracy] + [correct]
        bot_answer = random.choice(pool)
        bot_correct = bot_answer.strip().lower() == correct.strip().lower()

        bot_results.append({
            "name": b["name"],
            "answer": bot_answer,
            "correct": bot_correct,
            "buzz_time": round(buzz_time, 2)
        })

    # Determine winner of the round
    # Player buzzes at 0.0, bots have random delay
    participants = [{"name": "player", "buzz_time": 0.0, "correct": player_correct}]
    for i, b in enumerate(bot_results):
        participants.append({"name": b["name"], "buzz_time": b["buzz_time"], "correct": b["correct"]})

    participants.sort(key=lambda x: x["buzz_time"])

    round_winner = None
    for p in participants:
        if p["correct"]:
            round_winner = p["name"]
            break

    # Update scores
    if round_winner == "player":
        db.players.update_one({"game_id": game_id}, {"$inc": {"score": value}})
    elif round_winner:
        db.bots.update_one({"game_id": game_id, "name": round_winner}, {"$inc": {"score": value}})

    # Penalize wrong answers
    if not player_correct:
        db.players.update_one({"game_id": game_id}, {"$inc": {"score": -value}})
    for b in bot_results:
        if not b["correct"]:
            db.bots.update_one({"game_id": game_id, "name": b["name"]}, {"$inc": {"score": -value}})

    # Mark used
    db.board.update_one({"question_id": board_item["question_id"]}, {"$set": {"selected": True}})

    # Update round
    db.games.update_one({"game_id": game_id}, {"$inc": {"round": 1}})

    # Check game over
    remaining = db.board.count_documents({"game_id": game_id, "selected": False})

    return jsonify({
        "player_correct": player_correct,
        "correct_answer": correct,
        "bot_results": bot_results,
        "round_winner": round_winner,
        "remaining": remaining,
        "game_over": remaining == 0
    })

@app.route("/api/end-game/<game_id>", methods=["POST"])
def end_game(game_id):
    player = db.players.find_one({"game_id": game_id})
    bots = list(db.bots.find({"game_id": game_id}))
    questions = list(db.questions.find({"game_id": game_id}))

    all_participants = [{"name": player["name"], "score": player["score"]}] + \
                       [{"name": b["name"], "score": b["score"]} for b in bots]
    winner = max(all_participants, key=lambda x: x["score"])

    snapshot = {
        "game_id": game_id,
        "player": {"name": player["name"], "score": player["score"]},
        "bots": [{"name": b["name"], "difficulty": b["difficulty"], "score": b["score"]} for b in bots],
        "winner": winner,
        "total_questions": len(questions),
        "completed_at": time.time()
    }

    history_file = os.path.join(os.path.dirname(__file__), "history.json")
    history = []
    if os.path.exists(history_file):
        with open(history_file, "r") as f:
            try:
                history = json.load(f)
            except:
                history = []
    history.append(snapshot)
    with open(history_file, "w") as f:
        json.dump(history, f, indent=2, default=str)

    for col in ["categories", "questions", "board", "players", "bots", "games"]:
        db[col].delete_many({"game_id": game_id})

    return jsonify({"winner": winner, "all_scores": all_participants})

if __name__ == "__main__":
    app.run(debug=True)
