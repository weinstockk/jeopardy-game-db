import type {AppState, GameState, Screen} from '../src/App'

interface Props {
    gameState: GameState
    navigate: (screen: Screen, extra?: Partial<AppState>) => void
    setAppState: React.Dispatch<React.SetStateAction<AppState>>
}

export default function GameOverScreen({gameState, setAppState}: Props) {
    // The FinalScreen injects _winner and _allScores into gameState before navigating here
    const gs = gameState as GameState & {
        _winner?: { name: string; score: number };
        _allScores?: { name: string; score: number }[]
    }
    const winner = gs._winner
    const allScores = gs._allScores ?? []

    const isPlayerWinner = winner?.name === gameState.player.name

    function playAgain() {
        localStorage.removeItem('activeGameId')
        localStorage.removeItem('activeScreen')
        setAppState({
            screen: 'setup',
            gameId: null,
            gameState: null,
            loading: false,
            loadingMsg: 'Loading...',
        })
    }

    return (
        <div className="gameover-screen">
            <div className="gameover-inner">
                <h1 className="gameover-title">GAME OVER</h1>

                <div className="winner-box">
                    <div className="wl">{isPlayerWinner ? '🏆 You Win!' : 'Winner'}</div>
                    <div className="wn">{winner?.name ?? '—'}</div>
                    <div className="ws">${winner?.score?.toLocaleString() ?? 0}</div>
                </div>

                <div className="final-scores-list">
                    {[...allScores].sort((a, b) => b.score - a.score).map(p => (
                        <div key={p.name} className="fs-row">
                            <span>{p.name}{p.name === gameState.player.name ? ' (You)' : ''}</span>
                            <span className="fs-score">${p.score.toLocaleString()}</span>
                        </div>
                    ))}
                </div>

                <button className="btn-primary" style={{maxWidth: '300px'}} onClick={playAgain}>
                    Play Again
                </button>
            </div>
        </div>
    )
}