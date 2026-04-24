import os
import random
import json
import time
from pymongo import MongoClient
from dotenv import load_dotenv
from models.bot import Bot

load_dotenv()

client = MongoClient(os.getenv("MONGO_URI"))
db = client[os.getenv("DB_NAME")]


class GameEngine:

    def __init__(self, game_id):
        self.game_id = game_id
        self.game = db.games.find_one({"game_id": game_id})
        self.round = self.game.get("round", 1)
        self.current_turn = self.game.get("turn", "player")
        self.player = db.players.find_one({"game_id": game_id})

    def sync_state(self):
        db.games.update_one(
            {"game_id": self.game_id},
            {
                "$set": {
                    "round": self.round,
                    "turn": self.current_turn
                }
            }
        )

    def load_board(self):
        self.board = list(db.board.find({"game_id": self.game_id}))

    def run(self):

        print(f"\nStarting game {self.game_id}")
        print(f"Player: {self.player['name']}")

        bots = list(db.bots.find({"game_id": self.game_id}))

        while not self.is_game_over():

            print(f"\n--- ROUND {self.round}/25 ---")
            self.load_board()

            round_completed = self.play_round(bots)

            if round_completed:
                self.round += 1

            self.sync_state()

        self.end_game(bots)

    # -------------------------
    # PLAY ONE ROUND
    # -------------------------
    def play_round(self, bots):

        category = input("\nChoose category: ").strip()
        value = input("Choose value (200-1000): ").strip()

        if not value.isdigit():
            print("Invalid value input.")
            return False

        value = int(value)
        question = self.get_question(category, value)

        if not question:
            print("Invalid selection or already used.")
            return False

        print("\nQUESTION:")
        print(question["question"])

        order = self.get_buzz_order(bots)
        value = question["value"]

        # -------------------------
        # BUZZ LOOP
        # -------------------------
        for participant in order:

            name = participant["name"]

            # -------------------------
            # PLAYER
            # -------------------------
            if name == "player":

                answer = input("\nYour answer: ").strip()

                if self.check_answer(answer, question):
                    print(f"{self.player['name']} answered correctly!")
                    self.update_score("player", value)
                    self.mark_used(question["_id"])
                    return True

                else:
                    print(f"{self.player['name']} got it wrong!")
                    self.update_score("player", -value)

            # -------------------------
            # BOT
            # -------------------------
            else:

                bot = participant["bot"]
                bots_answer = bot.answer(question["correct_answer"], question["incorrect_answers"])
                print(f"{name}: {bots_answer}")

                if self.check_answer(bots_answer, question):
                    print(f"{name} answered correctly!")
                    self.update_score(name, value)
                    self.mark_used(question["_id"])
                    return True

                else:
                    print(f"{name} got it wrong!")
                    self.update_score(name, -value)

        print("No correct answers.")
        print(f"The correct answer was {question['correct_answer']}.")
        self.mark_used(question["_id"])
        return True

    def get_buzz_order(self, bots):
        participants = []

        # player instant
        participants.append({
            "name": "player",
            "buzz_time": 0.0,
            "bot": None
        })

        for b in bots:
            bot = Bot(b["name"], b["difficulty"])

            participants.append({
                "name": b["name"],
                "buzz_time": bot.buzz(),
                "bot": bot
            })

        participants.sort(key=lambda x: x["buzz_time"])
        return participants

    # -------------------------
    # QUESTION FETCH
    # -------------------------
    def get_question(self, category, value):

        board_item = db.board.find_one({
            "game_id": self.game_id,
            "category_name": category,
            "value": value,
            "selected": False
        })

        if not board_item:
            return None

        return db.questions.find_one({
            "_id": board_item["question_id"]
        })

    # -------------------------
    # ANSWER CHECK
    # -------------------------
    def check_answer(self, user_answer, question):

        return user_answer.strip().lower() == \
               question["correct_answer"].strip().lower()

    # -------------------------
    # SCORE UPDATE
    # -------------------------
    def update_score(self, name, value):

        if name == "player":

            db.players.update_one(
                {"game_id": self.game_id},
                {"$inc": {"score": value}}
            )

        else:

            db.bots.update_one(
                {"game_id": self.game_id, "name": name},
                {"$inc": {"score": value}}
            )

    # -------------------------
    # MARK QUESTION USED
    # -------------------------
    def mark_used(self, question_id):

        db.board.update_one(
            {"question_id": question_id},
            {"$set": {"selected": True}}
        )

    # -------------------------
    # GAME OVER
    # -------------------------
    def is_game_over(self):
        remaining = db.board.count_documents({
            "game_id": self.game_id,
            "selected": False
        })
        return remaining == 0 or self.round > 25

    # -------------------------
    # END GAME
    # -------------------------
    def end_game(self, bots):
        print("\nGAME OVER")
        winner = max([self.player] + bots, key=lambda x: x["score"])
        print(f"The Winner is: {winner['name']} with {winner['score']} points")

        player = db.players.find_one({"game_id": self.game_id})
        bots = list(db.bots.find({"game_id": self.game_id}))
        questions = list(db.questions.find({"game_id": self.game_id}))

        snapshot = {
            "game_id": self.game_id,
            "player": {
                "name": player["name"],
                "score": player["score"]
            },
            "bots": [
                {
                    "name": b["name"],
                    "difficulty": b["difficulty"],
                    "score": b["score"]
                }
                for b in bots
            ],
            "winner": winner,
            "total_questions": len(questions),
            "completed_at": time.time()
        }

        history_file = "history.json"

        if os.path.exists(history_file):
            with open(history_file, "r") as f:
                try:
                    history = json.load(f)
                except:
                    history = []
        else:
            history = []

        history.append(snapshot)

        with open(history_file, "w") as f:
            json.dump(history, f, indent=2)

        print("Game saved to history.json")

        db.categories.delete_many({"game_id": self.game_id})
        db.questions.delete_many({"game_id": self.game_id})
        db.board.delete_many({"game_id": self.game_id})
        db.players.delete_many({"game_id": self.game_id})
        db.bots.delete_many({"game_id": self.game_id})
        db.games.delete_many({"game_id": self.game_id})

        print("Game data removed from database")