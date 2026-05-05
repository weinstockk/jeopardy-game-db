import {useState, useEffect} from 'react'
import SetupScreen from '../screens/SetupScreen'
import GameScreen from '../screens/GameScreen'
import FinalScreen from '../screens/FinalScreen'
import GameOverScreen from '../screens/GameOverScreen'
import LoadingOverlay from '../components/LoadingOverlay'
import './App.css'
import {api} from "./api.ts";

export type Screen = 'setup' | 'game' | 'final' | 'gameover'

export interface GameState {
    game_id: string
    round: number
    player: { name: string; score: number }
    bots: { name: string; score: number; difficulty: string }[]
    board: Record<string, Record<number, { selected: boolean; is_daily_double: boolean }>>
    remaining: number
}

export interface AppState {
    screen: Screen
    gameId: string | null
    gameState: GameState | null
    loading: boolean
    loadingMsg: string
}

export default function App() {
    const [appState, setAppState] = useState<AppState>({
        screen: 'setup',
        gameId: null,
        gameState: null,
        loading: false,
        loadingMsg: 'Loading...',
    })

    useEffect(() => {
    const savedId = localStorage.getItem('activeGameId')
    const savedScreen = localStorage.getItem('activeScreen') as Screen | null
    if (!savedId) return

    setAppState(s => ({ ...s, loading: true, loadingMsg: 'Restoring game...' }))

    api.getGame(savedId)
        .then(gs => {
            const shouldBeFinal = savedScreen === 'final' || gs.remaining === 0
            setAppState({
                screen: shouldBeFinal ? 'final' : 'game',
                gameId: savedId,
                gameState: gs,
                loading: false,
                loadingMsg: '',
            })
            if (shouldBeFinal) {
                localStorage.setItem('activeScreen', 'final')
            }
        })
        .catch(() => {
            localStorage.removeItem('activeGameId')
            localStorage.removeItem('activeScreen')
            setAppState(s => ({ ...s, loading: false }))
        })
}, [])

    const setLoading = (loading: boolean, msg = 'Loading...') =>
        setAppState(s => ({...s, loading, loadingMsg: msg}))

    const navigate = (screen: Screen, extra?: Partial<AppState>) => {
        setAppState(s => ({ ...s, screen, ...extra }))
        if (screen === 'final' || screen === 'game') {
            localStorage.setItem('activeScreen', screen)
        } else {
            localStorage.removeItem('activeScreen')
        }
}

    return (
        <div className="app">
            {appState.loading && <LoadingOverlay msg={appState.loadingMsg}/>}

            {appState.screen === 'setup' && (
                <SetupScreen
                    setLoading={setLoading}
                    navigate={navigate}
                    setAppState={setAppState}
                />
            )}
            {appState.screen === 'game' && appState.gameId && appState.gameState && (
                <GameScreen
                    gameId={appState.gameId}
                    gameState={appState.gameState}
                    setGameState={(gs) => setAppState(s => ({...s, gameState: gs}))}
                    setLoading={setLoading}
                    navigate={navigate}
                />
            )}
            {appState.screen === 'final' && appState.gameId && appState.gameState && (
                <FinalScreen
                    gameId={appState.gameId}
                    gameState={appState.gameState}
                    setLoading={setLoading}
                    navigate={navigate}
                />
            )}
            {appState.screen === 'gameover' && appState.gameState && (
                <GameOverScreen
                    gameState={appState.gameState}
                    navigate={navigate}
                    setAppState={setAppState}
                />
            )}
        </div>
    )
}