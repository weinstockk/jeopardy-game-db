# Jeopardy Frontend Planner

---

## Stack Recommendation
- **Framework:** React
- **Styling:** Tailwind CSS
- **Backend communication:** Flask (Keagan) You already have a bit of this system, you are just switching the Input() methods to call the server instead.
- **State management:** React useState / useContext (no Redux needed at this scale) (Keagan) I'm unsure how you initialized the frontend but im assuming its JS React

---

## Screens

### 1. Start Screen
Replaces `game_start.py` input block. (Keagan) This is talking about anything that has Input(), instead of that it should be a call from the flask api you are making. 

**Components:**
- Radio button group or two large buttons: `New Game` / `Load Game`
- **New Game form:**
  - Text input → player name
  - Dropdown (`<select>`) → AI difficulty: Easy / Medium / Hard
  - Submit button → calls `POST /api/game/new`, receives `game_id` and opponent names (Keagan) you dont need the api part and instead do `/game/new` if you want, same for the GET
- **Load Game form:**
  - Text input → paste or type Game ID
  - Submit button → calls `GET /api/game/{game_id}/state`
- Display opponent names returned from the API before proceeding

---

### 2. Game Board Screen
Replaces the `play_round()` category/value inputs. (Keagan) This is talking about anything that has Input(), instead of that it should be a call from the flask api you are making. 

**Components:**
- 5×5 grid of buttons, columns = categories, rows = dollar values (200–1000)
  - Each cell shows the dollar value
  - Used cells are greyed out and disabled (`selected: true` from DB)
  - Category names displayed as column headers above the grid
- Scoreboard sidebar showing current scores for player and both bots, updating after each round
- Round indicator (e.g. `Round 7 / 25`)
- Player clicks a cell → triggers the Question Modal

**API call:** `POST /api/game/{game_id}/select` with `{ category, value }` (Keagan) dont need the api if you dont want it

---

### 3. Question Modal
Replaces the `print(question)` and answer `input()`. (Keagan) This is talking about anything that has Input(), instead of that it should be a call from the flask api you are making.

**Components:**
- Overlay modal, full screen or centered card
- Question text displayed prominently
- **If Daily Double:**
  - "DAILY DOUBLE" banner (animated reveal)
  - Show who buzzed first
  - **If player wins buzz:**
    - Display current score and max wager
    - Number input clamped between 0 and max wager
    - Confirm wager button → reveals question text
    - Text input for answer + Submit button
  - **If bot wins buzz:**
    - Display bot name, wager amount, and bot's answer automatically
    - Show correct/wrong result with score change
- **If normal question:**
  - Text input for player answer + Submit button
  - Bot answers display below in sequence after player submits
- After resolution: show correct answer, score deltas for all participants, Close button returns to board

**API call:** `POST /api/game/{game_id}/answer` with `{ answer, wager? }` (Keagan) dont need the api if you dont want it

---

### 4. Final Jeopardy Screen
Replaces `play_final_jeopardy()` inputs. (Keagan) This is talking about anything that has Input(), instead of that it should be a call from the flask api you are making.

**Components:**
- Full screen takeover with distinct styling (e.g. dark background, gold text)
- "FINAL JEOPARDY" title
- Question text displayed
- Number input for wager (0 to player's current score, enforced by `min`/`max` attributes)
- Confirm wager button → locks it in, reveals answer input
- Text input for answer + Submit button
- Reveal phase:
  - Show correct answer
  - Show each participant's answer, wager, correct/wrong, and score delta in sequence
  - Final scoreboard with all scores
- Proceed to Game Over button

**API call:** `POST /api/game/{game_id}/final` with `{ wager, answer }` (Keagan) dont need the api if you dont want it

---

### 5. Game Over Screen
Replaces `end_game()` print statements.

**Components:**
- Winner name and score displayed prominently
- Full leaderboard: player + both bots, ranked by score
- "Play Again" button → returns to Start Screen
- "View History" button (optional) → reads from `history.json` via `GET /api/history` (Keagan) dont need the api if you dont want it

---

## API Endpoints Needed (Keagan) dont need the api if you dont want it

| Method | Endpoint | Replaces |
|--------|----------|---------|
| POST | `/api/game/new` | `initialize_game()` + `start_game()` new branch |
| GET | `/api/game/{game_id}/state` | `GameEngine.__init__()` load branch |
| GET | `/api/game/{game_id}/board` | `load_board()` |
| POST | `/api/game/{game_id}/select` | `play_round()` category/value inputs |
| POST | `/api/game/{game_id}/answer` | `play_round()` answer input + scoring |
| POST | `/api/game/{game_id}/final` | `play_final_jeopardy()` wager + answer inputs |
| GET | `/api/history` | `history.json` read |

---

## Input Field Summary

| TODO in code | Frontend control |
|---|---|
| New/load choice | Two buttons or a radio group |
| Player name | `<input type="text">` with `.trim().title()` applied client-side |
| AI difficulty | `<select>` with three options |
| Game ID (load) | `<input type="text">` with paste support |
| Category selection | Click on board column header or cell |
| Value selection | Click on board cell |
| DD wager | `<input type="number" min="0" max={maxWager}>` |
| Round answer | `<input type="text">` + Submit button |
| Final wager | `<input type="number" min="0" max={playerScore}>` |
| Final answer | `<input type="text">` + Submit button |

---

---

## Optional: Adding a Real Buzzer for the Player (Keagan) This is to add more intearctivity currently its defaulted to player first but you could make the buzzer if you want (idc if you do or don't at this point)

Currently the player always gets `buzz_time: 0.0` in `get_buzz_order()`, meaning they always go first regardless of reaction speed. Below are two approaches to replace this with a real timed buzz-in.

### How it would work

When a question is revealed, instead of immediately showing the answer input, the frontend starts a timer. The player must click a **Buzz In** button before typing their answer. The time between question reveal and button click becomes their `buzz_time`, which is then compared against the bots' pre-generated buzz times.

### Frontend changes

- Question modal shows the question text but **no answer input yet**
- A large **Buzz In** button is displayed prominently
- A visible countdown timer (e.g. 5 seconds) runs — if it expires without a buzz, the player forfeits their turn for that round
- On buzz, the elapsed time in seconds is sent to the backend
- If the player buzzed before the winning bot's `buzz_time`, they get the answer input
- If a bot's `buzz_time` was faster, the bot answers first and the player only gets a turn if the bot is wrong

### Backend changes

In `get_buzz_order()`, remove the hardcoded `0.0` for the player and accept their actual buzz time from the request:

```python
# In play_round(), receive player_buzz_time from the frontend request
def get_buzz_order(self, bots, player_buzz_time):
    participants = [{"name": "player", "buzz_time": player_buzz_time, "bot": None}]
    for b in bots:
        bot = Bot(b["name"], b["difficulty"])
        participants.append({
            "name": b["name"],
            "buzz_time": bot.buzz(),
            "bot": bot
        })
    participants.sort(key=lambda x: x["buzz_time"])
    return participants
```

The `/api/game/{game_id}/select` endpoint would return the bot buzz times to the frontend so it can reveal who won the buzz after the player clicks in.

### Difficulty considerations

- **Trust:** Buzz times come from the client, so a player could theoretically send `0.0001` every time. If this matters, generate and store bot buzz times server-side at question selection time, then compare against the player's submitted time after the fact.
- **Daily Double:** Buzzing for DD is already fair since the player chose the square — the buzz mechanic is most meaningful for normal rounds only.
- **Feel:** Bot buzz ranges in `Bot.__init__()` are already tuned by difficulty (hard: 0.2–0.8s, medium: 0.7–1.3s, easy: 1.2–2.0s), so a typical human reaction time of ~0.3–0.6s would naturally beat easy bots most of the time and compete with medium, which matches expected game feel.