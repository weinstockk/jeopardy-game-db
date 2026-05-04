# Name: Keagan Weinstock
# File: game_engine.py
# # Rule logic for the game

import os
import random
import json
import time
from pymongo import MongoClient
from dotenv import load_dotenv
from models.bot import Bot
from db_init import initialize_game
from name_setup.ai_name_utils import pick_ai_names, store_player_name

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


    # ─────────────────────────────────────────────────────────────
    # FACTORY
    # ─────────────────────────────────────────────────────────────
    @staticmethod
    def create(player_name, ai_difficulty, game_id):
        ai_1, ai_2 = pick_ai_names(player_name)
        config = {
            "player_name": player_name,
            "ai_difficulty": ai_difficulty,
            "ai_1": ai_1,
            "ai_2": ai_2
        }
        initialize_game(game_id, config)
        store_player_name(player_name)
        return {"game_id": game_id, "player": player_name, "ai_1": ai_1, "ai_2": ai_2}


    # ─────────────────────────────────────────────────────────────
    # STATE
    # ─────────────────────────────────────────────────────────────
    def get_state(self):
        board = list(db.board.find({"game_id": self.game_id}))
        bots = list(db.bots.find({"game_id": self.game_id}))

        categories = {}
        for item in board:
            cat = item["category_name"]
            if cat not in categories:
                categories[cat] = {}
            categories[cat][item["value"]] = {
                "selected": item["selected"],
                "is_daily_double": item.get("is_daily_double", False)
            }

        return {
            "game_id": self.game_id,
            "round": self.round,
            "player": {"name": self.player["name"], "score": self.player["score"]},
            "bots": [{"name": b["name"], "score": b["score"], "difficulty": b["difficulty"]} for b in bots],
            "board": categories,
            "remaining": db.board.count_documents({"game_id": self.game_id, "selected": False})
        }


    # ─────────────────────────────────────────────────────────────
    # SELECT QUESTION
    # ─────────────────────────────────────────────────────────────
    def select_question(self, category, value):
        board_item = db.board.find_one({
            "game_id": self.game_id,
            "category_name": category,
            "value": value,
            "selected": False
        })
        if not board_item:
            return None, None
        question = db.questions.find_one({"_id": board_item["question_id"]})
        return board_item, question

    def get_question_payload(self, category, value):
        board_item, question = self.select_question(category, value)
        if not board_item:
            return None

        bots = list(db.bots.find({"game_id": self.game_id}))
        all_answers = question["incorrect_answers"] + [question["correct_answer"]]
        random.shuffle(all_answers)

        return {
            "question": question["question"],
            "answers": all_answers,
            "correct_answer": question["correct_answer"],
            "value": value,
            "category": category,
            "is_daily_double": board_item.get("is_daily_double", False),
            "bot_buzz_times": self._generate_buzz_times(bots)
        }


    # ─────────────────────────────────────────────────────────────
    # SUBMIT ANSWER
    # ─────────────────────────────────────────────────────────────
    def submit_answer(self, category, value, player_answer, player_buzz_time, bot_buzz_times):
        board_item, question = self.select_question(category, value)
        if not board_item:
            return None

        correct = question["correct_answer"]
        bots_data = list(db.bots.find({"game_id": self.game_id}))

        participants = [
            {"name": "player", "display_name": self.player["name"], "buzz_time": player_buzz_time, "is_player": True}]
        for b in bots_data:
            participants.append({
                "name": b["name"],
                "display_name": b["name"],
                "buzz_time": bot_buzz_times.get(b["name"], 999),
                "is_player": False,
                "difficulty": b["difficulty"]
            })
        participants.sort(key=lambda x: x["buzz_time"])

        results = []
        round_winner = None

        for participant in participants:
            if participant["is_player"]:
                # Player only answers if they actually buzzed (buzz_time < BUZZ_WINDOW)
                if player_buzz_time >= 999:
                    continue
                is_correct = player_answer.lower() == correct.lower()
                delta = value if is_correct else -value
                self.update_score("player", delta)
                results.append({
                    "name": "player",
                    "display_name": self.player["name"],
                    "is_player": True,
                    "answer": player_answer,
                    "correct": is_correct,
                    "buzz_time": participant["buzz_time"]
                })
                if is_correct:
                    round_winner = "player"
                    break
            else:
                bot_data = next(b for b in bots_data if b["name"] == participant["name"])
                bot = Bot(bot_data["name"], bot_data["difficulty"])
                bot_answer = bot.answer(correct, question["incorrect_answers"])
                is_correct = bot_answer.lower() == correct.lower()
                delta = value if is_correct else -value
                self.update_score(participant["name"], delta)
                results.append({
                    "name": participant["name"],
                    "display_name": participant["name"],
                    "is_player": False,
                    "answer": bot_answer,
                    "correct": is_correct,
                    "buzz_time": participant["buzz_time"]
                })
                if is_correct:
                    round_winner = participant["name"]
                    break

        self.mark_used(board_item["question_id"])
        self._increment_round()

        remaining = db.board.count_documents({"game_id": self.game_id, "selected": False})
        player_result = next((r for r in results if r["is_player"]), None)

        return {
            "player_buzzed_first": len(results) > 0 and results[0]["is_player"],
            "player_correct": player_result["correct"] if player_result else False,
            "correct_answer": correct,
            "results": results,
            "all_buzz_times": [{"name": p["display_name"], "buzz_time": p["buzz_time"], "is_player": p["is_player"]} for
                               p in participants],
            "round_winner": round_winner,
            "remaining": remaining,
            "game_over": remaining == 0
        }

    def submit_player_answer(self, category, value, player_answer):
        """Called when player gets a second chance after all bots miss."""
        board_item = db.board.find_one({
            "game_id": self.game_id,
            "category_name": category,
            "value": value,
            "selected": True  # already marked used by submitBotsOnly
        })
        if not board_item:
            return None

        question = db.questions.find_one({"_id": board_item["question_id"]})
        correct = question["correct_answer"]

        is_correct = player_answer.lower() == correct.lower()
        delta = value if is_correct else -value
        self.update_score("player", delta)

        remaining = db.board.count_documents({"game_id": self.game_id, "selected": False})

        return {
            "correct_answer": correct,
            "round_winner": "player" if is_correct else None,
            "results": [{
                "name": "player",
                "display_name": self.player["name"],
                "is_player": True,
                "answer": player_answer,
                "correct": is_correct,
                "buzz_time": self.player.get("buzz_time", 0)
            }],
            "game_over": remaining == 0
        }


    # ─────────────────────────────────────────────────────────────
    # DAILY DOUBLE
    # ─────────────────────────────────────────────────────────────
    def submit_daily_double(self, category, value, player_wager, player_answer):
        board_item, question = self.select_question(category, value)
        if not board_item:
            return None

        correct = question["correct_answer"]
        player_score = db.players.find_one({"game_id": self.game_id})["score"]
        max_wager = max(200, player_score)
        player_wager = max(0, min(player_wager, max_wager))

        is_correct = player_answer.lower() == correct.lower()
        delta = player_wager if is_correct else -player_wager
        self.update_score("player", delta)

        self.mark_used(board_item["question_id"])
        self._increment_round()

        remaining = db.board.count_documents({"game_id": self.game_id, "selected": False})
        return {
            "player_correct": is_correct,
            "correct_answer": correct,
            "wager": player_wager,
            "delta": delta,
            "remaining": remaining,
            "game_over": remaining == 0
        }


    # ─────────────────────────────────────────────────────────────
    # FINAL JEOPARDY
    # ─────────────────────────────────────────────────────────────
    def get_final_payload(self):
        final = db.final_game.find_one({"game_id": self.game_id})
        if not final:
            return None
        player = db.players.find_one({"game_id": self.game_id})
        return {
            "question": final["question"],
            "answers": final.get("incorrect_answers", []) + [final["correct_answer"]],
            "status": final.get("status", "not_started"),
            "player_score": player["score"]
        }

    def submit_final(self, player_wager, player_answer):
        final = db.final_game.find_one({"game_id": self.game_id})
        if not final:
            return None

        correct = final["correct_answer"]
        bots_data = list(db.bots.find({"game_id": self.game_id}))
        player = db.players.find_one({"game_id": self.game_id})

        wagers, answers, results = {}, {}, {}

        player_wager = max(0, min(player_wager, max(0, player["score"])))
        wagers["player"] = player_wager
        answers["player"] = player_answer

        for b in bots_data:
            bot_score = db.bots.find_one({"game_id": self.game_id, "name": b["name"]})["score"]
            pct = {"hard": random.uniform(0.7, 1.0), "medium": random.uniform(0.3, 0.7)}.get(
                b["difficulty"], random.uniform(0.0, 0.4)
            )
            wagers[b["name"]] = int(max(0, bot_score) * pct)

        for b in bots_data:
            bot = Bot(b["name"], b["difficulty"])
            answers[b["name"]] = bot.answer(correct, final["incorrect_answers"])

        player_correct = player_answer.lower() == correct.lower()
        delta = player_wager if player_correct else -player_wager
        self.update_score("player", delta)
        results["player"] = {"correct": player_correct, "wager": player_wager, "delta": delta, "answer": player_answer}

        for b in bots_data:
            bot_correct = answers[b["name"]].lower() == correct.lower()
            bot_delta = wagers[b["name"]] if bot_correct else -wagers[b["name"]]
            self.update_score(b["name"], bot_delta)
            results[b["name"]] = {"correct": bot_correct, "wager": wagers[b["name"]], "delta": bot_delta, "answer": answers[b["name"]]}

        db.final_game.update_one(
            {"game_id": self.game_id},
            {"$set": {"status": "completed", "wagers": wagers, "answers": answers, "results": results}}
        )

        reveal = [{"name": player["name"], "is_player": True, **results["player"]}]
        for b in bots_data:
            reveal.append({"name": b["name"], "is_player": False, **results[b["name"]]})

        return {"correct_answer": correct, "reveal": reveal}


    # ─────────────────────────────────────────────────────────────
    # END GAME
    # ─────────────────────────────────────────────────────────────
    def end_game(self):
        player = db.players.find_one({"game_id": self.game_id})
        bots = list(db.bots.find({"game_id": self.game_id}))
        questions = list(db.questions.find({"game_id": self.game_id}))

        all_participants = [{"name": player["name"], "score": player["score"]}] + \
                           [{"name": b["name"], "score": b["score"]} for b in bots]
        winner = max(all_participants, key=lambda x: x["score"])

        snapshot = {
            "game_id": self.game_id,
            "player": {"name": player["name"], "score": player["score"]},
            "bots": [{"name": b["name"], "difficulty": b["difficulty"], "score": b["score"]} for b in bots],
            "winner": {"name": winner["name"], "score": winner["score"]},
            "total_questions": len(questions),
            "completed_at": time.time()
        }

        history_file = os.path.join(os.path.dirname(__file__), "data/history.json")
        history = []
        if os.path.exists(history_file):
            with open(history_file, "r") as f:
                try:
                    history = json.load(f)
                except Exception:
                    history = []
        history.append(snapshot)
        with open(history_file, "w") as f:
            json.dump(history, f, indent=2, default=str)

        for col in ["categories", "questions", "board", "players", "bots", "games", "final_game"]:
            db[col].delete_many({"game_id": self.game_id})

        return {"winner": winner, "all_scores": all_participants}


    # ─────────────────────────────────────────────────────────────
    # INTERNAL HELPERS
    # ─────────────────────────────────────────────────────────────
    def _generate_buzz_times(self, bots_data):
        return {b["name"]: Bot(b["name"], b["difficulty"]).buzz() for b in bots_data}

    def _increment_round(self):
        self.round += 1
        db.games.update_one({"game_id": self.game_id}, {"$inc": {"round": 1}})

    def update_score(self, name, value):
        if name == "player":
            db.players.update_one({"game_id": self.game_id}, {"$inc": {"score": value}})
        else:
            db.bots.update_one({"game_id": self.game_id, "name": name}, {"$inc": {"score": value}})

    def mark_used(self, question_id):
        db.board.update_one({"question_id": question_id}, {"$set": {"selected": True}})

    def check_answer(self, user_answer, question):
        return user_answer.strip().lower() == question["correct_answer"].strip().lower()

    def is_game_over(self):
        return db.board.count_documents({"game_id": self.game_id, "selected": False}) == 0

    def sync_state(self):
        db.games.update_one({"game_id": self.game_id}, {"$set": {"round": self.round, "turn": self.current_turn}})

    # ─────────────────────────────────────────────────────────────
    # CONSOLE RUNNER
    # ─────────────────────────────────────────────────────────────
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

        self.play_final_jeopardy(bots)
        self.end_game(bots)

    def load_board(self):
        self.board = list(db.board.find({"game_id": self.game_id}))

    def play_round(self, bots):
        category = input("\nChoose category: ").strip()
        value = input("Choose value (200-1000): ").strip()

        if not value.isdigit():
            print("Invalid value input.")
            return False

        dollar_value = int(value)
        board_item, question = self.select_question(category, dollar_value)

        if not board_item:
            print("Invalid selection or already used.")
            return False

        print("\nQUESTION:")
        print(question["question"])

        is_dd = board_item.get("is_daily_double", False)

        if is_dd:
            print("\nDAILY DOUBLE!")
            order = self.get_buzz_order(bots)
            winner = order[0]

            if winner["name"] == "player":
                player_score = db.players.find_one({"game_id": self.game_id})["score"]
                max_wager = max(200, player_score)
                wager = int(input(f"Your score: ${player_score}. Wager up to {max_wager}: "))
                wager = max(0, min(wager, max_wager))
                answer = input("Your answer: ").strip()

                if self.check_answer(answer, question):
                    print("Correct!")
                    self.update_score("player", wager)
                else:
                    print(f"Wrong! The correct answer was: {question['correct_answer']}")
                    self.update_score("player", -wager)

            else:
                bot_data = next(b for b in bots if b["name"] == winner["name"])
                bot = Bot(bot_data["name"], bot_data["difficulty"])
                bot_doc = db.bots.find_one({"game_id": self.game_id, "name": winner["name"]})
                bot_score = bot_doc["score"]
                max_wager = max(200, bot_score)

                if bot.difficulty == "hard":
                    wager = int(max_wager * random.uniform(0.7, 1.0))
                elif bot.difficulty == "medium":
                    wager = int(max_wager * random.uniform(0.3, 0.7))
                else:
                    wager = int(max_wager * random.uniform(0.0, 0.4))

                bot_answer = bot.answer(question["correct_answer"], question["incorrect_answers"])
                print(f"{winner['name']} buzzed first and gets the Daily Double!")
                print(f"{winner['name']} wagers ${wager} and answers: {bot_answer}")

                if self.check_answer(bot_answer, question):
                    print(f"{winner['name']} is correct!")
                    self.update_score(winner["name"], wager)
                else:
                    print(f"{winner['name']} is wrong! The correct answer was: {question['correct_answer']}")
                    self.update_score(winner["name"], -wager)

            self.mark_used(board_item["question_id"])
            return True

        order = self.get_buzz_order(bots)

        for participant in order:
            name = participant["name"]

            if name == "player":
                answer = input("\nYour answer: ").strip()

                if self.check_answer(answer, question):
                    print(f"{self.player['name']} answered correctly!")
                    self.update_score("player", dollar_value)
                    self.mark_used(board_item["question_id"])
                    return True
                else:
                    print(f"{self.player['name']} got it wrong!")
                    self.update_score("player", -dollar_value)

            else:
                bot_data = next(b for b in bots if b["name"] == name)
                bot = Bot(bot_data["name"], bot_data["difficulty"])
                bot_answer = bot.answer(question["correct_answer"], question["incorrect_answers"])
                print(f"{name}: {bot_answer}")

                if self.check_answer(bot_answer, question):
                    print(f"{name} answered correctly!")
                    self.update_score(name, dollar_value)
                    self.mark_used(board_item["question_id"])
                    return True
                else:
                    print(f"{name} got it wrong!")
                    self.update_score(name, -dollar_value)

        print("No correct answers.")
        print(f"The correct answer was {question['correct_answer']}.")
        self.mark_used(board_item["question_id"])
        return True

    def play_final_jeopardy(self, bots):
        final = db.final_game.find_one({"game_id": self.game_id})

        if not final or final.get("status") == "completed":
            return

        print("\n" + "=" * 40)
        print("       FINAL JEOPARDY")
        print("=" * 40)
        print(f"\nQuestion: {final['question']}")

        wagers, answers, results = {}, {}, {}

        player_score = db.players.find_one({"game_id": self.game_id})["score"]
        max_wager = max(0, player_score)
        print(f"\n{self.player['name']}, your score: ${player_score}")
        raw = input(f"Enter your wager (0–{max_wager}): ").strip()
        player_wager = int(raw) if raw.isdigit() else 0
        player_wager = max(0, min(player_wager, max_wager))
        wagers["player"] = player_wager

        for b in bots:
            bot_score = db.bots.find_one({"game_id": self.game_id, "name": b["name"]})["score"]
            bot_max = max(0, bot_score)
            pct = {"hard": random.uniform(0.7, 1.0), "medium": random.uniform(0.3, 0.7)}.get(
                b["difficulty"], random.uniform(0.0, 0.4)
            )
            wagers[b["name"]] = int(bot_max * pct)

        answers["player"] = input("Your answer: ").strip()

        for b in bots:
            bot = Bot(b["name"], b["difficulty"])
            answers[b["name"]] = bot.answer(final["correct_answer"], final["incorrect_answers"])

        print(f"\nCorrect answer: {final['correct_answer']}")
        print("-" * 40)

        player_correct = self.check_answer(answers["player"], final)
        delta = wagers["player"] if player_correct else -wagers["player"]
        self.update_score("player", delta)
        results["player"] = {"correct": player_correct, "wager": wagers["player"], "delta": delta}
        print(
            f"{self.player['name']}: {answers['player']} — {'CORRECT' if player_correct else 'WRONG'} (${delta:+,})")

        for b in bots:
            bot_correct = self.check_answer(answers[b["name"]], final)
            delta = wagers[b["name"]] if bot_correct else -wagers[b["name"]]
            self.update_score(b["name"], delta)
            results[b["name"]] = {"correct": bot_correct, "wager": wagers[b["name"]], "delta": delta}
            print(f"{b['name']}: {answers[b['name']]} — {'CORRECT' if bot_correct else 'WRONG'} (${delta:+,})")

        db.final_game.update_one(
            {"game_id": self.game_id},
            {"$set": {"status": "completed", "wagers": wagers, "answers": answers, "results": results}}
        )

    def get_buzz_order(self, bots):
        participants = [{"name": "player", "buzz_time": 0.0, "bot": None}]
        for b in bots:
            bot = Bot(b["name"], b["difficulty"])
            participants.append({"name": b["name"], "buzz_time": bot.buzz(), "bot": bot})
        participants.sort(key=lambda x: x["buzz_time"])
        return participants