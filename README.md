# Jeopardy Game (MongoDB + Python)
A Jeopardy-style quiz game built with Python and MongoDB, featuring dynamic question generation, AI opponents, and a persistent NoSQL-backed game engine.

## Tech Stack

- Python 3
- MongoDB
- PyMongo
- Open Trivia Database API (https://opentdb.com/)
- dotenv for environment configuration

## Setup
1. Clone the repo
   * `git clone https://github.com/weinstockk/jeopardy-game-db.git`
   * `cd jeopardy-game-db`
2. Install dependencies: `pip install -r requirements.txt`
3. Create a .env file: `cp .env.example .env`
4. Add the correct MongoDB connection string 
5. Run the game start script `python game_start.py`

## Usage
1. Start a new game or load an existing one using a game_id
2. Select categories and values to answer questions
3. Compete against AI opponents with varying difficulty
4. Scores update in real time
5. Completed games are saved to `history.json`

## Data Persistence
* Active games are stored in MongoDB collections:
  * games, players, bots, board, questions, categories
* Completed games are:
  * Removed from MongoDB 
  * Archived locally in `history.json`

## Collaborators
* Keagan Weinstock: [weinstockk@msoe.edu](mailto::weinstockk@msoe.edu)
* Jaden Griffith: [griffithjr@msoe.edu](mailto::griffithjr@msoe.edu)
