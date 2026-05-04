import { useEffect, useState } from 'react'
import { api } from '../src/api'
import type { GameState, Screen } from '../src/App'

interface Props {
  gameId: string
  gameState: GameState
  setLoading: (v: boolean, msg?: string) => void
  navigate: (screen: Screen, extra?: Partial<{ gameId: string; gameState: GameState }>) => void
}

type Phase = 'wager' | 'answer' | 'reveal'

interface RevealEntry {
  name: string
  is_player: boolean
  correct: boolean
  wager: number
  delta: number
  answer: string
}

export default function FinalScreen({ gameId, gameState, setLoading, navigate }: Props) {
  const [phase, setPhase] = useState<Phase>('wager')
  const [question, setQuestion] = useState('')
  const [answers, setAnswers] = useState<string[]>([])
  const [playerScore, setPlayerScore] = useState(gameState.player.score)
  const [wager, setWager] = useState('')
  const [confirmedWager, setConfirmedWager] = useState(0)
  const [selected, setSelected] = useState<string | null>(null)
  const [correct, setCorrect] = useState('')
  const [reveal, setReveal] = useState<RevealEntry[]>([])


  useEffect(() => {
    loadFinal()
  }, [])

  async function loadFinal() {
    setLoading(true, 'Loading Final Jeopardy...')
    try {
      const data = await api.getFinal(gameId)
      if (data.status === 'completed') {
        await triggerGameOver()
        return
      }
      setQuestion(data.question)
      setAnswers(shuffle([...data.answers]))
      setPlayerScore(data.player_score)
      setLoading(false)
    } catch {
      setLoading(false)
      await triggerGameOver()
    }
  }

  function shuffle<T>(arr: T[]): T[] {
    for (let i = arr.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [arr[i], arr[j]] = [arr[j], arr[i]]
    }
    return arr
  }

  function confirmWager() {
    let w = parseInt(wager) || 0
    // Allow wagering up to score; if score <= 0, allow wager of 0
    w = Math.max(0, Math.min(w, Math.max(0, playerScore)))
    setConfirmedWager(w)
    setPhase('answer')
  }

  async function submitFinal() {
    if (!selected) return
    setLoading(true, 'Submitting...')
    try {
      const data = await api.submitFinal(gameId, confirmedWager, selected)
      setCorrect(data.correct_answer)
      setReveal(data.reveal)
      setLoading(false)
      setPhase('reveal')
    } catch {
      setLoading(false)
    }
  }

  async function triggerGameOver() {
    setLoading(true, 'Finalizing game...')
    try {
      const data = await api.endGame(gameId)
      setLoading(false)
      navigate('gameover', {
        gameState: {
          ...gameState,
          _winner: data.winner,
          _allScores: data.all_scores,
        } as unknown as GameState,
      })
    } catch {
      setLoading(false)
      navigate('gameover')
    }
  }

  const maxWager = Math.max(0, playerScore)

  return (
    <div className="final-screen">
      <div className="final-inner">
        <div className="final-title">FINAL JEOPARDY</div>

        {phase === 'wager' && (
          <div className="card">
            <div style={{ color: 'rgba(255,255,255,0.7)', marginBottom: '0.5rem', fontSize: '0.95rem', textAlign: 'center' }}>
              Your score: ${playerScore.toLocaleString()} · Max wager: ${maxWager.toLocaleString()}
            </div>
            <p className="hint-text" style={{ marginBottom: '1rem' }}>Place your wager before the question is revealed.</p>
            <div className="form-group">
              <label>Your Wager (0 – ${maxWager.toLocaleString()})</label>
              <input
                type="number" min={0} max={maxWager}
                value={wager}
                onChange={e => setWager(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && confirmWager()}
                placeholder={`0 – ${maxWager}`}
              />
            </div>
            <button className="btn-primary" onClick={confirmWager}>Reveal Question</button>
          </div>
        )}

        {phase === 'answer' && (
          <div className="card">
            <div style={{ fontSize: '0.75rem', color: 'var(--gray)', letterSpacing: '2px', textAlign: 'center', marginBottom: '0.75rem' }}>
              WAGER: ${confirmedWager.toLocaleString()}
            </div>
            <div className="modal-question" style={{ fontSize: '1.3rem', marginBottom: '1.5rem' }}>{question}</div>
            <div className="answer-grid">
              {answers.map(ans => (
                <button
                  key={ans}
                  className={`answer-btn${selected === ans ? ' selected' : ''}`}
                  onClick={() => setSelected(ans)}
                >
                  {ans}
                </button>
              ))}
            </div>
            <button
              className="btn-primary"
              style={{ marginTop: '0.75rem' }}
              disabled={!selected}
              onClick={submitFinal}
            >
              Submit Answer
            </button>
          </div>
        )}

        {phase === 'reveal' && (
          <div className="card">
            <div className="final-correct">Correct Answer: {correct}</div>
            {reveal.map((r, i) => {
              const sign = r.delta >= 0 ? '+' : ''
              return (
                <div key={i} className={`reveal-row ${r.correct ? 'correct' : 'wrong'}`}>
                  <span className="reveal-name">{r.name}{r.is_player ? ' (You)' : ''}</span>
                  <span className="reveal-ans">{r.answer}</span>
                  <span className="reveal-wager">wagered ${r.wager.toLocaleString()}</span>
                  <span className={`reveal-delta ${r.correct ? 'ok' : 'bad'}`}>{sign}${r.delta.toLocaleString()}</span>
                </div>
              )
            })}
            <button className="btn-primary" style={{ marginTop: '1.5rem' }} onClick={triggerGameOver}>
              See Final Scores
            </button>
          </div>
        )}
      </div>
    </div>
  )
}