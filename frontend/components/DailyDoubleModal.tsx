import {useState} from 'react'
import {api} from '../src/api'

interface Props {
    gameId: string
    category: string
    value: number
    question: string
    answers: string[]
    playerScore: number
    onClose: (gameOver: boolean) => void
}

type Phase = 'wager' | 'answer' | 'result'

export default function DailyDoubleModal({gameId, category, value, question, answers, playerScore, onClose}: Props) {
    const maxWager = Math.max(200, playerScore)
    const [phase, setPhase] = useState<Phase>('wager')
    const [wager, setWager] = useState('')
    const [confirmedWager, setConfirmedWager] = useState(0)
    const [selected, setSelected] = useState<string | null>(null)
    const [correct, setCorrect] = useState<string | null>(null)
    const [isCorrect, setIsCorrect] = useState<boolean | null>(null)
    const [delta, setDelta] = useState(0)
    const [gameOver, setGameOver] = useState(false)

    function confirmWager() {
        let w = parseInt(wager) || 0
        w = Math.max(0, Math.min(w, maxWager))
        setConfirmedWager(w)
        setPhase('answer')
    }

    async function submitAnswer(ans: string) {
        setSelected(ans)
        try {
            const data = await api.dailyDouble(gameId, category, value, confirmedWager, ans)
            setCorrect(data.correct_answer)
            setIsCorrect(data.player_correct)
            setDelta(data.delta)
            setGameOver(data.game_over)
            setPhase('result')
        } catch {
            onClose(false)
        }
    }

    return (
        <div className="modal-backdrop">
            <div className="modal-box" style={{textAlign: 'center'}}>
                <div className="dd-banner">⭐ DAILY DOUBLE ⭐</div>
                <div style={{
                    fontSize: '0.8rem',
                    color: 'var(--gray)',
                    letterSpacing: '2px',
                    textTransform: 'uppercase',
                    marginBottom: '1rem'
                }}>
                    {category} — ${value}
                </div>

                {phase === 'wager' && (
                    <>
                        <div style={{color: 'rgba(255,255,255,0.7)', marginBottom: '0.5rem', fontSize: '0.95rem'}}>
                            Your score: ${playerScore.toLocaleString()} · Max wager: ${maxWager.toLocaleString()}
                        </div>
                        <div className="form-group" style={{textAlign: 'left', marginTop: '1rem'}}>
                            <label>Your Wager</label>
                            <input
                                type="number" min={0} max={maxWager}
                                value={wager}
                                onChange={e => setWager(e.target.value)}
                                onKeyDown={e => e.key === 'Enter' && confirmWager()}
                                placeholder={`0 – ${maxWager}`}
                            />
                        </div>
                        <button className="btn-primary" onClick={confirmWager}>Confirm Wager</button>
                    </>
                )}

                {phase === 'answer' && (
                    <>
                        <div style={{fontSize: '0.8rem', color: 'var(--gray)', marginBottom: '0.5rem'}}>Wager:
                            ${confirmedWager.toLocaleString()}</div>
                        <div className="modal-question">{question}</div>
                        <div className="answer-grid">
                            {answers.map(ans => (
                                <button
                                    key={ans}
                                    className={`answer-btn${selected === ans ? ' selected' : ''}`}
                                    disabled={selected !== null}
                                    onClick={() => submitAnswer(ans)}
                                >
                                    {ans}
                                </button>
                            ))}
                        </div>
                    </>
                )}

                {phase === 'result' && (
                    <>
                        <div className={`result-banner ${isCorrect ? 'correct' : 'wrong'}`}>
                            {isCorrect ? `✓ Correct! +$${confirmedWager.toLocaleString()}` : `✗ Wrong! −$${Math.abs(delta).toLocaleString()}`}
                        </div>
                        {!isCorrect && (
                            <div style={{marginTop: '0.5rem', color: 'var(--gray)', fontSize: '0.88rem'}}>
                                Correct answer: <strong style={{color: 'var(--gold)'}}>{correct}</strong>
                            </div>
                        )}
                        <div className="answer-grid" style={{marginTop: '1rem'}}>
                            {answers.map(ans => {
                                let cls = 'answer-btn'
                                if (ans === correct) cls += ' reveal-correct'
                                else if (ans === selected && !isCorrect) cls += ' reveal-wrong'
                                else cls += ' dimmed'
                                return <button key={ans} className={cls} disabled>{ans}</button>
                            })}
                        </div>
                        <button className="btn-primary" style={{marginTop: '1rem'}} onClick={() => onClose(gameOver)}>
                            Continue
                        </button>
                    </>
                )}
            </div>
        </div>
    )
}