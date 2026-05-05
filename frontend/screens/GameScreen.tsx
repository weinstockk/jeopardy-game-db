import {useState} from 'react'
import {api} from '../src/api'
import type {GameState, Screen} from '../src/App'
import QuestionModal from '../components/QuestionModal'
import DailyDoubleModal from '../components/DailyDoubleModal'

interface QuestionPayload {
    question: string
    answers: string[]
    correct_answer: string
    value: number
    category: string
    is_daily_double: boolean
    bot_buzz_times: Record<string, number>
}

interface Props {
    gameId: string
    gameState: GameState
    setGameState: (gs: GameState) => void
    setLoading: (v: boolean, msg?: string) => void
    navigate: (screen: Screen, extra?: Partial<{ gameId: string; gameState: GameState }>) => void
}

export default function GameScreen({gameId, gameState, setGameState, setLoading, navigate}: Props) {
    const [activeQ, setActiveQ] = useState<QuestionPayload | null>(null)

    const categories = Object.keys(gameState.board)
    const values = [200, 400, 600, 800, 1000]

    async function openQuestion(category: string, value: number) {
        setLoading(true, 'Loading question...')
        try {
            const q = await api.getQuestion(gameId, category, value)
            setLoading(false)
            setActiveQ(q)
        } catch {
            setLoading(false)
        }
    }

    async function afterQuestion(gameOver: boolean) {
        setActiveQ(null)
        if (gameOver) {
            navigate('final')
            return
        }
        const gs = await api.getGame(gameId)
        setGameState(gs)
    }

    return (
        <div className="game-screen">
            {/* ── SCOREBOARD ── */}
            <div className="scoreboard">
                <div className="scores-row">
                    <div className="score-card is-player">
                        <div className="sc-name">{gameState.player.name}</div>
                        <div className="sc-score">${gameState.player.score.toLocaleString()}</div>
                    </div>
                    {gameState.bots.map(b => (
                        <div key={b.name} className="score-card">
                            <div className="sc-name">{b.name}</div>
                            <div className="sc-score">${b.score.toLocaleString()}</div>
                        </div>
                    ))}
                </div>
                <div style={{display: 'flex', alignItems: 'center', gap: '1rem'}}>
                    <div className="round-badge">Round {gameState.round} / 25</div>
                    <button
                        className="btn-ghost"
                        style={{width: 'auto', padding: '0.3rem 0.8rem', fontSize: '0.85rem'}}
                        onClick={() => {
                            localStorage.removeItem('activeGameId')
                            localStorage.removeItem('activeScreen')
                            navigate('setup')
                        }}
                    >
                        ✕ Quit
                    </button>
                </div>
            </div>

            {/* ── BOARD ── */}
            <div className="board-wrap">
                <div className="board">
                    {/* Category headers */}
                    {categories.map(cat => (
                        <div key={cat} className="board-cat-header">{cat}</div>
                    ))}
                    {/* Cells: row by row */}
                    {values.map(val =>
                        categories.map(cat => {
                            const cell = gameState.board[cat]?.[val]
                            const used = cell?.selected ?? true
                            return (
                                <div
                                    key={`${cat}-${val}`}
                                    className={`board-cell${used ? ' used' : ''}`}
                                    onClick={() => !used && openQuestion(cat, val)}
                                >
                                    <span className="cell-value">${val}</span>
                                </div>
                            )
                        })
                    )}
                </div>
            </div>

            {/* ── QUESTION MODAL ── */}
            {activeQ && !activeQ.is_daily_double && (
                <QuestionModal
                    gameId={gameId}
                    q={activeQ}
                    playerName={gameState.player.name}
                    playerScore={gameState.player.score}
                    onClose={({gameOver}) => afterQuestion(gameOver)}
                />
            )}

            {/* ── DAILY DOUBLE MODAL ── */}
            {activeQ && activeQ.is_daily_double && (
                <DailyDoubleModal
                    gameId={gameId}
                    category={activeQ.category}
                    value={activeQ.value}
                    question={activeQ.question}
                    answers={activeQ.answers}
                    playerScore={gameState.player.score}
                    onClose={(gameOver) => afterQuestion(gameOver)}
                />
            )}
        </div>
    )
}