# Jeopardy Game

A full-stack Jeopardy-style trivia game built with a Python/FastAPI backend, React/TypeScript frontend, and MongoDB for game state persistence. Features real-time buzzer mechanics, AI opponents, Daily Doubles, and Final Jeopardy.

## Tech Stack

**Backend**
- Python 3
- FastAPI + Uvicorn
- MongoDB + PyMongo
- Open Trivia Database API (https://opentdb.com/)
- python-dotenv

**Frontend**
- React 19 + TypeScript
- Vite
- CSS (no component library)

## Project Structure

```
jeopardy-game-db/
├── .env
├── .gitignore
├── complex_queries.py
├── README.md
├── requirements.txt
├── backend/
│   ├── backend_info.md      # Information
│   ├── app.py               # FastAPI routes
│   ├── game_engine.py       # Core game logic
│   ├── game_start.py        # Console game start
│   ├── db_init.py           # MongoDB initialization
│   ├── models/
│   │   └── bot.py           # Bot AI model
│   ├── name_setup/
│   │   └── ai_name_utils.py # AI name generation
│   └── data/
│       └── history.json     # Completed game archive
└── frontend/
    ├── index.html
    ├── vite.config.ts
    ├── frontend_info.md
    └── src/
        ├── App.tsx
        ├── App.css
        ├── api.ts
        ├── components/
        │   ├── LoadingOverlay.tsx
        │   ├── QuestionModal.tsx
        │   └── DailyDoubleModal.tsx
        └── screens/
            ├── SetupScreen.tsx
            ├── GameScreen.tsx
            ├── FinalScreen.tsx
            └── GameOverScreen.tsx
```

## Setup

### Backend
1. Clone the repo
   ```bash
   git clone https://github.com/weinstockk/jeopardy-game-db.git
   cd jeopardy-game-db/backend
   ```
2. Install dependencies
   ```bash
   pip install -r requirements.txt
   ```
3. Configure environment
   ```bash
   cp .env.example .env
   ```
   Then fill in your MongoDB connection string and database name in `.env`:
   ```
   MONGO_URI=mongodb://...
   DB_NAME=jeopardy
   ```
4. Navigate to the backend directory
   ```bash
   cd ../backend
   ```
5. Start the server
   ```bash
   uvicorn app:app --reload
   ```
   The API will be available at `http://localhost:8000`.

### Frontend
1. Navigate to the frontend directory
   ```bash
   cd ../frontend
   ```
2. Install dependencies
   ```bash
   npm install
   ```
3. Start the dev server
   ```bash
   npm run dev
   ```
   The app will be available at `http://localhost:5173`.

## Gameplay

1. Enter your name and select AI difficulty (Easy / Medium / Hard)
2. Pick a category and dollar value from the 5×5 board
3. Hit **BUZZ IN** before the 5-second window closes to answer
4. If a bot buzzes faster, they answer first — if they miss, you get a second chance
5. Daily Doubles let you wager before seeing the question
6. After all 25 questions, Final Jeopardy lets every player wager and answer simultaneously
7. Highest score wins

## Data Persistence

Active games are stored across six MongoDB collections:

| Collection   | Contents                              |
|--------------|---------------------------------------|
| `games`      | Game status, round, turn              |
| `players`    | Player name and score                 |
| `bots`       | Bot names, difficulty, and score      |
| `board`      | 5×5 grid cells, values, daily doubles |
| `questions`  | Question text, answers, difficulty    |
| `categories` | Category names and OpenTDB IDs        |

When a game ends, all six collections are cleaned up and a snapshot is appended to `history.json`.

## Collaborators

- **Keagan Weinstock** — [weinstockk@msoe.edu](mailto:weinstockk@msoe.edu)
- **Jaden Griffith** — [griffithjr@msoe.edu](mailto:griffithjr@msoe.edu)