// =============================================
//  JEOPARDY - Frontend JS
// =============================================

let gameId = null;
let gameState = null;
let selectedDifficulty = "easy";
let currentQuestion = null;

// =============================================
//  SCREEN SWITCHING
// =============================================
function showScreen(id) {
  document.querySelectorAll(".screen").forEach(s => s.classList.remove("active"));
  document.getElementById(id).classList.add("active");
}

// =============================================
//  SETUP SCREEN
// =============================================
document.querySelectorAll(".diff-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".diff-btn").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    selectedDifficulty = btn.dataset.diff;
  });
});

document.getElementById("start-btn").addEventListener("click", async () => {
  const name = document.getElementById("player-name").value.trim();
  const errEl = document.getElementById("setup-error");

  if (!name) {
    errEl.textContent = "Please enter your name.";
    return;
  }

  errEl.textContent = "";
  showLoading("Fetching categories...");

  try {
    const res = await fetch("/api/new-game", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ player_name: name, ai_difficulty: selectedDifficulty })
    });

    const data = await res.json();

    if (data.error) {
      hideLoading();
      errEl.textContent = data.error;
      return;
    }

    gameId = data.game_id;
    hideLoading();
    await loadGame();
    showScreen("game-screen");

  } catch (e) {
    hideLoading();
    errEl.textContent = "Connection error. Is the server running?";
  }
});

function showLoading(msg = "Loading...") {
  const overlay = document.getElementById("loading-overlay");
  document.getElementById("loading-text").textContent = msg;
  overlay.classList.remove("hidden");
}

function hideLoading() {
  document.getElementById("loading-overlay").classList.add("hidden");
}

// =============================================
//  LOAD / REFRESH GAME STATE
// =============================================
async function loadGame() {
  const res = await fetch(`/api/game/${gameId}`);
  gameState = await res.json();
  renderScoreboard();
  renderBoard();
  document.getElementById("round-num").textContent = gameState.round;
}

// =============================================
//  SCOREBOARD
// =============================================
function renderScoreboard() {
  const row = document.getElementById("scores-row");
  row.innerHTML = "";

  // Player
  const playerCard = makeScoreCard(gameState.player.name, gameState.player.score, true);
  row.appendChild(playerCard);

  // Bots
  gameState.bots.forEach(b => {
    row.appendChild(makeScoreCard(b.name, b.score, false));
  });
}

function makeScoreCard(name, score, isPlayer) {
  const div = document.createElement("div");
  div.className = "score-card" + (isPlayer ? " is-player" : "");
  div.innerHTML = `
    <div class="sc-name">${name}</div>
    <div class="sc-score">$${score.toLocaleString()}</div>
  `;
  return div;
}

// =============================================
//  BOARD
// =============================================
function renderBoard() {
  const board = document.getElementById("board");
  board.innerHTML = "";

  const categories = Object.keys(gameState.board);

  // Category headers
  categories.forEach(cat => {
    const header = document.createElement("div");
    header.className = "board-cat-header";
    header.textContent = cat;
    board.appendChild(header);
  });

  // Value rows
  const values = [200, 400, 600, 800, 1000];
  values.forEach(val => {
    categories.forEach(cat => {
      const used = gameState.board[cat][val];
      const cell = document.createElement("div");
      cell.className = "board-cell" + (used ? " used" : "");
      cell.innerHTML = `<span class="cell-value">$${val}</span>`;

      if (!used) {
        cell.addEventListener("click", () => openQuestion(cat, val));
      }

      board.appendChild(cell);
    });
  });
}

// =============================================
//  QUESTION MODAL
// =============================================
async function openQuestion(category, value) {
  showLoading("Loading question...");

  try {
    const res = await fetch(`/api/question/${gameId}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ category, value })
    });

    const data = await res.json();
    hideLoading();

    if (data.error) return;

    currentQuestion = { category, value, ...data };
    showQuestionModal(data);

  } catch (e) {
    hideLoading();
  }
}

function showQuestionModal(q) {
  document.getElementById("modal-category").textContent = q.category;
  document.getElementById("modal-value").textContent = `$${q.value}`;
  document.getElementById("modal-question").textContent = q.question;

  const answersEl = document.getElementById("modal-answers");
  answersEl.innerHTML = "";
  q.answers.forEach(ans => {
    const btn = document.createElement("button");
    btn.className = "answer-btn";
    btn.textContent = ans;
    btn.addEventListener("click", () => submitAnswer(ans));
    answersEl.appendChild(btn);
  });

  document.getElementById("modal-result").className = "modal-result hidden";
  document.getElementById("modal-result").textContent = "";
  document.getElementById("modal-bot-results").className = "modal-bot-results hidden";
  document.getElementById("modal-bot-results").innerHTML = "";
  document.getElementById("modal-continue").classList.add("hidden");

  document.getElementById("question-modal").classList.remove("hidden");
}

async function submitAnswer(answer) {
  // Disable all answer buttons immediately
  document.querySelectorAll(".answer-btn").forEach(btn => {
    btn.disabled = true;
  });

  try {
    const res = await fetch(`/api/answer/${gameId}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        category: currentQuestion.category,
        value: currentQuestion.value,
        answer
      })
    });

    const data = await res.json();
    showResult(answer, data);

  } catch (e) {
    closeModal();
  }
}

function showResult(playerAnswer, data) {
  const correct = data.correct_answer;

  // Highlight answer buttons
  document.querySelectorAll(".answer-btn").forEach(btn => {
    if (btn.textContent === correct) {
      btn.classList.add("reveal-correct");
    } else if (btn.textContent === playerAnswer && !data.player_correct) {
      btn.classList.add("wrong");
    }
  });

  // Result banner
  const resultEl = document.getElementById("modal-result");
  if (data.player_correct) {
    resultEl.textContent = `✓ Correct! +$${currentQuestion.value}`;
    resultEl.className = "modal-result correct-res";
  } else {
    resultEl.textContent = `✗ Wrong! -$${currentQuestion.value}`;
    resultEl.className = "modal-result wrong-res";
  }

  // Bot results
  const botEl = document.getElementById("modal-bot-results");
  let html = "<h4>Bot Answers</h4>";
  data.bot_results.forEach(b => {
    const ok = b.correct;
    html += `
      <div class="bot-result-row">
        <span class="bot-name">${b.name}</span>
        <span class="bot-ans">${b.answer}</span>
        <span class="bot-status ${ok ? 'ok' : 'bad'}">${ok ? '✓' : '✗'}</span>
      </div>`;
  });

  if (data.round_winner) {
    const winName = data.round_winner === "player" ? gameState.player.name : data.round_winner;
    html += `<div style="margin-top:0.5rem; font-size:0.8rem; color:#aaa; text-align:center">
      Round winner: <strong style="color:var(--gold)">${winName}</strong>
    </div>`;
  }

  botEl.innerHTML = html;
  botEl.className = "modal-bot-results";

  // Continue button
  const continueBtn = document.getElementById("modal-continue");
  continueBtn.classList.remove("hidden");
  continueBtn.onclick = async () => {
    closeModal();
    if (data.game_over) {
      await triggerGameOver();
    } else {
      await loadGame();
    }
  };
}

function closeModal() {
  document.getElementById("question-modal").classList.add("hidden");
}

// =============================================
//  GAME OVER
// =============================================
async function triggerGameOver() {
  showLoading("Finalizing game...");

  const res = await fetch(`/api/end-game/${gameId}`, { method: "POST" });
  const data = await res.json();

  hideLoading();

  const winner = data.winner;
  const isPlayerWinner = winner.name === gameState.player.name;

  document.getElementById("winner-display").innerHTML = `
    <div class="winner-label">${isPlayerWinner ? "🏆 You Win!" : "Winner"}</div>
    <div class="winner-name">${winner.name}</div>
    <div class="winner-score">$${winner.score.toLocaleString()}</div>
  `;

  const finalScores = document.getElementById("final-scores");
  finalScores.innerHTML = "";
  data.all_scores
    .sort((a, b) => b.score - a.score)
    .forEach(p => {
      const row = document.createElement("div");
      row.className = "final-score-row";
      row.innerHTML = `<span>${p.name}</span><span class="fscore">$${p.score.toLocaleString()}</span>`;
      finalScores.appendChild(row);
    });

  showScreen("gameover-screen");
}

document.getElementById("play-again-btn").addEventListener("click", () => {
  gameId = null;
  gameState = null;
  document.getElementById("player-name").value = "";
  showScreen("setup-screen");
});
