import {useEffect, useRef, useState} from 'react'
import {api} from '../src/api'

const BUZZ_WINDOW = 5.0

interface QuestionPayload {
    question: string
    answers: string[]
    correct_answer: string
    value: number
    category: string
    is_daily_double: boolean
    bot_buzz_times: Record<string, number>
}

interface SubmitResult {
    player_buzzed_first: boolean
    player_correct: boolean
    correct_answer: string
    results: {
        name: string;
        display_name: string;
        is_player: boolean;
        answer: string;
        correct: boolean;
        buzz_time: number
    }[]
    all_buzz_times: { name: string; buzz_time: number; is_player: boolean }[]
    round_winner: string | null
    remaining: number
    game_over: boolean
}

type Phase = 'buzz' | 'answer' | 'second-chance' | 'result'

interface Props {
    gameId: string
    q: QuestionPayload
    playerName: string
    playerScore: number
    onClose: (result: { gameOver: boolean; data: SubmitResult | null }) => void
}

export default function QuestionModal({gameId, q, playerName, onClose}: Props) {
    const [phase, setPhase] = useState<Phase>('buzz')
    const [timeLeft, setTimeLeft] = useState(BUZZ_WINDOW)
    const [, setBuzzed] = useState(false)
    const [selected, setSelected] = useState<string | null>(null)
    const [result, setResult] = useState<SubmitResult | null>(null)
    const [buzzerLose, setBuzzerLose] = useState('')
    const [secondChanceBots, setSecondChanceBots] = useState<SubmitResult | null>(null)

    const buzzTimeRef = useRef<number | null>(null)
    const startRef = useRef<number>(Date.now())
    const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)
    const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)

    useEffect(() => {
        startRef.current = Date.now()

        timerRef.current = setInterval(() => {
            const elapsed = (Date.now() - startRef.current) / 1000
            setTimeLeft(Math.max(0, BUZZ_WINDOW - elapsed))
        }, 80)

        timeoutRef.current = setTimeout(() => {
            clearInterval(timerRef.current!)
            handleBotWin(null)
        }, BUZZ_WINDOW * 1000)

        return () => {
            clearInterval(timerRef.current!)
            clearTimeout(timeoutRef.current!)
        }
    }, [])

    function handleBuzz() {
        clearInterval(timerRef.current!)
        clearTimeout(timeoutRef.current!)
        const playerTime = (Date.now() - startRef.current) / 1000

        const faster = Object.entries(q.bot_buzz_times).find(([, t]) => t < playerTime)
        if (faster) {
            handleBotWin(playerTime)
        } else {
            buzzTimeRef.current = playerTime
            setBuzzed(true)
            setPhase('answer')
        }
    }

    function handleBotWin(playerTime: number | null) {
        const [botName, botTime] = Object.entries(q.bot_buzz_times).sort((a, b) => a[1] - b[1])[0]
        setBuzzerLose(
            playerTime !== null
                ? `${botName} buzzed faster (${botTime.toFixed(2)}s vs your ${playerTime.toFixed(2)}s)`
                : `${botName} buzzed at ${botTime.toFixed(2)}s — you were too slow!`
        )
        setBuzzed(false)
        // Submit bots-only, player_buzz_time=999
        submitBots(playerTime !== null)
    }

    async function submitBots(playerWasThere: boolean) {
        try {
            const data = await api.submitAnswer(gameId, q.category, q.value, '', 999, q.bot_buzz_times)
            if (!data.round_winner && playerWasThere) {
                // Bots all missed — give player second chance
                setSecondChanceBots(data)
                setBuzzerLose('Bots missed! Your turn — pick an answer.')
                setPhase('second-chance')
            } else {
                setResult(data)
                setPhase('result')
            }
        } catch {
            onClose({gameOver: false, data: null})
        }
    }

    async function submitAnswer(answer: string) {
        setSelected(answer)
        try {
            const data = await api.submitAnswer(
                gameId, q.category, q.value, answer,
                buzzTimeRef.current ?? 0, q.bot_buzz_times
            )
            setResult(data)
            setPhase('result')
        } catch {
            onClose({gameOver: false, data: null})
        }
    }

    async function submitSecondChance(answer: string) {
        setSelected(answer)
        try {
            const playerData = await api.submitPlayerAnswer(gameId, q.category, q.value, answer)
            const merged: SubmitResult = {
                ...(secondChanceBots!),
                correct_answer: playerData.correct_answer,
                round_winner: playerData.round_winner,
                game_over: playerData.game_over,
                results: [...(secondChanceBots?.results ?? []), ...playerData.results],
            }
            setResult(merged)
            setPhase('result')
        } catch {
            onClose({gameOver: false, data: null})
        }
    }

    const barWidth = `${(timeLeft / BUZZ_WINDOW) * 100}%`
    const correct = result?.correct_answer ?? ''
    const playerResult = result?.results?.find(r => r.is_player)

    return (
        <div className="modal-backdrop">
            <div className="modal-box">
                <div className="modal-header">
                    <span className="cat-label">{q.category}</span>
                    <span className="val-label">${q.value}</span>
                </div>
                <div className="modal-question">{q.question}</div>

                {/* ── BUZZ PHASE ── */}
                {(phase === 'buzz') && (
                    <div className="buzzer-section">
                        <div className="buzz-bar-wrap">
                            <div className="buzz-bar" style={{width: barWidth, transition: 'width 0.08s linear'}}/>
                        </div>
                        <div className="buzz-timer">{timeLeft.toFixed(1)}s</div>
                        <div className="buzz-status">Be the first to buzz in!</div>
                        <button className="buzz-btn" onClick={handleBuzz}>⚡ BUZZ IN</button>
                    </div>
                )}

                {/* ── BOT WON — waiting for submit ── */}
                {(phase === 'buzz' && buzzerLose) && (
                    <div className="buzz-status lose" style={{marginTop: '0.5rem'}}>{buzzerLose}</div>
                )}

                {/* ── ANSWER PHASE ── */}
                {phase === 'answer' && (
                    <>
                        <div className="buzz-status win" style={{marginBottom: '0.5rem', textAlign: 'center'}}>
                            You buzzed in at {buzzTimeRef.current?.toFixed(2)}s — choose your answer!
                        </div>
                        <AnswerGrid
                            answers={q.answers}
                            selected={selected}
                            correct={null}
                            onSelect={submitAnswer}
                        />
                    </>
                )}

                {/* ── SECOND CHANCE PHASE ── */}
                {phase === 'second-chance' && (
                    <>
                        <div className="buzz-status win" style={{marginBottom: '0.5rem', textAlign: 'center'}}>
                            {buzzerLose}
                        </div>
                        <AnswerGrid
                            answers={q.answers}
                            selected={selected}
                            correct={null}
                            onSelect={submitSecondChance}
                        />
                    </>
                )}

                {/* ── RESULT PHASE ── */}
                {phase === 'result' && result && (
                    <>
                        {playerResult ? (
                            <div className={`result-banner ${playerResult.correct ? 'correct' : 'wrong'}`}>
                                {playerResult.correct ? `✓ Correct! +$${q.value}` : `✗ Wrong! −$${q.value}`}
                            </div>
                        ) : (
                            <div className="result-banner wrong">You didn't buzz in time!</div>
                        )}

                        <AnswerGrid
                            answers={q.answers}
                            selected={selected}
                            correct={correct}
                            onSelect={() => {
                            }}
                            disabled
                        />

                        <div className="results-list">
                            <h4>Buzz Times</h4>
                            {result.all_buzz_times.map(p => (
                                <div key={p.name} className="result-row">
                                    <span
                                        className="rr-name">{p.is_player ? playerName : p.name}{p.is_player ? ' (you)' : ''}</span>
                                    <span
                                        className="rr-ans">{p.buzz_time >= 999 ? '—' : `${p.buzz_time.toFixed(2)}s`}</span>
                                </div>
                            ))}
                            {result.results.length > 0 && (
                                <>
                                    <h4 style={{marginTop: '0.5rem'}}>Answers</h4>
                                    {result.results.map((r, i) => (
                                        <div key={i} className="result-row">
                                            <span className="rr-name">{r.is_player ? 'You' : r.display_name}</span>
                                            <span className="rr-ans">{r.answer || '—'}</span>
                                            <span
                                                className={r.correct ? 'rr-ok' : 'rr-bad'}>{r.correct ? '✓' : '✗'}</span>
                                        </div>
                                    ))}
                                </>
                            )}
                            {result.round_winner ? (
                                <div style={{
                                    marginTop: '0.5rem',
                                    textAlign: 'center',
                                    color: '#aaa',
                                    fontSize: '0.78rem'
                                }}>
                                    +${q.value} → <strong style={{color: 'var(--gold)'}}>
                                    {result.round_winner === 'player' ? playerName : result.round_winner}
                                </strong>
                                </div>
                            ) : (
                                <div style={{
                                    marginTop: '0.5rem',
                                    textAlign: 'center',
                                    color: '#aaa',
                                    fontSize: '0.78rem'
                                }}>
                                    No winner · correct: <strong style={{color: 'var(--gold)'}}>{correct}</strong>
                                </div>
                            )}
                        </div>

                        <button
                            className="btn-primary"
                            style={{marginTop: '1rem'}}
                            onClick={() => onClose({gameOver: result.game_over, data: result})}
                        >
                            Continue
                        </button>
                    </>
                )}
            </div>
        </div>
    )
}

function AnswerGrid({
                        answers, selected, correct, onSelect, disabled = false
                    }: {
    answers: string[];
    selected: string | null;
    correct: string | null;
    onSelect: (a: string) => void;
    disabled?: boolean
}) {
    return (
        <div className="answer-grid">
            {answers.map(ans => {
                let cls = 'answer-btn'
                if (correct) {
                    if (ans === correct) cls += ' reveal-correct'
                    else if (ans === selected) cls += ' reveal-wrong'
                    else cls += ' dimmed'
                } else if (ans === selected) {
                    cls += ' selected'
                }
                return (
                    <button
                        key={ans}
                        className={cls}
                        disabled={disabled || selected !== null}
                        onClick={() => !disabled && selected === null && onSelect(ans)}
                    >
                        {ans}
                    </button>
                )
            })}
        </div>
    )
}