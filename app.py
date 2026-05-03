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

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

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
# BOT CLASS (mirrors models/bot.py exactly)
# -----------------------------
class Bot:
    def __init__(self, name, difficulty):
        self.name = name
        self.difficulty = difficulty
        if difficulty == "easy":
            self.buzz_low = 1.2
            self.buzz_high = 2.0
            self.accuracy = 3
        elif difficulty == "medium":
            self.buzz_low = 0.7
            self.buzz_high = 1.3
            self.accuracy = 2
        else:
            self.buzz_low = 0.2
            self.buzz_high = 0.8
            self.accuracy = 1

    def buzz(self):
        return round(random.uniform(self.buzz_low, self.buzz_high), 3)

    def answer(self, correct_answer, incorrect_answers):
        answers = incorrect_answers[:self.accuracy].copy()
        answers.append(correct_answer)
        return random.choice(answers)


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
        time.sleep(0.2 * (attempt + 1))
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

def assign_daily_doubles(game_id):
    """Mirrors db_init.py assign_daily_doubles()"""
    board = list(db.board.find({"game_id": game_id}))
    if len(board) < 2:
        return
    dd_cells = random.sample(board, 2)
    for cell in dd_cells:
        db.board.update_one(
            {"_id": cell["_id"]},
            {"$set": {"is_daily_double": True}}
        )

def generate_buzz_times(bots_data):
    """Generate bot buzz times server-side so client can't cheat"""
    buzz_times = {}
    for b in bots_data:
        bot = Bot(b["name"], b["difficulty"])
        buzz_times[b["name"]] = bot.buzz()
    return buzz_times


# -----------------------------
# ROUTES
# -----------------------------
@app.route("/")
def index():
    return render_template("index.html")

# -----------------------------
# NEW GAME
# -----------------------------
@app.route("/api/new-game", methods=["POST"])
def new_game():
    data = request.json
    player_name = data.get("player_name", "Player").strip().title()
    ai_difficulty = data.get("ai_difficulty", "medium")
    game_id = str(uuid.uuid4())

    ai_1, ai_2 = pick_ai_names(player_name)

    for col in ["categories", "questions", "board", "players", "bots", "games", "final_game"]:
        db[col].delete_many({"game_id": game_id})

    try:
        cat_data = requests.get("https://opentdb.com/api_category.php", timeout=5).json()
        all_categories = cat_data["trivia_categories"]
        random.shuffle(all_categories)
    except:
        return jsonify({"error": "Failed to fetch categories."}), 500

    # Pick 5 working categories
    selected_categories = []
    used_ids = set()
    for cat in all_categories:
        if len(selected_categories) == 5:
            break
        if cat["id"] in used_ids:
            continue
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

    board_docs = []
    for cat in selected_categories:
        for value in VALUES:
            difficulty = DIFFICULTY_MAP[value]
            q = fetch_question(cat["id"], difficulty)
            if not q:
                q = fetch_question(cat["id"], "easy")
            if not q:
                q = fetch_question(cat["id"], "medium")
            if not q:
                continue

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
                "selected": False,
                "is_daily_double": False
            })

    db.board.insert_many(board_docs)

    # Assign 2 daily doubles (mirrors db_init.py)
    assign_daily_doubles(game_id)

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

    # Final Jeopardy question (mirrors db_init.py)
    final_q = fetch_question(
        random.choice(selected_categories)["id"],
        "hard"
    )
    if final_q:
        db.final_game.insert_one({
            "game_id": game_id,
            "question": html.unescape(final_q["question"]),
            "correct_answer": html.unescape(final_q["correct_answer"]),
            "incorrect_answers": [html.unescape(x) for x in final_q["incorrect_answers"]],
            "status": "not_started",
            "wagers": {},
            "answers": {},
            "results": {}
        })

    store_player_name(player_name)

    return jsonify({"game_id": game_id, "player": player_name, "ai_1": ai_1, "ai_2": ai_2})

# -----------------------------
# GET GAME STATE
# -----------------------------
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
        categories[cat][item["value"]] = {
            "selected": item["selected"],
            "is_daily_double": item.get("is_daily_double", False)
        }

    return jsonify({
        "game_id": game_id,
        "round": game.get("round", 1),
        "player": {"name": player["name"], "score": player["score"]},
        "bots": [{"name": b["name"], "score": b["score"], "difficulty": b["difficulty"]} for b in bots],
        "board": categories,
        "remaining": db.board.count_documents({"game_id": game_id, "selected": False})
    })

# -----------------------------
# LIST ACTIVE GAMES
# -----------------------------
@app.route("/api/active-games", methods=["GET"])
def active_games():
    games = list(db.games.find({"status": "active"}))
    result = []
    for g in games:
        player = db.players.find_one({"game_id": g["game_id"]})
        remaining = db.board.count_documents({"game_id": g["game_id"], "selected": False})
        result.append({
            "game_id": g["game_id"],
            "player_name": player["name"] if player else "Unknown",
            "round": g.get("round", 1),
            "remaining": remaining,
            "created_at": str(g.get("created_at", ""))
        })
    return jsonify(result)

# -----------------------------
# HISTORY
# -----------------------------
@app.route("/api/history", methods=["GET"])
def get_history():
    history_file = os.path.join(os.path.dirname(__file__), "history.json")
    if not os.path.exists(history_file):
        return jsonify([])
    with open(history_file, "r") as f:
        try:
            history = json.load(f)
        except:
            history = []
    return jsonify(list(reversed(history)))

# -----------------------------
# SELECT QUESTION (returns question + pre-generated bot buzz times)
# Bot buzz times are generated SERVER-SIDE so the client can't cheat
# -----------------------------
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
    bots = list(db.bots.find({"game_id": game_id}))
    is_dd = board_item.get("is_daily_double", False)

    all_answers = question["incorrect_answers"] + [question["correct_answer"]]
    random.shuffle(all_answers)

    # Generate bot buzz times server-side
    bot_buzz_times = generate_buzz_times(bots)

    return jsonify({
        "question": question["question"],
        "answers": all_answers,
        "correct_answer": question["correct_answer"],
        "value": value,
        "category": category,
        "is_daily_double": is_dd,
        "bot_buzz_times": bot_buzz_times  # {bot_name: buzz_time_seconds}
    })

# -----------------------------
# SUBMIT ANSWER (normal round)
# player_buzz_time sent from frontend (time they clicked buzz in)
# Compared against bot buzz times to determine who answered
# -----------------------------
@app.route("/api/answer/<game_id>", methods=["POST"])
def submit_answer(game_id):
    data = request.json
    category = data.get("category")
    value = int(data.get("value"))
    player_answer = data.get("answer", "").strip()
    player_buzz_time = float(data.get("player_buzz_time", 999))
    bot_buzz_times = data.get("bot_buzz_times", {})  # sent back from frontend

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
    bots_data = list(db.bots.find({"game_id": game_id}))
    player = db.players.find_one({"game_id": game_id})

    # Build ordered participant list by buzz time
    participants = [{"name": "player", "display_name": player["name"], "buzz_time": player_buzz_time, "is_player": True}]
    for b in bots_data:
        participants.append({
            "name": b["name"],
            "display_name": b["name"],
            "buzz_time": bot_buzz_times.get(b["name"], 999),
            "is_player": False,
            "difficulty": b["difficulty"]
        })
    participants.sort(key=lambda x: x["buzz_time"])

    # Only the FIRST person in buzz order gets to answer
    # Everyone else does not get a turn
    first = participants[0]
    results = []
    round_winner = None

    if first["is_player"]:
        # Player buzzed first — use their answer
        is_correct = player_answer.lower() == correct.lower()
        results.append({
            "name": "player",
            "display_name": player["name"],
            "is_player": True,
            "answer": player_answer,
            "correct": is_correct,
            "buzz_time": first["buzz_time"]
        })
        if is_correct:
            db.players.update_one({"game_id": game_id}, {"$inc": {"score": value}})
            round_winner = "player"
        else:
            db.players.update_one({"game_id": game_id}, {"$inc": {"score": -value}})
    else:
        # A bot buzzed first — bot answers, player doesn't get to answer
        bot_data = next((b for b in bots_data if b["name"] == first["name"]), None)
        bot = Bot(bot_data["name"], bot_data["difficulty"])
        bot_answer = bot.answer(correct, question["incorrect_answers"])
        is_correct = bot_answer.lower() == correct.lower()

        results.append({
            "name": first["name"],
            "display_name": first["name"],
            "is_player": False,
            "answer": bot_answer,
            "correct": is_correct,
            "buzz_time": first["buzz_time"]
        })

        if is_correct:
            db.bots.update_one({"game_id": game_id, "name": first["name"]}, {"$inc": {"score": value}})
            round_winner = first["name"]
        else:
            db.bots.update_one({"game_id": game_id, "name": first["name"]}, {"$inc": {"score": -value}})

    # Mark question used and increment round
    db.board.update_one({"question_id": board_item["question_id"]}, {"$set": {"selected": True}})
    db.games.update_one({"game_id": game_id}, {"$inc": {"round": 1}})

    remaining = db.board.count_documents({"game_id": game_id, "selected": False})
    player_buzzed_first = first["is_player"]

    return jsonify({
        "player_buzzed_first": player_buzzed_first,
        "player_correct": results[0]["correct"] if player_buzzed_first else False,
        "correct_answer": correct,
        "results": results,
        "all_buzz_times": [{"name": p["display_name"], "buzz_time": p["buzz_time"], "is_player": p["is_player"]} for p in participants],
        "round_winner": round_winner,
        "remaining": remaining,
        "game_over": remaining == 0
    })

# -----------------------------
# DAILY DOUBLE ANSWER
# Player always gets DD since they clicked it
# Bot wager logic mirrors game_engine.py exactly
# -----------------------------
@app.route("/api/daily-double/<game_id>", methods=["POST"])
def daily_double(game_id):
    data = request.json
    category = data.get("category")
    value = int(data.get("value"))
    player_wager = int(data.get("wager", 0))
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
    player = db.players.find_one({"game_id": game_id})
    bots_data = list(db.bots.find({"game_id": game_id}))

    # Clamp player wager
    player_score = player["score"]
    max_wager = max(200, player_score)
    player_wager = max(0, min(player_wager, max_wager))

    player_correct = player_answer.lower() == correct.lower()
    delta = player_wager if player_correct else -player_wager
    db.players.update_one({"game_id": game_id}, {"$inc": {"score": delta}})

    # Bots don't get to answer on player's DD
    # But show their buzz times for flavor
    bot_results = []
    for b in bots_data:
        bot = Bot(b["name"], b["difficulty"])
        buzz = bot.buzz()
        bot_results.append({"name": b["name"], "buzz_time": buzz})

    db.board.update_one({"question_id": board_item["question_id"]}, {"$set": {"selected": True}})
    db.games.update_one({"game_id": game_id}, {"$inc": {"round": 1}})

    remaining = db.board.count_documents({"game_id": game_id, "selected": False})

    return jsonify({
        "player_correct": player_correct,
        "correct_answer": correct,
        "wager": player_wager,
        "delta": delta,
        "remaining": remaining,
        "game_over": remaining == 0
    })

# -----------------------------
# FINAL JEOPARDY
# Mirrors game_engine.py play_final_jeopardy() exactly
# -----------------------------
@app.route("/api/final/<game_id>", methods=["GET"])
def get_final(game_id):
    final = db.final_game.find_one({"game_id": game_id})
    if not final:
        return jsonify({"error": "No Final Jeopardy found"}), 404

    player = db.players.find_one({"game_id": game_id})

    return jsonify({
        "question": final["question"],
        "answers": final.get("incorrect_answers", []) + [final["correct_answer"]],
        "status": final.get("status", "not_started"),
        "player_score": player["score"]
    })

@app.route("/api/final/<game_id>", methods=["POST"])
def submit_final(game_id):
    data = request.json
    player_wager = int(data.get("wager", 0))
    player_answer = data.get("answer", "").strip()

    final = db.final_game.find_one({"game_id": game_id})
    if not final:
        return jsonify({"error": "No Final Jeopardy found"}), 404

    player = db.players.find_one({"game_id": game_id})
    bots_data = list(db.bots.find({"game_id": game_id}))
    correct = final["correct_answer"]

    wagers = {}
    answers = {}
    results = {}

    # Player wager clamp
    player_score = player["score"]
    max_wager = max(0, player_score)
    player_wager = max(0, min(player_wager, max_wager))
    wagers["player"] = player_wager
    answers["player"] = player_answer

    # Bot wagers (mirrors game_engine.py exactly)
    for b in bots_data:
        bot_doc = db.bots.find_one({"game_id": game_id, "name": b["name"]})
        bot_score = bot_doc["score"]
        bot_max = max(0, bot_score)
        if b["difficulty"] == "hard":
            wager_pct = random.uniform(0.7, 1.0)
        elif b["difficulty"] == "medium":
            wager_pct = random.uniform(0.3, 0.7)
        else:
            wager_pct = random.uniform(0.0, 0.4)
        wagers[b["name"]] = int(bot_max * wager_pct)

    # Bot answers
    for b in bots_data:
        bot = Bot(b["name"], b["difficulty"])
        answers[b["name"]] = bot.answer(correct, final["incorrect_answers"])

    # Score player
    player_correct = player_answer.lower() == correct.lower()
    delta = player_wager if player_correct else -player_wager
    db.players.update_one({"game_id": game_id}, {"$inc": {"score": delta}})
    results["player"] = {"correct": player_correct, "wager": player_wager, "delta": delta, "answer": player_answer}

    # Score bots
    for b in bots_data:
        bot_correct = answers[b["name"]].lower() == correct.lower()
        bot_delta = wagers[b["name"]] if bot_correct else -wagers[b["name"]]
        db.bots.update_one({"game_id": game_id, "name": b["name"]}, {"$inc": {"score": bot_delta}})
        results[b["name"]] = {"correct": bot_correct, "wager": wagers[b["name"]], "delta": bot_delta, "answer": answers[b["name"]]}

    # Persist result
    db.final_game.update_one(
        {"game_id": game_id},
        {"$set": {"status": "completed", "wagers": wagers, "answers": answers, "results": results}}
    )

    # Build reveal list
    reveal = [{"name": player["name"], "is_player": True, **results["player"]}]
    for b in bots_data:
        reveal.append({"name": b["name"], "is_player": False, **results[b["name"]]})

    return jsonify({
        "correct_answer": correct,
        "reveal": reveal
    })

# -----------------------------
# END GAME
# -----------------------------
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
        "winner": {"name": winner["name"], "score": winner["score"]},
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

    for col in ["categories", "questions", "board", "players", "bots", "games", "final_game"]:
        db[col].delete_many({"game_id": game_id})

    return jsonify({"winner": winner, "all_scores": all_participants})

if __name__ == "__main__":
    app.run(debug=True)
