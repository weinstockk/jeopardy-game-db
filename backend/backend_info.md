# Backend Documentation

## Overview

The backend is a Python FastAPI application that manages all game state through MongoDB. It exposes a REST API consumed by the React frontend. Game logic lives in `game_engine.py`; database initialization (fetching questions, building the board) lives in `db_init.py`.

---

## Environment Variables

| Variable    | Description                        |
|-------------|------------------------------------|
| `MONGO_URI` | MongoDB connection string          |
| `DB_NAME`   | Name of the MongoDB database to use |

---

## Running the Server

```bash
uvicorn app:app --reload
```

Runs on `http://localhost:8000` by default.

---

## API Endpoints

### Game Lifecycle

| Method | Route | Description |
|--------|-------|-------------|
| `POST` | `/api/new-game` | Create a new game. Returns `game_id`, player name, and AI names |
| `GET`  | `/api/game/{game_id}` | Get full game state (board, scores, round) |
| `GET`  | `/api/active-games` | List all in-progress games |
| `GET`  | `/api/history` | List completed games from `history.json` (newest first) |
| `POST` | `/api/end-game/{game_id}` | Finalize game, archive to history, clean up MongoDB |

### Questions

| Method | Route | Description |
|--------|-------|-------------|
| `POST` | `/api/question/{game_id}` | Fetch a question payload for a given category + value |
| `POST` | `/api/answer/{game_id}` | Submit answer with player buzz time and bot buzz times |
| `POST` | `/api/player-answer/{game_id}` | Submit player's second-chance answer after all bots miss |
| `POST` | `/api/daily-double/{game_id}` | Submit wager and answer for a Daily Double |

### Final Jeopardy

| Method | Route | Description |
|--------|-------|-------------|
| `GET`  | `/api/final/{game_id}` | Get Final Jeopardy question and player score |
| `POST` | `/api/final/{game_id}` | Submit wager and answer; returns full reveal for all players |

---

## Request / Response Shapes

### `POST /api/new-game`
```json
// Request
{ "player_name": "Alice", "ai_difficulty": "medium" }

// Response
{ "game_id": "uuid", "player": "Alice", "ai_1": "Marcus", "ai_2": "Elena" }
```

### `POST /api/question/{game_id}`
```json
// Request
{ "category": "Science", "value": 400 }

// Response
{
  "question": "...",
  "answers": ["A", "B", "C", "D"],
  "correct_answer": "B",
  "value": 400,
  "category": "Science",
  "is_daily_double": false,
  "bot_buzz_times": { "Marcus": 1.23, "Elena": 3.87 }
}
```

### `POST /api/answer/{game_id}`
```json
// Request
{
  "category": "Science",
  "value": 400,
  "answer": "B",
  "player_buzz_time": 0.94,
  "bot_buzz_times": { "Marcus": 1.23, "Elena": 3.87 }
}

// Response
{
  "player_buzzed_first": true,
  "player_correct": true,
  "correct_answer": "B",
  "results": [...],
  "all_buzz_times": [...],
  "round_winner": "player",
  "remaining": 21,
  "game_over": false
}
```

### `POST /api/daily-double/{game_id}`
```json
// Request
{ "category": "History", "value": 800, "wager": 500, "answer": "C" }

// Response
{
  "player_correct": false,
  "correct_answer": "D",
  "wager": 500,
  "delta": -500,
  "remaining": 20,
  "game_over": false
}
```

### `POST /api/final/{game_id}`
```json
// Request
{ "wager": 1200, "answer": "A" }

// Response
{
  "correct_answer": "A",
  "reveal": [
    { "name": "Alice", "is_player": true, "correct": true, "wager": 1200, "delta": 1200, "answer": "A" },
    { "name": "Marcus", "is_player": false, "correct": false, "wager": 800, "delta": -800, "answer": "C" }
  ]
}
```

---

## Game Engine (`game_engine.py`)

The `GameEngine` class is instantiated per-request using a `game_id`. It reads from MongoDB on init and writes back after each action.

### Key Methods

| Method | Description |
|--------|-------------|
| `GameEngine.create()` | Static factory. Calls `db_init`, stores player/bot docs, returns identifiers |
| `get_state()` | Returns board, scores, round, remaining count |
| `get_question_payload()` | Fetches question + shuffled answers + bot buzz times |
| `submit_answer()` | Resolves buzz order, scores all participants, marks question used |
| `submit_player_answer()` | Second-chance scoring after all bots miss |
| `submit_daily_double()` | Applies wager-based scoring for Daily Doubles |
| `get_final_payload()` | Returns Final Jeopardy question and current player score |
| `submit_final()` | Scores all players simultaneously for Final Jeopardy |
| `end_game()` | Computes winner, writes `history.json`, deletes all game collections |

### Buzz Resolution Logic

1. Bot buzz times are pre-generated when the question payload is created (`_generate_buzz_times`)
2. The frontend timer runs for 5 seconds; the player's buzz time is measured client-side
3. `submit_answer` receives both the player's buzz time and the pre-generated bot times
4. Participants are sorted by buzz time; the first correct answer wins the value
5. If `player_buzz_time = 999`, the player is treated as not having buzzed in

---

## Database Initialization (`db_init.py`)

Called once per new game. Performs the following in order:

1. Fetches 5 random categories from OpenTDB
2. For each category, fetches one question per value tier (200–1000), mapped to difficulty:
   - 200/400 → `easy`, 600/800 → `medium`, 1000 → `hard`
3. Inserts all questions and board cells into MongoDB
4. Creates player and bot documents (2 bots, same difficulty)
5. Creates the game state document
6. Fetches one additional `hard` question for Final Jeopardy
7. Randomly assigns 2 Daily Doubles across the board

Questions are fetched with retry logic (up to 8 attempts, with back-off) to handle OpenTDB rate limits.

---

## Bot Model (`models/bot.py`)

Each bot has a difficulty level that controls two behaviors:

- **`buzz()`** — returns a randomized buzz time. Hard bots buzz faster on average than medium or easy bots
- **`answer()`** — returns the correct answer or a random incorrect one, weighted by difficulty:
  - Hard: high probability of answering correctly
  - Medium: moderate probability
  - Easy: low probability

For Final Jeopardy, bots also wager a percentage of their score based on difficulty (hard wagers 70–100%, medium 30–70%, easy 0–40%).

---

## Data Persistence

### Active Game Collections

| Collection   | Key Fields |
|--------------|------------|
| `games`      | `game_id`, `status`, `round`, `turn`, `created_at` |
| `players`    | `game_id`, `name`, `score` |
| `bots`       | `game_id`, `name`, `difficulty`, `score` |
| `board`      | `game_id`, `category_name`, `value`, `question_id`, `selected`, `is_daily_double` |
| `questions`  | `game_id`, `question`, `correct_answer`, `incorrect_answers`, `difficulty`, `value` |
| `categories` | `game_id`, `name`, `otdb_id` |
| `final_game` | `game_id`, `question`, `correct_answer`, `status`, `wagers`, `answers`, `results` |

### Completed Games (`history.json`)

Each entry contains a snapshot: player name/score, bot names/scores, winner, total questions, and a Unix timestamp. Entries are prepended so the most recent game appears first.