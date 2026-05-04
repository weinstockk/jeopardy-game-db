# Frontend Documentation

## Overview

The frontend is a React 19 + TypeScript single-page application built with Vite. There is no client-side router — screen transitions are managed through a single `AppState` object lifted into `App.tsx`. All API calls are centralized in `api.ts`.

---

## Running the Dev Server

```bash
npm install
npm run dev
```

Runs on `http://localhost:5173`. The backend is expected at `http://localhost:8000` (configured in `src/api.ts`).

---

## File Structure

```
src/
├── App.tsx                  # Root component, screen router, shared state
├── App.css                  # All global styles and CSS variables
├── main.tsx                 # Vite entry point
├── index.css                # Box-sizing reset
├── api.ts                   # All API calls, fully typed
├── components/
│   ├── LoadingOverlay.tsx   # Full-screen spinner
│   ├── QuestionModal.tsx    # Buzz → answer → result flow
│   └── DailyDoubleModal.tsx # Wager → answer → result flow
└── screens/
    ├── SetupScreen.tsx      # Home / load game / history
    ├── GameScreen.tsx       # Board + scoreboard
    ├── FinalScreen.tsx      # Final Jeopardy (wager → answer → reveal)
    └── GameOverScreen.tsx   # Winner display and final scores
```

---

## State Management

There is no external state library. All shared state lives in `AppState` inside `App.tsx` and is passed down as props.

```ts
interface AppState {
  screen: 'setup' | 'game' | 'final' | 'gameover'
  gameId: string | null
  gameState: GameState | null
  loading: boolean
  loadingMsg: string
}
```

`GameState` mirrors the `/api/game/{game_id}` response shape:

```ts
interface GameState {
  game_id: string
  round: number
  player: { name: string; score: number }
  bots: { name: string; score: number; difficulty: string }[]
  board: Record<string, Record<number, { selected: boolean; is_daily_double: boolean }>>
  remaining: number
}
```

Screens navigate by calling `navigate(screen, extraState?)` which merges into `AppState` via `setAppState`.

---

## API Layer (`api.ts`)

All fetch calls are wrapped in a typed `req<T>()` helper that handles `Content-Type`, error parsing, and throws on non-2xx responses. The base URL defaults to `http://localhost:8000`.

Each method is documented inline in `api.ts`. Key methods:

| Method | Description |
|--------|-------------|
| `api.newGame()` | POST new game, returns game_id and AI names |
| `api.getGame()` | GET full game state |
| `api.activeGames()` | GET list of resumable games |
| `api.history()` | GET completed game history |
| `api.getQuestion()` | POST to fetch a question payload |
| `api.submitAnswer()` | POST answer with buzz times |
| `api.submitPlayerAnswer()` | POST second-chance answer |
| `api.dailyDouble()` | POST wager + answer for Daily Double |
| `api.getFinal()` | GET Final Jeopardy question |
| `api.submitFinal()` | POST Final Jeopardy wager + answer |
| `api.endGame()` | POST to finalize and archive game |

---

## Screen Breakdown

### `SetupScreen`

Manages three sub-views via a local `view` state (`'home' | 'load' | 'history'`) — no separate routes or components. Transitions between them with a back button rather than separate pages.

- **Home** — name input, difficulty picker, three action buttons
- **Load** — fetches `/api/active-games` and lists resumable sessions
- **History** — fetches `/api/history` and displays completed game results

### `GameScreen`

Renders the scoreboard and 5×5 board. Clicking an unselected cell calls `api.getQuestion()` and opens either `QuestionModal` (normal) or `DailyDoubleModal` (daily double) based on `is_daily_double` in the response. After the modal closes, the board refreshes via `api.getGame()`.

### `FinalScreen`

Three sequential phases managed by a local `phase` state:

1. **Wager** — player enters a wager (capped at `max(0, score)` to handle negative balances)
2. **Answer** — question revealed, player picks from 4 shuffled answers, submits when ready
3. **Reveal** — all participants' answers, wagers, and score deltas shown in a table

After reveal, "See Final Scores" calls `api.endGame()` and navigates to `GameOverScreen`, passing winner and score data through `AppState`.

### `GameOverScreen`

Reads `_winner` and `_allScores` injected into `gameState` by `FinalScreen` before navigation. Displays the winner and a sorted score table. "Play Again" resets `AppState` to initial values.

---

## Component Breakdown

### `QuestionModal`

Manages a four-phase state machine: `'buzz' | 'answer' | 'second-chance' | 'result'`.

**Buzz phase**
- A 5-second countdown bar and timer run via `setInterval` (ref-stored and always cleared)
- Player clicks BUZZ IN; elapsed time is compared against pre-generated bot buzz times from the payload
- If a bot buzzed faster, `submitBots()` is called with `player_buzz_time: 999`
- If the player was faster, they move to the answer phase

**Answer phase**
- Four answer buttons enabled; selecting one immediately locks the grid and calls `api.submitAnswer()`

**Second-chance phase**
- Only reached when all bots answered incorrectly and the player was present during the buzz window
- Calls `api.submitPlayerAnswer()` (a separate endpoint that scores only the player)
- Bot results from the earlier `submitBots()` call are merged with the player result before showing the result phase

**Result phase**
- Answer buttons reveal correct/wrong state via CSS classes
- Buzz times and answer results shown in a results list
- "Continue" button reloads game state or navigates to Final Jeopardy

### `DailyDoubleModal`

Three-phase flow: `'wager' | 'answer' | 'result'`. Wager is capped at `max(200, playerScore)`. Calls `api.dailyDouble()` on answer submission.

### `LoadingOverlay`

Fixed full-screen overlay with a spinning border animation and a message string. Shown/hidden by `AppState.loading`.

---

## Styling

All styles are in `App.css` using CSS custom properties:

| Variable      | Value     | Usage |
|---------------|-----------|-------|
| `--blue`      | `#060CE9` | Board cells, card backgrounds |
| `--gold`      | `#FFD700` | Primary accent, scores, logo |
| `--gold-dark` | `#e6c200` | Button hover state |
| `--green`     | `#00c851` | Correct answer feedback |
| `--red`       | `#ff3547` | Wrong answer feedback |
| `--gray`      | `#888`    | Secondary labels |
| `--bg`        | `#020318` | Page background |

Fonts are loaded from Google Fonts:
- **Bebas Neue** — headings, logo, scores, buttons
- **Barlow** — body text, answer buttons, inputs

There is no component library or CSS framework. All layout uses CSS Grid and Flexbox. The board grid is `grid-template-columns: repeat(5, 1fr)` with headers and value cells rendered in a single flat grid (headers first, then rows by value).

Responsive breakpoints apply at `640px`: single-column answer grid, smaller board cells and fonts, condensed scoreboard.