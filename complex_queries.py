# Name: Keagan Weinstock
# File: complex_queries.py
# Description: Six complex MongoDB queries for the Jeopardy NoSQL project.
#              These queries demonstrate aggregation, joins ($lookup),
#              and analytical insights using the ACTUAL project schema.
#              NOTE: This version does NOT rely on a game_history collection.

import os
from pymongo import MongoClient
from dotenv import load_dotenv
from pprint import pprint

load_dotenv()

client = MongoClient(os.getenv("MONGO_URI"))
db = client[os.getenv("DB_NAME")]


# ─────────────────────────────────────────────────────────────────────────────
# QUERY 1: Player Leaderboard Across All Games
# Equivalent SQL: SELECT name, SUM(score), COUNT(*)
#                 FROM players GROUP BY name ORDER BY SUM(score) DESC LIMIT 5
# ─────────────────────────────────────────────────────────────────────────────
def query_1_player_leaderboard():
    """
    Aggregates the players collection to compute total score and number of
    games played per player. Produces a top-5 leaderboard.

    Demonstrates:
    - $group (aggregation)
    - computed averages
    - sorting and limiting
    """
    print("\n═══ QUERY 1: Player Leaderboard ═══")

    pipeline = [
        {"$group": {
            "_id": "$name",
            "total_score": {"$sum": "$score"},
            "games_played": {"$sum": 1}
        }},
        {"$sort": {"total_score": -1}},
        {"$limit": 5},
        {"$project": {
            "_id": 0,
            "player": "$_id",
            "total_score": 1,
            "games_played": 1,
            "avg_score": {
                "$round": [
                    {"$divide": ["$total_score", "$games_played"]}, 1
                ]
            }
        }}
    ]

    results = list(db.players.aggregate(pipeline))
    pprint(results)
    return results


# ─────────────────────────────────────────────────────────────────────────────
# QUERY 2: Question Difficulty Distribution
# Equivalent SQL: SELECT difficulty, COUNT(*), AVG(value)
#                 FROM questions GROUP BY difficulty
# ─────────────────────────────────────────────────────────────────────────────
def query_2_difficulty_distribution():
    """
    Analyzes how questions are distributed across difficulty levels and
    calculates the average point value for each difficulty.

    Demonstrates:
    - grouping categorical data
    - statistical aggregation (count + average)
    """
    print("\n═══ QUERY 2: Question Difficulty Distribution ═══")

    pipeline = [
        {"$group": {
            "_id": "$difficulty",
            "count": {"$sum": 1},
            "avg_value": {"$avg": "$value"}
        }},
        {"$sort": {"count": -1}},
        {"$project": {
            "_id": 0,
            "difficulty": "$_id",
            "count": 1,
            "avg_value": {"$round": ["$avg_value", 0]}
        }}
    ]

    results = list(db.questions.aggregate(pipeline))
    pprint(results)
    return results


# ─────────────────────────────────────────────────────────────────────────────
# QUERY 3: Bot Performance by Difficulty
# Equivalent SQL: SELECT difficulty, AVG(score), MAX(score), COUNT(*)
#                 FROM bots GROUP BY difficulty
# ─────────────────────────────────────────────────────────────────────────────
def query_3_bot_performance():
    """
    Evaluates how bots perform depending on their difficulty setting.
    Calculates average and maximum scores across all games.

    Demonstrates:
    - aggregation over AI agents
    - performance comparison across categories
    """
    print("\n═══ QUERY 3: Bot Performance ═══")

    pipeline = [
        {"$group": {
            "_id": "$difficulty",
            "avg_score": {"$avg": "$score"},
            "max_score": {"$max": "$score"},
            "games": {"$sum": 1}
        }},
        {"$sort": {"avg_score": -1}},
        {"$project": {
            "_id": 0,
            "difficulty": "$_id",
            "avg_score": {"$round": ["$avg_score", 0]},
            "max_score": 1,
            "games": 1
        }}
    ]

    results = list(db.bots.aggregate(pipeline))
    pprint(results)
    return results


# ─────────────────────────────────────────────────────────────────────────────
# QUERY 4: Category Value Contribution
# Equivalent SQL: SELECT category_name, COUNT(*), SUM(value)
#                 FROM categories JOIN questions
#                 ON categories._id = questions.category_id
#                 GROUP BY category_name ORDER BY SUM(value) DESC
# ─────────────────────────────────────────────────────────────────────────────
def query_4_category_value():
    """
    Joins categories with questions to determine which categories contribute
    the most total point value across all games.

    Demonstrates:
    - $lookup (MongoDB JOIN)
    - array aggregation
    - derived metrics from joined collections
    """
    print("\n═══ QUERY 4: Category Value Contribution ═══")

    pipeline = [
        {"$lookup": {
            "from": "questions",
            "localField": "_id",
            "foreignField": "category_id",
            "as": "questions"
        }},
        {"$project": {
            "name": 1,
            "question_count": {"$size": "$questions"},
            "total_value": {"$sum": "$questions.value"}
        }},
        {"$sort": {"total_value": -1}},
        {"$limit": 10}
    ]

    results = list(db.categories.aggregate(pipeline))
    pprint(results)
    return results


# ─────────────────────────────────────────────────────────────────────────────
# QUERY 5: Board Utilization Rate per Game
# Equivalent SQL: SELECT game_id,
#                 SUM(selected)/COUNT(*) * 100 AS utilization
#                 FROM board GROUP BY game_id
# ─────────────────────────────────────────────────────────────────────────────
def query_5_board_utilization():
    """
    Measures how much of the game board was actually used in each game.
    Useful for identifying incomplete or abandoned games.

    Demonstrates:
    - conditional aggregation ($cond)
    - ratio calculation
    """
    print("\n═══ QUERY 5: Board Utilization Rate ═══")

    pipeline = [
        {"$group": {
            "_id": "$game_id",
            "total_cells": {"$sum": 1},
            "answered_cells": {
                "$sum": {"$cond": ["$selected", 1, 0]}
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
            "utilization_pct": 1
        }}
    ]

    results = list(db.board.aggregate(pipeline))
    pprint(results)
    return results


# ─────────────────────────────────────────────────────────────────────────────
# QUERY 6: Final Jeopardy Wager Analysis
# Equivalent SQL: SELECT AVG(wager), MAX(wager), SUM(wager)
#                 FROM final_game (after unnesting wagers map)
# ─────────────────────────────────────────────────────────────────────────────
def query_6_final_jeopardy_wagers():
    """
    Analyzes wagering behavior in Final Jeopardy by converting the dynamic
    wagers object into an array and aggregating values.

    Demonstrates:
    - $objectToArray (handling dynamic keys)
    - $unwind
    - aggregation over nested data
    """
    print("\n═══ QUERY 6: Final Jeopardy Wager Analysis ═══")

    pipeline = [
        {"$project": {
            "wagers_array": {"$objectToArray": "$wagers"}
        }},
        {"$unwind": "$wagers_array"},
        {"$group": {
            "_id": None,
            "avg_wager": {"$avg": "$wagers_array.v"},
            "max_wager": {"$max": "$wagers_array.v"},
            "total_wager": {"$sum": "$wagers_array.v"}
        }},
        {"$project": {
            "_id": 0,
            "avg_wager": {"$round": ["$avg_wager", 0]},
            "max_wager": 1,
            "total_wager": 1
        }}
    ]

    results = list(db.final_game.aggregate(pipeline))
    pprint(results)
    return results


# ─────────────────────────────────────────────────────────────────────────────
# RUN ALL QUERIES
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("Running all complex queries...\n")

    query_1_player_leaderboard()
    query_2_difficulty_distribution()
    query_3_bot_performance()
    query_4_category_value()
    query_5_board_utilization()
    query_6_final_jeopardy_wagers()

    print("\nAll queries complete.")