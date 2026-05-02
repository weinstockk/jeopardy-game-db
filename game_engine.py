# Name: Keagan Weinstock
# File: game_engine.py

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
        print(f"\nStarting game {self.game_id}") # TODO: Replace with frontend game start screen
        print(f"Player: {self.player['name']}") # TODO: Replace with frontend player display

        bots = list(db.bots.find({"game_id": self.game_id}))

        while not self.is_game_over():
            print(f"\n--- ROUND {self.round}/25 ---") # TODO: Replace with frontend round indicator
            self.load_board()

            round_completed = self.play_round(bots)

            if round_completed:
                self.round += 1

            self.sync_state()

        # ── Final Jeopardy ──────────────────────────────────────
        self.play_final_jeopardy(bots)
        self.end_game(bots)

    # ─────────────────────────────────────────────────────────────
    # PLAY ONE ROUND
    # ─────────────────────────────────────────────────────────────
    def play_round(self, bots):

        category = input("\nChoose category: ").strip() # TODO: Replace with frontend board category selection
        value = input("Choose value (200-1000): ").strip() # TODO: Replace with frontend board value selection

        if not value.isdigit():
            print("Invalid value input.") # TODO: Replace with frontend validation
            return False

        dollar_value = int(value)
        question = self.get_question(category, dollar_value)

        # ── Guard: invalid or already used ──────────────────────
        if not question:
            print("Invalid selection or already used.") # TODO: Replace with frontend error state (grey out used cells)
            return False

        board_item = db.board.find_one({
            "game_id": self.game_id,
            "question_id": question["_id"]
        })

        print("\nQUESTION:") # TODO: Replace with frontend question modal
        print(question["question"])

        # ── Daily Double ─────────────────────────────────────────
        is_dd = board_item.get("is_daily_double", False) if board_item else False

        if is_dd:
            print("\nDAILY DOUBLE!") # TODO: Replace with frontend Daily Double reveal animation

            # ── Buzz to determine who gets the DD ───────────────
            order = self.get_buzz_order(bots)
            winner = order[0]

            if winner["name"] == "player":
                player_score = db.players.find_one({"game_id": self.game_id})["score"]
                max_wager = max(200, player_score)
                wager = int(input(f"Your score: ${player_score}. Wager up to {max_wager}: ")) # TODO: Replace with frontend wager input
                wager = max(0, min(wager, max_wager))

                answer = input("Your answer: ").strip() # TODO: Replace with frontend answer input

                if self.check_answer(answer, question):
                    print("Correct!") # TODO: Replace with frontend correct answer feedback
                    self.update_score("player", wager)
                else:
                    print(f"Wrong! The correct answer was: {question['correct_answer']}") # TODO: Replace with frontend wrong answer feedback
                    self.update_score("player", -wager)

            else:
                bot = winner["bot"]
                bot_doc = db.bots.find_one({"game_id": self.game_id, "name": winner["name"]})
                bot_score = bot_doc["score"]
                max_wager = max(200, bot_score)

                # ── Bot wagers based on difficulty ───────────────
                if bot.difficulty == "hard":
                    wager = int(max_wager * random.uniform(0.7, 1.0))
                elif bot.difficulty == "medium":
                    wager = int(max_wager * random.uniform(0.3, 0.7))
                else:
                    wager = int(max_wager * random.uniform(0.0, 0.4))

                bot_answer = bot.answer(question["correct_answer"], question["incorrect_answers"])
                print(f"{winner['name']} buzzed first and gets the Daily Double!") # TODO: Replace with frontend bot DD notification
                print(f"{winner['name']} wagers ${wager} and answers: {bot_answer}")

                if self.check_answer(bot_answer, question):
                    print(f"{winner['name']} is correct!") # TODO: Replace with frontend bot correct answer feedback
                    self.update_score(winner["name"], wager)
                else:
                    print(f"{winner['name']} is wrong! The correct answer was: {question['correct_answer']}") # TODO: Replace with frontend bot wrong answer feedback
                    self.update_score(winner["name"], -wager)

            self.mark_used(question["_id"])
            return True

        # ── Normal Buzz Loop ─────────────────────────────────────
        order = self.get_buzz_order(bots)

        for participant in order:
            name = participant["name"]

            if name == "player":
                answer = input("\nYour answer: ").strip() # TODO: Replace with frontend answer input with buzz-in trigger

                if self.check_answer(answer, question):
                    print(f"{self.player['name']} answered correctly!") # TODO: Replace with frontend correct answer feedback
                    self.update_score("player", dollar_value)
                    self.mark_used(question["_id"])
                    return True
                else:
                    print(f"{self.player['name']} got it wrong!") # TODO: Replace with frontend wrong answer feedback
                    self.update_score("player", -dollar_value)

            else:
                bot = participant["bot"]
                bots_answer = bot.answer(
                    question["correct_answer"],
                    question["incorrect_answers"]
                )
                print(f"{name}: {bots_answer}") # TODO: Replace with frontend bot answer display

                if self.check_answer(bots_answer, question):
                    print(f"{name} answered correctly!") # TODO: Replace with frontend bot correct answer feedback
                    self.update_score(name, dollar_value)
                    self.mark_used(question["_id"])
                    return True
                else:
                    print(f"{name} got it wrong!") # TODO: Replace with frontend bot wrong answer feedback
                    self.update_score(name, -dollar_value)

        print("No correct answers.") # TODO: Replace with frontend no-answer state
        print(f"The correct answer was: {question['correct_answer']}") # TODO: Replace with frontend answer reveal
        self.mark_used(question["_id"])
        return True

    # ─────────────────────────────────────────────────────────────
    # FINAL JEOPARDY
    # ─────────────────────────────────────────────────────────────
    def play_final_jeopardy(self, bots):
        final = db.final_game.find_one({"game_id": self.game_id})

        if not final or final.get("status") == "completed":
            return

        print("\n" + "=" * 40) # TODO: Replace with frontend Final Jeopardy screen transition
        print("       FINAL JEOPARDY")
        print("=" * 40)
        print(f"\nQuestion: {final['question']}") # TODO: Replace with frontend Final Jeopardy question display

        wagers = {}
        answers = {}
        results = {}

        # ── Player wager ─────────────────────────────────────────
        player_score = db.players.find_one({"game_id": self.game_id})["score"]
        max_wager = max(0, player_score)

        print(f"\n{self.player['name']}, your score: ${player_score}") # TODO: Replace with frontend score display
        raw = input(f"Enter your wager (0–{max_wager}): ").strip() # TODO: Replace with frontend wager input (hidden from bots)
        player_wager = int(raw) if raw.isdigit() else 0
        player_wager = max(0, min(player_wager, max_wager))
        wagers["player"] = player_wager

        # ── Bot wagers (silent) ──────────────────────────────────
        for b in bots:
            bot_score = db.bots.find_one(
                {"game_id": self.game_id, "name": b["name"]}
            )["score"]
            bot_max = max(0, bot_score)
            if b["difficulty"] == "hard":
                wager_pct = random.uniform(0.7, 1.0)
            elif b["difficulty"] == "medium":
                wager_pct = random.uniform(0.3, 0.7)
            else:
                wager_pct = random.uniform(0.0, 0.4)
            wagers[b["name"]] = int(bot_max * wager_pct)

        # ── Player answer ────────────────────────────────────────
        player_answer = input("Your answer: ").strip() # TODO: Replace with frontend timed answer input
        answers["player"] = player_answer

        # ── Bot answers ──────────────────────────────────────────
        for b in bots:
            bot = Bot(b["name"], b["difficulty"])
            answers[b["name"]] = bot.answer(
                final["correct_answer"],
                final["incorrect_answers"]
            )

        # ── Reveal & score ───────────────────────────────────────
        print(f"\nCorrect answer: {final['correct_answer']}") # TODO: Replace with frontend answer reveal animation
        print("-" * 40)

        correct = self.check_answer(answers["player"], final)
        delta = wagers["player"] if correct else -wagers["player"]
        self.update_score("player", delta)
        results["player"] = {"correct": correct, "wager": wagers["player"], "delta": delta}
        result_str = "CORRECT" if correct else "WRONG"
        print(f"{self.player['name']}: {answers['player']} — {result_str} (${delta:+,})") # TODO: Replace with frontend player result display

        for b in bots:
            correct = self.check_answer(answers[b["name"]], final)
            delta = wagers[b["name"]] if correct else -wagers[b["name"]]
            self.update_score(b["name"], delta)
            results[b["name"]] = {"correct": correct, "wager": wagers[b["name"]], "delta": delta}
            result_str = "CORRECT" if correct else "WRONG"
            print(f"{b['name']}: {answers[b['name']]} — {result_str} (${delta:+,})") # TODO: Replace with frontend bot result display

        # ── Persist result ───────────────────────────────────────
        db.final_game.update_one(
            {"game_id": self.game_id},
            {"$set": {
                "status": "completed",
                "wagers": wagers,
                "answers": answers,
                "results": results
            }}
        )

    # ─────────────────────────────────────────────────────────────
    # HELPERS
    # ─────────────────────────────────────────────────────────────
    def get_buzz_order(self, bots):
        participants = [{"name": "player", "buzz_time": 0.0, "bot": None}]
        for b in bots:
            bot = Bot(b["name"], b["difficulty"])
            participants.append({
                "name": b["name"],
                "buzz_time": bot.buzz(),
                "bot": bot
            })
        participants.sort(key=lambda x: x["buzz_time"])
        return participants

    def get_question(self, category, value):
        board_item = db.board.find_one({
            "game_id": self.game_id,
            "category_name": category,
            "value": value,
            "selected": False
        })
        if not board_item:
            return None
        return db.questions.find_one({"_id": board_item["question_id"]})

    def check_answer(self, user_answer, question):
        return (
            user_answer.strip().lower()
            == question["correct_answer"].strip().lower()
        )

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

    def mark_used(self, question_id):
        db.board.update_one(
            {"question_id": question_id},
            {"$set": {"selected": True}}
        )

    def is_game_over(self):
        remaining = db.board.count_documents({
            "game_id": self.game_id,
            "selected": False
        })
        return remaining == 0 or self.round > 25

    def end_game(self, bots):
        print("\nGAME OVER") # TODO: Replace with frontend game over screen

        player = db.players.find_one({"game_id": self.game_id})
        bots = list(db.bots.find({"game_id": self.game_id}))

        all_players = [player] + bots
        winner = max(all_players, key=lambda x: x["score"])
        print(f"The winner is: {winner['name']} with ${winner['score']:,}") # TODO: Replace with frontend winner display

        questions = list(db.questions.find({"game_id": self.game_id}))

        snapshot = {
            "game_id": self.game_id,
            "player": {"name": player["name"], "score": player["score"]},
            "bots": [
                {"name": b["name"], "difficulty": b["difficulty"], "score": b["score"]}
                for b in bots
            ],
            "winner": {"name": winner["name"], "score": winner["score"]},
            "total_questions": len(questions),
            "completed_at": time.time()
        }

        # ── Save to history ──────────────────────────────────────
        history_file = "history.json"
        if os.path.exists(history_file):
            with open(history_file, "r") as f:
                try:
                    history = json.load(f)
                except Exception:
                    history = []
        else:
            history = []

        history.append(snapshot)
        with open(history_file, "w") as f:
            json.dump(history, f, indent=2)

        print("Game saved to history.json") # TODO: Replace with frontend save confirmation

        # ── Cleanup ──────────────────────────────────────────────
        db.categories.delete_many({"game_id": self.game_id})
        db.questions.delete_many({"game_id": self.game_id})
        db.board.delete_many({"game_id": self.game_id})
        db.players.delete_many({"game_id": self.game_id})
        db.bots.delete_many({"game_id": self.game_id})
        db.games.delete_many({"game_id": self.game_id})
        db.final_game.delete_many({"game_id": self.game_id})

        print("Game data removed from database")