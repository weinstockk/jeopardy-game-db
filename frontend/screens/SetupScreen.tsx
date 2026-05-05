import {useState} from 'react'
import {api} from '../src/api'
import type {AppState, Screen} from '../src/App'

type View = 'home' | 'load' | 'history'

interface Props {
    setLoading: (v: boolean, msg?: string) => void
    navigate: (screen: Screen, extra?: Partial<AppState>) => void
    setAppState: React.Dispatch<React.SetStateAction<AppState>>
}

export default function SetupScreen({setLoading, setAppState}: Props) {
    const [view, setView] = useState<View>('home')
    const [name, setName] = useState('')
    const [diff, setDiff] = useState<'easy' | 'medium' | 'hard'>('easy')
    const [error, setError] = useState('')
    const [activeGames, setActiveGames] = useState<{
        game_id: string;
        player_name: string;
        round: number;
        remaining: number
    }[]>([])
    const [history, setHistory] = useState<{
        game_id: string;
        player: { name: string; score: number };
        bots: { name: string; score: number }[];
        winner: { name: string; score: number };
        completed_at: number
    }[]>([])

    async function startGame() {
        if (!name.trim()) {
            setError('Please enter your name.');
            return
        }
        setError('')
        setLoading(true, 'Fetching questions...')
        try {
            const result = await api.newGame(name.trim(), diff)
            localStorage.setItem('activeGameId', result.game_id)
            const gs = await api.getGame(result.game_id)
            setAppState(s => ({...s, gameId: result.game_id, gameState: gs, screen: 'game', loading: false}))
            localStorage.setItem('activeScreen', 'game')
        } catch (e: unknown) {
            setLoading(false)
            setError(e instanceof Error ? e.message : 'Could not connect to server.')
        }
    }

    async function loadGames() {
        setLoading(true, 'Fetching active games...')
        try {
            const games = await api.activeGames()
            setActiveGames(games)
            setLoading(false)
            setView('load')
        } catch {
            setLoading(false)
            setError('Could not load games.')
        }
    }

    async function loadHistory() {
        setLoading(true, 'Loading history...')
        try {
            const h = await api.history()
            setHistory(h)
            setLoading(false)
            setView('history')
        } catch {
            setLoading(false)
            setView('history')
        }
    }

    async function resumeGame(gameId: string) {
        setLoading(true, 'Loading game...')
        try {
            const gs = await api.getGame(gameId)
            localStorage.setItem('activeGameId', gameId)
            localStorage.setItem('activeScreen', 'game')
            setAppState(s => ({...s, gameId, gameState: gs, screen: 'game', loading: false}))
        } catch {
            setLoading(false)
        }
    }

    return (
        <div className="setup-screen">
            <div className="setup-inner">
                <div>
                    <div className="logo">JEOPARDY!</div>
                    <p className="logo-sub">The Classic Trivia Game</p>
                </div>

                {view === 'home' && (
                    <div className="card">
                        <h2>Start New Game</h2>
                        <div className="form-group">
                            <label>Your Name</label>
                            <input
                                type="text"
                                value={name}
                                onChange={e => setName(e.target.value)}
                                onKeyDown={e => e.key === 'Enter' && startGame()}
                                placeholder="Enter your name"
                                maxLength={20}
                            />
                        </div>
                        <div className="form-group">
                            <label>AI Difficulty</label>
                            <div className="diff-row">
                                {(['easy', 'medium', 'hard'] as const).map(d => (
                                    <button key={d} className={`diff-btn${diff === d ? ' active' : ''}`}
                                            onClick={() => setDiff(d)}>
                                        {d.charAt(0).toUpperCase() + d.slice(1)}
                                    </button>
                                ))}
                            </div>
                        </div>
                        <div className="btn-stack">
                            <button className="btn-primary" onClick={startGame}>Start Game</button>
                            <button className="btn-ghost" onClick={loadGames}>Resume Game</button>
                            <button className="btn-ghost" onClick={loadHistory}>View History</button>
                        </div>
                        {error && <p className="error-msg">{error}</p>}
                    </div>
                )}

                {view === 'load' && (
                    <div className="card">
                        <h2>Resume Game</h2>
                        {activeGames.length === 0
                            ? <p className="no-items">No active games found.</p>
                            : activeGames.map(g => (
                                <div key={g.game_id} className="game-item">
                                    <div className="game-item-info">
                                        <div className="gi-name">{g.player_name}</div>
                                        <div className="gi-sub">Round {g.round} · {g.remaining} questions left</div>
                                    </div>
                                    <button className="btn-primary btn-sm"
                                            onClick={() => resumeGame(g.game_id)}>Resume
                                    </button>
                                </div>
                            ))
                        }
                        <button className="btn-ghost" style={{marginTop: '1rem'}} onClick={() => setView('home')}>←
                            Back
                        </button>
                    </div>
                )}

                {view === 'history' && (
                    <div className="card">
                        <h2>History</h2>
                        {history.length === 0
                            ? <p className="no-items">No completed games yet.</p>
                            : history.map(g => {
                                const date = g.completed_at ? new Date(g.completed_at * 1000).toLocaleDateString() : ''
                                const scores = [g.player, ...(g.bots || [])].sort((a, b) => b.score - a.score)
                                    .map(p => `${p.name}: $${p.score.toLocaleString()}`).join(' · ')
                                return (
                                    <div key={g.game_id} className="game-item" style={{display: 'block'}}>
                                        <div className="gi-name">🏆 {g.winner.name} won</div>
                                        <div className="gi-sub">{scores}</div>
                                        {date && <div className="gi-sub"
                                                      style={{color: '#555', marginTop: '0.1rem'}}>{date}</div>}
                                    </div>
                                )
                            })
                        }
                        <button className="btn-ghost" style={{marginTop: '1rem'}} onClick={() => setView('home')}>←
                            Back
                        </button>
                    </div>
                )}
            </div>
        </div>
    )
}