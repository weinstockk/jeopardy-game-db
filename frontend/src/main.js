import './style.css'

const API = 'http://localhost:5000'

// =============================================
//  STATE
// =============================================
let gameId = null
let gameState = null
let selectedDifficulty = 'easy'
let currentQuestion = null       // { category, value, answers, correct_answer, is_daily_double, bot_buzz_times }
let buzzStartTime = null         // when question was shown (for measuring player buzz time)
let buzzerTimeout = null         // the 5s countdown timeout
let selectedAnswer = null        // which answer button player clicked
let finalWager = 0               // player's final jeopardy wager

const BUZZ_WINDOW = 5.0          // seconds player has to buzz in

// =============================================
//  SCREENS
// =============================================
function showScreen(id) {
  document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'))
  document.getElementById(id).classList.add('active')
}

function showLoading(msg = 'Loading...') {
  document.getElementById('loading-text').textContent = msg
  document.getElementById('loading-overlay').classList.remove('hidden')
}

function hideLoading() {
  document.getElementById('loading-overlay').classList.add('hidden')
}

// =============================================
//  SETUP SCREEN
// =============================================
document.querySelectorAll('.diff-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.diff-btn').forEach(b => b.classList.remove('active'))
    btn.classList.add('active')
    selectedDifficulty = btn.dataset.diff
  })
})

document.getElementById('start-btn').addEventListener('click', async () => {
  const name = document.getElementById('player-name').value.trim()
  const errEl = document.getElementById('setup-error')
  if (!name) { errEl.textContent = 'Please enter your name.'; return }
  errEl.textContent = ''
  showLoading('Fetching categories...')
  try {
    const res = await fetch(`${API}/api/new-game`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ player_name: name, ai_difficulty: selectedDifficulty })
    })
    const data = await res.json()
    if (data.error) { hideLoading(); errEl.textContent = data.error; return }
    gameId = data.game_id
    hideLoading()
    await loadGame()
    showScreen('game-screen')
  } catch (e) {
    hideLoading()
    errEl.textContent = 'Cannot connect to server. Make sure Flask is running.'
  }
})

document.getElementById('load-game-btn').addEventListener('click', async () => {
  showLoading('Fetching active games...')
  try {
    const res = await fetch(`${API}/api/active-games`)
    const games = await res.json()
    hideLoading()
    showLoadGameScreen(games)
  } catch (e) {
    hideLoading()
    document.getElementById('setup-error').textContent = 'Could not load games.'
  }
})

document.getElementById('history-btn').addEventListener('click', async () => {
  showLoading('Fetching history...')
  try {
    const res = await fetch(`${API}/api/history`)
    const history = await res.json()
    hideLoading()
    showHistoryScreen(history)
  } catch (e) {
    hideLoading()
  }
})

// =============================================
//  LOAD GAME SCREEN
// =============================================
function showLoadGameScreen(games) {
  const list = document.getElementById('load-game-list')
  list.innerHTML = ''
  if (games.length === 0) {
    list.innerHTML = '<p class="no-games">No active games found.</p>'
  } else {
    games.forEach(g => {
      const item = document.createElement('div')
      item.className = 'game-list-item'
      item.innerHTML = `
        <div>
          <div class="gli-player">${g.player_name}</div>
          <div class="gli-info">Round ${g.round} • ${g.remaining} questions left</div>
        </div>
        <button class="primary-btn small-btn" data-id="${g.game_id}">Resume</button>
      `
      item.querySelector('button').addEventListener('click', async () => {
        gameId = g.game_id
        showLoading('Loading game...')
        await loadGame()
        hideLoading()
        showScreen('game-screen')
      })
      list.appendChild(item)
    })
  }
  showScreen('load-game-screen')
}

document.getElementById('back-to-setup-btn').addEventListener('click', () => showScreen('setup-screen'))

// =============================================
//  HISTORY SCREEN
// =============================================
function showHistoryScreen(history) {
  const list = document.getElementById('history-list')
  list.innerHTML = ''
  if (history.length === 0) {
    list.innerHTML = '<p class="no-games">No completed games yet.</p>'
  } else {
    history.forEach(g => {
      const date = g.completed_at ? new Date(g.completed_at * 1000).toLocaleDateString() : ''
      const scores = [g.player, ...(g.bots || [])]
        .sort((a, b) => b.score - a.score)
        .map(p => `${p.name}: $${p.score.toLocaleString()}`)
        .join(' • ')
      const item = document.createElement('div')
      item.className = 'game-list-item'
      item.innerHTML = `
        <div>
          <div class="gli-player">🏆 ${g.winner.name} won</div>
          <div class="gli-info">${scores}</div>
          <div class="gli-info" style="color:#555">${date}</div>
        </div>
      `
      list.appendChild(item)
    })
  }
  showScreen('history-screen')
}

document.getElementById('back-from-history-btn').addEventListener('click', () => showScreen('setup-screen'))

// =============================================
//  LOAD GAME STATE
// =============================================
async function loadGame() {
  const res = await fetch(`${API}/api/game/${gameId}`)
  gameState = await res.json()
  renderScoreboard()
  renderBoard()
  document.getElementById('round-num').textContent = gameState.round
}

// =============================================
//  SCOREBOARD
// =============================================
function renderScoreboard() {
  const row = document.getElementById('scores-row')
  row.innerHTML = ''
  row.appendChild(makeScoreCard(gameState.player.name, gameState.player.score, true))
  gameState.bots.forEach(b => row.appendChild(makeScoreCard(b.name, b.score, false)))
}

function makeScoreCard(name, score, isPlayer) {
  const div = document.createElement('div')
  div.className = 'score-card' + (isPlayer ? ' is-player' : '')
  div.innerHTML = `<div class="sc-name">${name}</div><div class="sc-score">$${score.toLocaleString()}</div>`
  return div
}

// =============================================
//  BOARD
// =============================================
function renderBoard() {
  const board = document.getElementById('board')
  board.innerHTML = ''
  const categories = Object.keys(gameState.board)

  categories.forEach(cat => {
    const header = document.createElement('div')
    header.className = 'board-cat-header'
    header.textContent = cat
    board.appendChild(header)
  })

  const values = [200, 400, 600, 800, 1000]
  values.forEach(val => {
    categories.forEach(cat => {
      const cellData = gameState.board[cat][val]
      const used = cellData.selected
      const cell = document.createElement('div')
      cell.className = 'board-cell' + (used ? ' used' : '')
      cell.innerHTML = `<span class="cell-value">$${val}</span>`
      if (!used) cell.addEventListener('click', () => openQuestion(cat, val))
      board.appendChild(cell)
    })
  })
}

// =============================================
//  OPEN QUESTION
// =============================================
async function openQuestion(category, value) {
  showLoading('Loading question...')
  try {
    const res = await fetch(`${API}/api/question/${gameId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ category, value })
    })
    const data = await res.json()
    hideLoading()
    if (data.error) return

    currentQuestion = { category, value, ...data }

    if (data.is_daily_double) {
      openDailyDouble(data)
    } else {
      openNormalQuestion(data)
    }
  } catch (e) {
    hideLoading()
  }
}

// =============================================
//  NORMAL QUESTION + REAL BUZZER
// =============================================
function openNormalQuestion(q) {
  // Reset modal state
  document.getElementById('modal-category').textContent = q.category
  document.getElementById('modal-value').textContent = `$${q.value}`
  document.getElementById('modal-question').textContent = q.question
  document.getElementById('buzzer-phase').classList.remove('hidden')
  document.getElementById('answer-phase').classList.add('hidden')
  document.getElementById('modal-result').className = 'modal-result hidden'
  document.getElementById('modal-results-list').className = 'modal-bot-results hidden'
  document.getElementById('modal-results-list').innerHTML = ''
  document.getElementById('modal-continue').classList.add('hidden')
  document.getElementById('buzz-btn').disabled = false
  document.getElementById('buzz-btn').classList.remove('buzzed')
  document.getElementById('buzz-status').textContent = 'Be the first to buzz in!'
  document.getElementById('buzz-status').className = 'buzz-status'

  // Build answer buttons (hidden until buzzer phase is done)
  const answersEl = document.getElementById('modal-answers')
  answersEl.innerHTML = ''
  q.answers.forEach(ans => {
    const btn = document.createElement('button')
    btn.className = 'answer-btn'
    btn.textContent = ans
    btn.addEventListener('click', () => {
      selectedAnswer = ans
      lockAnswerSelection(btn)
    })
    answersEl.appendChild(btn)
  })

  document.getElementById('question-modal').classList.remove('hidden')

  // Start buzz countdown
  startBuzzCountdown()
}

function startBuzzCountdown() {
  buzzStartTime = Date.now()
  selectedAnswer = null

  const bar = document.getElementById('buzz-timer-bar')
  const timerText = document.getElementById('buzz-timer-text')
  bar.style.transition = 'none'
  bar.style.width = '100%'

  // Animate bar
  requestAnimationFrame(() => {
    bar.style.transition = `width ${BUZZ_WINDOW}s linear`
    bar.style.width = '0%'
  })

  // Update timer text
  const interval = setInterval(() => {
    const elapsed = (Date.now() - buzzStartTime) / 1000
    const remaining = Math.max(0, BUZZ_WINDOW - elapsed)
    timerText.textContent = remaining.toFixed(1) + 's'
    if (remaining <= 0) clearInterval(interval)
  }, 100)

  // Find fastest bot buzz time
  const botBuzzTimes = currentQuestion.bot_buzz_times || {}
  const fastestBotTime = Math.min(...Object.values(botBuzzTimes))

  // If fastest bot buzzes before player window ends, bot wins automatically
  buzzerTimeout = setTimeout(() => {
    clearInterval(interval)
    // Player didn't buzz in time — bot wins
    handleBotWonBuzz()
  }, BUZZ_WINDOW * 1000)

  // Attach buzz button handler
  const buzzBtn = document.getElementById('buzz-btn')
  buzzBtn.onclick = () => {
    const playerBuzzTime = (Date.now() - buzzStartTime) / 1000
    clearTimeout(buzzerTimeout)
    clearInterval(interval)

    // Check if player beat all bots
    const botBeatPlayer = Object.entries(botBuzzTimes).find(([name, t]) => t < playerBuzzTime)

    if (botBeatPlayer) {
      // A bot was faster — bot wins even though player tried to buzz
      handleBotWonBuzz(playerBuzzTime)
    } else {
      // Player wins the buzz
      handlePlayerWonBuzz(playerBuzzTime)
    }
  }
}

function handlePlayerWonBuzz(playerBuzzTime) {
  document.getElementById('buzz-btn').disabled = true
  document.getElementById('buzz-btn').classList.add('buzzed')
  document.getElementById('buzz-status').textContent = `You buzzed in! (${playerBuzzTime.toFixed(2)}s) Pick your answer.`
  document.getElementById('buzz-status').className = 'buzz-status buzz-win'
  document.getElementById('buzzer-phase').classList.add('hidden')
  document.getElementById('answer-phase').classList.remove('hidden')

  // Store buzz time for submission
  currentQuestion.playerBuzzTime = playerBuzzTime
}

function handleBotWonBuzz(playerBuzzTime = null) {
  // Find which bot was fastest
  const botBuzzTimes = currentQuestion.bot_buzz_times || {}
  const fastestBot = Object.entries(botBuzzTimes).sort((a, b) => a[1] - b[1])[0]
  const [botName, botTime] = fastestBot

  document.getElementById('buzz-btn').disabled = true
  document.getElementById('buzzer-phase').classList.add('hidden')

  const statusEl = document.getElementById('buzz-status')
  statusEl.textContent = playerBuzzTime
    ? `${botName} buzzed in faster (${botTime.toFixed(2)}s vs your ${playerBuzzTime.toFixed(2)}s)`
    : `${botName} buzzed in at ${botTime.toFixed(2)}s — you didn't buzz in time!`
  statusEl.className = 'buzz-status buzz-lose'
  statusEl.classList.remove('hidden')
  document.getElementById('buzzer-phase').classList.remove('hidden')
  document.getElementById('buzz-btn').style.display = 'none'

  // Auto-submit with bot winning the buzz
  submitAnswer(null, playerBuzzTime || BUZZ_WINDOW + 1)
}

function lockAnswerSelection(selectedBtn) {
  document.querySelectorAll('.answer-btn').forEach(btn => {
    btn.disabled = true
    if (btn !== selectedBtn) btn.classList.add('dimmed')
  })
  selectedBtn.classList.add('selected-answer')

  // Submit after brief delay so player sees their selection
  setTimeout(() => {
    submitAnswer(selectedAnswer, currentQuestion.playerBuzzTime || 0)
  }, 400)
}

async function submitAnswer(answer, playerBuzzTime) {
  try {
    const res = await fetch(`${API}/api/answer/${gameId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        category: currentQuestion.category,
        value: currentQuestion.value,
        answer: answer || '',
        player_buzz_time: playerBuzzTime,
        bot_buzz_times: currentQuestion.bot_buzz_times
      })
    })
    const data = await res.json()
    showNormalResult(data)
  } catch (e) {
    closeModal()
  }
}

function showNormalResult(data) {
  const correct = data.correct_answer

  // Highlight answer buttons if player got to answer
  if (data.player_buzzed_first) {
    document.querySelectorAll('.answer-btn').forEach(btn => {
      btn.disabled = true
      if (btn.textContent === correct) btn.classList.add('reveal-correct')
      else if (btn.classList.contains('selected-answer') && !data.player_correct) btn.classList.add('wrong')
    })
  }

  // Result banner
  const resultEl = document.getElementById('modal-result')
  if (data.player_buzzed_first) {
    if (data.player_correct) {
      resultEl.textContent = `✓ Correct! +$${currentQuestion.value}`
      resultEl.className = 'modal-result correct-res'
    } else {
      resultEl.textContent = `✗ Wrong! -$${currentQuestion.value}`
      resultEl.className = 'modal-result wrong-res'
    }
  } else {
    const winner = data.results[0]
    resultEl.textContent = `${winner.display_name} buzzed in first!`
    resultEl.className = 'modal-result wrong-res'
  }

  // Buzz time breakdown
  const resultsEl = document.getElementById('modal-results-list')
  let html = '<h4>Buzz Times</h4>'
  data.all_buzz_times.forEach(p => {
    const you = p.is_player ? ' (you)' : ''
    html += `<div class="bot-result-row">
      <span class="bot-name">${p.name}${you}</span>
      <span class="bot-ans">${p.buzz_time.toFixed(2)}s</span>
    </div>`
  })

  if (data.results.length > 0) {
    const r = data.results[0]
    const label = r.is_player ? 'You' : r.display_name
    const status = r.correct ? '✓ correct' : '✗ wrong'
    const cls = r.correct ? 'ok' : 'bad'
    html += `<div class="bot-result-row" style="margin-top:0.5rem;border-top:1px solid rgba(255,255,255,0.1);padding-top:0.5rem">
      <span class="bot-name">${label} answered:</span>
      <span class="bot-ans">${r.answer}</span>
      <span class="bot-status ${cls}">${status}</span>
    </div>`
  }

  if (data.round_winner) {
    const winName = data.round_winner === 'player' ? gameState.player.name : data.round_winner
    html += `<div style="margin-top:0.5rem;text-align:center;color:#aaa;font-size:0.8rem">
      +$${currentQuestion.value} → <strong style="color:var(--gold)">${winName}</strong>
    </div>`
  } else {
    html += `<div style="margin-top:0.5rem;text-align:center;color:#aaa;font-size:0.8rem">No winner this round — correct answer: <strong style="color:var(--gold)">${correct}</strong></div>`
  }

  resultsEl.innerHTML = html
  resultsEl.className = 'modal-bot-results'

  document.getElementById('buzz-btn').style.display = ''

  const continueBtn = document.getElementById('modal-continue')
  continueBtn.classList.remove('hidden')
  continueBtn.onclick = async () => {
    closeModal()
    if (data.game_over) {
      await startFinalJeopardy()
    } else {
      await loadGame()
    }
  }
}

function closeModal() {
  document.getElementById('question-modal').classList.add('hidden')
  if (buzzerTimeout) clearTimeout(buzzerTimeout)
  document.getElementById('buzz-btn').style.display = ''
}

// =============================================
//  DAILY DOUBLE
// =============================================
function openDailyDouble(q) {
  const player = gameState.player
  const maxWager = Math.max(200, player.score)

  document.getElementById('dd-category').textContent = `${q.category} — $${q.value}`
  document.getElementById('dd-score-display').textContent = `Your score: $${player.score.toLocaleString()} | Max wager: $${maxWager.toLocaleString()}`
  document.getElementById('dd-wager-input').max = maxWager
  document.getElementById('dd-wager-input').value = ''

  document.getElementById('dd-wager-phase').classList.remove('hidden')
  document.getElementById('dd-question-phase').classList.add('hidden')
  document.getElementById('dd-result').className = 'modal-result hidden'
  document.getElementById('dd-continue-btn').classList.add('hidden')

  document.getElementById('dd-modal').classList.remove('hidden')
}

document.getElementById('dd-confirm-wager-btn').addEventListener('click', () => {
  const input = document.getElementById('dd-wager-input')
  const player = gameState.player
  const maxWager = Math.max(200, player.score)
  let wager = parseInt(input.value) || 0
  wager = Math.max(0, Math.min(wager, maxWager))
  currentQuestion.ddWager = wager

  document.getElementById('dd-wager-phase').classList.add('hidden')

  // Show question
  document.getElementById('dd-question').textContent = currentQuestion.question
  const answersEl = document.getElementById('dd-answers')
  answersEl.innerHTML = ''
  currentQuestion.answers.forEach(ans => {
    const btn = document.createElement('button')
    btn.className = 'answer-btn'
    btn.textContent = ans
    btn.addEventListener('click', () => submitDailyDouble(ans, wager))
    answersEl.appendChild(btn)
  })

  document.getElementById('dd-question-phase').classList.remove('hidden')
})

async function submitDailyDouble(answer, wager) {
  document.querySelectorAll('#dd-answers .answer-btn').forEach(b => b.disabled = true)

  try {
    const res = await fetch(`${API}/api/daily-double/${gameId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        category: currentQuestion.category,
        value: currentQuestion.value,
        wager,
        answer
      })
    })
    const data = await res.json()

    const correct = data.correct_answer
    document.querySelectorAll('#dd-answers .answer-btn').forEach(btn => {
      if (btn.textContent === correct) btn.classList.add('reveal-correct')
      else if (btn.textContent === answer && !data.player_correct) btn.classList.add('wrong')
    })

    const resultEl = document.getElementById('dd-result')
    if (data.player_correct) {
      resultEl.textContent = `✓ Correct! +$${data.wager.toLocaleString()}`
      resultEl.className = 'modal-result correct-res'
    } else {
      resultEl.textContent = `✗ Wrong! -$${data.wager.toLocaleString()} | Answer: ${correct}`
      resultEl.className = 'modal-result wrong-res'
    }

    document.getElementById('dd-continue-btn').classList.remove('hidden')
    document.getElementById('dd-continue-btn').onclick = async () => {
      document.getElementById('dd-modal').classList.add('hidden')
      if (data.game_over) {
        await startFinalJeopardy()
      } else {
        await loadGame()
      }
    }
  } catch (e) {
    document.getElementById('dd-modal').classList.add('hidden')
  }
}

// =============================================
//  FINAL JEOPARDY
// =============================================
async function startFinalJeopardy() {
  showLoading('Loading Final Jeopardy...')
  try {
    const res = await fetch(`${API}/api/final/${gameId}`)
    const data = await res.json()
    hideLoading()

    if (data.error || data.status === 'completed') {
      await triggerGameOver()
      return
    }

    const player = gameState.player
    document.getElementById('final-score-display').textContent =
      `Your score: $${player.score.toLocaleString()} | Max wager: $${player.score.toLocaleString()}`
    document.getElementById('final-wager-input').max = player.score
    document.getElementById('final-wager-input').value = ''

    document.getElementById('final-wager-phase').classList.remove('hidden')
    document.getElementById('final-question-phase').classList.add('hidden')
    document.getElementById('final-reveal-phase').classList.add('hidden')

    // Store final question data
    currentQuestion = { ...data }

    showScreen('final-screen')
  } catch (e) {
    hideLoading()
    await triggerGameOver()
  }
}

document.getElementById('final-confirm-wager-btn').addEventListener('click', () => {
  const input = document.getElementById('final-wager-input')
  const player = gameState.player
  let wager = parseInt(input.value) || 0
  wager = Math.max(0, Math.min(wager, player.score))
  finalWager = wager

  document.getElementById('final-wager-phase').classList.add('hidden')

  // Show question + answer choices
  document.getElementById('final-question').textContent = currentQuestion.question

  const answersEl = document.getElementById('final-answers')
  answersEl.innerHTML = ''
  selectedAnswer = null

  const allAnswers = [...(currentQuestion.answers || [])]
  // Shuffle if not already shuffled
  for (let i = allAnswers.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [allAnswers[i], allAnswers[j]] = [allAnswers[j], allAnswers[i]]
  }

  allAnswers.forEach(ans => {
    const btn = document.createElement('button')
    btn.className = 'answer-btn'
    btn.textContent = ans
    btn.addEventListener('click', () => {
      document.querySelectorAll('#final-answers .answer-btn').forEach(b => b.classList.remove('selected-answer'))
      btn.classList.add('selected-answer')
      selectedAnswer = ans
      document.getElementById('final-submit-btn').classList.remove('hidden')
    })
    answersEl.appendChild(btn)
  })

  document.getElementById('final-submit-btn').classList.add('hidden')
  document.getElementById('final-question-phase').classList.remove('hidden')
})

document.getElementById('final-submit-btn').addEventListener('click', async () => {
  if (!selectedAnswer) return
  document.querySelectorAll('#final-answers .answer-btn').forEach(b => b.disabled = true)
  document.getElementById('final-submit-btn').disabled = true

  try {
    const res = await fetch(`${API}/api/final/${gameId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ wager: finalWager, answer: selectedAnswer })
    })
    const data = await res.json()
    showFinalReveal(data)
  } catch (e) {
    await triggerGameOver()
  }
})

function showFinalReveal(data) {
  document.getElementById('final-question-phase').classList.add('hidden')

  document.getElementById('final-correct-answer').textContent =
    `Correct Answer: ${data.correct_answer}`

  const list = document.getElementById('final-reveal-list')
  list.innerHTML = ''

  data.reveal.forEach(r => {
    const sign = r.delta >= 0 ? '+' : ''
    const cls = r.correct ? 'reveal-row-correct' : 'reveal-row-wrong'
    const row = document.createElement('div')
    row.className = `reveal-row ${cls}`
    row.innerHTML = `
      <div class="reveal-name">${r.name}${r.is_player ? ' (You)' : ''}</div>
      <div class="reveal-answer">${r.answer}</div>
      <div class="reveal-wager">Wagered: $${r.wager.toLocaleString()}</div>
      <div class="reveal-delta ${r.correct ? 'ok' : 'bad'}">${sign}$${r.delta.toLocaleString()}</div>
    `
    list.appendChild(row)
  })

  document.getElementById('final-reveal-phase').classList.remove('hidden')
}

document.getElementById('final-end-btn').addEventListener('click', async () => {
  await triggerGameOver()
})

// =============================================
//  GAME OVER
// =============================================
async function triggerGameOver() {
  showLoading('Finalizing game...')
  try {
    const res = await fetch(`${API}/api/end-game/${gameId}`, { method: 'POST' })
    const data = await res.json()
    hideLoading()

    const winner = data.winner
    const isPlayerWinner = winner.name === gameState.player.name

    document.getElementById('winner-display').innerHTML = `
      <div class="winner-label">${isPlayerWinner ? '🏆 You Win!' : 'Winner'}</div>
      <div class="winner-name">${winner.name}</div>
      <div class="winner-score">$${winner.score.toLocaleString()}</div>
    `

    const finalScoresEl = document.getElementById('final-scores')
    finalScoresEl.innerHTML = ''
    data.all_scores.sort((a, b) => b.score - a.score).forEach(p => {
      const row = document.createElement('div')
      row.className = 'final-score-row'
      row.innerHTML = `<span>${p.name}</span><span class="fscore">$${p.score.toLocaleString()}</span>`
      finalScoresEl.appendChild(row)
    })

    showScreen('gameover-screen')
  } catch (e) {
    hideLoading()
    showScreen('gameover-screen')
  }
}

document.getElementById('play-again-btn').addEventListener('click', () => {
  gameId = null
  gameState = null
  currentQuestion = null
  selectedAnswer = null
  finalWager = 0
  document.getElementById('player-name').value = ''
  showScreen('setup-screen')
})
