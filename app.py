# Name: Jaden Griffith / Keagan Weinstock
# File: app.py
# Frontend Routing (FastAPI)

import os
import uuid
import json
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from pymongo import MongoClient
from dotenv import load_dotenv
from game_engine import GameEngine

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mongo
client = MongoClient(os.getenv("MONGO_URI"))
db = client[os.getenv("DB_NAME")]

# ----------- Request Models -----------

class NewGameRequest(BaseModel):
    player_name: str = "Player"
    ai_difficulty: str = "medium"

class QuestionRequest(BaseModel):
    category: str
    value: int

class AnswerRequest(BaseModel):
    category: str
    value: int
    answer: str
    player_buzz_time: float = 999
    bot_buzz_times: dict = {}

class DailyDoubleRequest(BaseModel):
    category: str
    value: int
    wager: int
    answer: str

class FinalRequest(BaseModel):
    wager: int
    answer: str

class PlayerAnswerRequest(BaseModel):
    category: str
    value: int
    answer: str

# ----------- Routes -----------

@app.get("/", response_class=HTMLResponse)
def index():
    with open("templates/index.html") as f:
        return f.read()

@app.post("/api/new-game")
def new_game(data: NewGameRequest):
    player_name = data.player_name.strip().title()
    ai_difficulty = data.ai_difficulty
    game_id = str(uuid.uuid4())

    try:
        result = GameEngine.create(player_name, ai_difficulty, game_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/game/{game_id}")
def get_game(game_id: str):
    engine = GameEngine(game_id)
    return engine.get_state()

@app.get("/api/active-games")
def active_games():
    games = list(db.games.find({"status": "active"}))
    result = []

    for g in games:
        player = db.players.find_one({"game_id": g["game_id"]})
        remaining = db.board.count_documents({
            "game_id": g["game_id"],
            "selected": False
        })

        result.append({
            "game_id": g["game_id"],
            "player_name": player["name"] if player else "Unknown",
            "round": g.get("round", 1),
            "remaining": remaining,
            "created_at": str(g.get("created_at", ""))
        })

    return result

@app.get("/api/history")
def get_history():
    history_file = os.path.join(os.path.dirname(__file__), "history.json")

    if not os.path.exists(history_file):
        return []

    with open(history_file, "r") as f:
        try:
            return list(reversed(json.load(f)))
        except Exception:
            return []

@app.post("/api/question/{game_id}")
def get_question(game_id: str, data: QuestionRequest):
    engine = GameEngine(game_id)
    payload = engine.get_question_payload(data.category, data.value)

    if not payload:
        raise HTTPException(status_code=400, detail="Question already used or not found")

    return payload

@app.post("/api/answer/{game_id}")
def submit_answer(game_id: str, data: AnswerRequest):
    engine = GameEngine(game_id)

    result = engine.submit_answer(
        data.category,
        data.value,
        data.answer.strip(),
        data.player_buzz_time,
        data.bot_buzz_times
    )

    if not result:
        raise HTTPException(status_code=400, detail="Invalid question")

    return result

@app.post("/api/daily-double/{game_id}")
def daily_double(game_id: str, data: DailyDoubleRequest):
    engine = GameEngine(game_id)

    result = engine.submit_daily_double(
        data.category,
        data.value,
        data.wager,
        data.answer.strip()
    )

    if not result:
        raise HTTPException(status_code=400, detail="Invalid question")

    return result

@app.get("/api/final/{game_id}")
def get_final(game_id: str):
    engine = GameEngine(game_id)
    payload = engine.get_final_payload()

    if not payload:
        raise HTTPException(status_code=404, detail="No Final Jeopardy found")

    return payload

@app.post("/api/final/{game_id}")
def submit_final(game_id: str, data: FinalRequest):
    engine = GameEngine(game_id)

    result = engine.submit_final(data.wager, data.answer.strip())

    if not result:
        raise HTTPException(status_code=404, detail="No Final Jeopardy found")

    return result

@app.post("/api/end-game/{game_id}")
def end_game(game_id: str):
    engine = GameEngine(game_id)
    return engine.end_game()

@app.post("/api/player-answer/{game_id}")
def player_answer(game_id: str, data: PlayerAnswerRequest):
    engine = GameEngine(game_id)

    result = engine.submit_player_answer(
        data.category,
        data.value,
        data.answer.strip()
    )

    if not result:
        raise HTTPException(status_code=400, detail="Invalid question")

    return result