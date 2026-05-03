# Name: Keagan Weinstock
# File: complex_queries.py
# Description: Six complex MongoDB queries for the Jeopardy NoSQL project.
#              Each query demonstrates aggregation, multi-collection logic,
#              or analytical insight that would require JOINs/GROUP BY in SQL.

import os
from pymongo import MongoClient
from dotenv import load_dotenv
from pprint import pprint

load_dotenv()

client = MongoClient(os.getenv("MONGO_URI"))
db = client[os.getenv("DB_NAME")]


# ─────────────────────────────────────────────────────────────────────────────
# QUERY 1: Leaderboard — Top 5 Players Across All Game History
# Equivalent SQL: SELECT name, SUM(score) AS total, COUNT(*) AS games_played
#                 FROM history GROUP BY name ORDER BY total DESC LIMIT 5
# ─────────────────────────────────────────────────────────────────────────────
def query_1_leaderboard():
    """
    Aggregates the game_history collection to produce a leaderboard of the
    top 5 human players by cumulative score across all completed games.
    Mirrors a GROUP BY + ORDER BY + LIMIT pattern from relational SQL.
    """
    print("\n═══ QUERY 1: Top 5 Players (All-Time Leaderboard) ═══")
    pipeline = [
        {"$unwind": "$players"},
        {"$match": {"players.type": "human"}},
        {"$group": {
            "_id": "$players.name",
            "total_score": {"$sum": "$players.final_score"},
            "games_played": {"$sum": 1},
            "wins": {"$sum": {"$cond": [{"$eq": ["$winner", "$players.name"]}, 1, 0]}}
        }},
        {"$sort": {"total_score": -1}},
        {"$limit": 5},
        {"$project": {
            "_id": 0,
            "player": "$_id",
            "total_score": 1,
            "games_played": 1,
            "wins": 1,
            "avg_score": {"$divide": ["$total_score", "$games_played"]}
        }}
    ]
    results = list(db.game_history.aggregate(pipeline))
    pprint(results)
    return results


# ─────────────────────────────────────────────────────────────────────────────
# QUERY 2: Category Difficulty Analysis — Average Score Delta Per Difficulty
# Equivalent SQL: SELECT difficulty, AVG(score_delta) FROM questions
#                 JOIN board ON ... GROUP BY difficulty
# ─────────────────────────────────────────────────────────────────────────────
def query_2_difficulty_analysis():
    """
    Joins the questions collection with the board collection (via $lookup) to
    compute the average value of correctly vs incorrectly answered questions
    per difficulty tier. Reveals which difficulty levels are most valuable.
    """
    print("\n═══ QUERY 2: Score Delta by Difficulty Level ═══")
    pipeline = [
        {"$lookup": {
            "from": "board",
            "localField": "_id",
            "foreignField": "question_id",
            "as": "board_info"
        }},
        {"$unwind": "$board_info"},
        {"$group": {
            "_id": "$difficulty",
            "avg_value": {"$avg": "$value"},
            "total_questions": {"$sum": 1},
            "daily_doubles": {"$sum": {"$cond": ["$board_info.is_daily_double", 1, 0]}}
        }},
        {"$sort": {"avg_value": 1}},
        {"$project": {
            "_id": 0,
            "difficulty": "$_id",
            "avg_value": {"$round": ["$avg_value", 2]},
            "total_questions": 1,
            "daily_doubles": 1
        }}
    ]
    results = list(db.questions.aggregate(pipeline))
    pprint(results)
    return results


# ─────────────────────────────────────────────────────────────────────────────
# QUERY 3: Bot Performance — Win Rate and Avg Score by AI Difficulty Setting
# Equivalent SQL: SELECT difficulty, COUNT(*) AS games,
#                 AVG(score) AS avg_score FROM bots GROUP BY difficulty
# ─────────────────────────────────────────────────────────────────────────────
def query_3_bot_performance():
    """
    Aggregates the game_history collection, drilling into the bots sub-array
    to compute per-difficulty win rates and average scores. Shows whether
    hard bots actually win more than easy bots across all stored game records.
    """
    print("\n═══ QUERY 3: Bot Performance by Difficulty Setting ═══")
    pipeline = [
        {"$unwind": "$bots"},
        {"$group": {
            "_id": "$bots.difficulty",
            "total_games": {"$sum": 1},
            "avg_score": {"$avg": "$bots.final_score"},
            "total_wins": {"$sum": {
                "$cond": [{"$eq": ["$winner", "$bots.name"]}, 1, 0]
            }}
        }},
        {"$addFields": {
            "win_rate_pct": {
                "$round": [
                    {"$multiply": [
                        {"$divide": ["$total_wins", "$total_games"]},
                        100
                    ]},
                    1
                ]
            }
        }},
        {"$sort": {"win_rate_pct": -1}},
        {"$project": {
            "_id": 0,
            "bot_difficulty": "$_id",
            "total_games": 1,
            "avg_score": {"$round": ["$avg_score", 0]},
            "win_rate_pct": 1
        }}
    ]
    results = list(db.game_history.aggregate(pipeline))
    pprint(results)
    return results


# ─────────────────────────────────────────────────────────────────────────────
# QUERY 4: Category Popularity — Which Categories Appeared Most and Were Worth Most
# Equivalent SQL: SELECT category_name, COUNT(*) AS appearances,
#                 SUM(value) AS total_value FROM categories
#                 JOIN questions ON ... GROUP BY category_name ORDER BY appearances DESC
# ─────────────────────────────────────────────────────────────────────────────
def query_4_category_popularity():
    """
    Looks up category documents joined with their questions to compute how
    often each category name has appeared across games, and total board value
    it contributed. Surfaces the most and least common trivia categories.
    """
    print("\n═══ QUERY 4: Category Popularity & Total Board Value ═══")
    pipeline = [
        {"$lookup": {
            "from": "questions",
            "localField": "_id",
            "foreignField": "category_id",
            "as": "questions"
        }},
        {"$project": {
            "name": 1,
            "game_id": 1,
            "question_count": {"$size": "$questions"},
            "total_value": {"$sum": "$questions.value"}
        }},
        {"$group": {
            "_id": "$name",
            "appearances": {"$sum": 1},
            "total_board_value": {"$sum": "$total_value"},
            "avg_board_value": {"$avg": "$total_value"}
        }},
        {"$sort": {"appearances": -1}},
        {"$limit": 10},
        {"$project": {
            "_id": 0,
            "category": "$_id",
            "appearances": 1,
            "total_board_value": 1,
            "avg_board_value": {"$round": ["$avg_board_value", 0]}
        }}
    ]
    results = list(db.categories.aggregate(pipeline))
    pprint(results)
    return results


# ─────────────────────────────────────────────────────────────────────────────
# QUERY 5: Final Jeopardy Analysis — Correct Answer Rate and Avg Wager
# Equivalent SQL: SELECT answered_correctly, COUNT(*) AS count,
#                 AVG(wager) AS avg_wager FROM final_game GROUP BY answered_correctly
# ─────────────────────────────────────────────────────────────────────────────
def query_5_final_jeopardy_analysis():
    """
    Unpacks the nested wagers and results maps in the final_game collection
    to compute correct-answer rate and average wager for both human players
    and bots in Final Jeopardy. Demonstrates $objectToArray on dynamic keys.
    """
    print("\n═══ QUERY 5: Final Jeopardy Correct Rate & Average Wager ═══")
    pipeline = [
        {"$match": {"status": "completed"}},
        {"$project": {
            "results_array": {"$objectToArray": "$results"},
            "wagers_array": {"$objectToArray": "$wagers"}
        }},
        {"$unwind": "$results_array"},
        {"$unwind": "$wagers_array"},
        {"$match": {"$expr": {"$eq": ["$results_array.k", "$wagers_array.k"]}}},
        {"$group": {
            "_id": "$results_array.v.correct",
            "count": {"$sum": 1},
            "avg_wager": {"$avg": "$wagers_array.v"},
            "total_wager": {"$sum": "$wagers_array.v"}
        }},
        {"$project": {
            "_id": 0,
            "answered_correctly": "$_id",
            "count": 1,
            "avg_wager": {"$round": ["$avg_wager", 0]},
            "total_wager": 1
        }}
    ]
    results = list(db.final_game.aggregate(pipeline))
    pprint(results)
    return results


# ─────────────────────────────────────────────────────────────────────────────
# QUERY 6: Game Duration Proxy — Board Utilization Rate Per Game
# Equivalent SQL: SELECT game_id,
#                 SUM(CASE WHEN selected=1 THEN 1 ELSE 0 END) / COUNT(*) AS utilization
#                 FROM board GROUP BY game_id
# ─────────────────────────────────────────────────────────────────────────────
def query_6_board_utilization():
    """
    Computes the board utilization rate for each game — the proportion of
    the 25 board cells that were actually answered before the game ended.
    Games that ended early (e.g., load-and-abandon) will show < 100%.
    Demonstrates conditional counting and ratio calculation in aggregation.
    """
    print("\n═══ QUERY 6: Board Utilization Rate Per Game ═══")
    pipeline = [
        {"$group": {
            "_id": "$game_id",
            "total_cells": {"$sum": 1},
            "answered_cells": {"$sum": {"$cond": ["$selected", 1, 0]}},
            "daily_doubles_hit": {
                "$sum": {
                    "$cond": [
                        {"$and": ["$is_daily_double", "$selected"]},
                        1, 0
                    ]
                }
            }
        }},
        {"$addFields": {
            "utilization_pct": {
                "$round": [
                    {"$multiply": [
                        {"$divide": ["$answered_cells", "$total_cells"]},
                        100
                    ]},
                    1
                ]
            }
        }},
        {"$sort": {"utilization_pct": -1}},
        {"$project": {
            "_id": 0,
            "game_id": "$_id",
            "total_cells": 1,
            "answered_cells": 1,
            "daily_doubles_hit": 1,
            "utilization_pct": 1
        }}
    ]
    results = list(db.board.aggregate(pipeline))
    pprint(results)
    return results


# ─────────────────────────────────────────────────────────────────────────────
# RUN ALL QUERIES
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("Running all complex queries against Jeopardy database...\n")
    query_1_leaderboard()
    query_2_difficulty_analysis()
    query_3_bot_performance()
    query_4_category_popularity()
    query_5_final_jeopardy_analysis()
    query_6_board_utilization()
    print("\nAll queries complete.")