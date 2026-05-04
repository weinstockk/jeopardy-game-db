const API = 'http://localhost:8000'

async function req<T>(path: string, method = 'GET', body?: unknown): Promise<T> {
    const res = await fetch(`${API}${path}`, {
        method,
        headers: body ? {'Content-Type': 'application/json'} : {},
        body: body ? JSON.stringify(body) : undefined,
    })
    if (!res.ok) {
        const err = await res.json().catch(() => ({detail: 'Request failed'}))
        throw new Error(err.detail ?? 'Request failed')
    }
    return res.json()
}

export const api = {
    newGame: (player_name: string, ai_difficulty: string) =>
        req<{ game_id: string; player: string; ai_1: string; ai_2: string }>('/api/new-game', 'POST', {
            player_name,
            ai_difficulty
        }),

    getGame: (gameId: string) =>
        req<import('../src/App').GameState>(`/api/game/${gameId}`),

    activeGames: () =>
        req<{
            game_id: string;
            player_name: string;
            round: number;
            remaining: number;
            created_at: string
        }[]>('/api/active-games'),

    history: () =>
        req<{
            game_id: string; player: { name: string; score: number };
            bots: { name: string; score: number }[];
            winner: { name: string; score: number };
            completed_at: number
        }[]>('/api/history'),

    getQuestion: (gameId: string, category: string, value: number) =>
        req<{
            question: string; answers: string[]; correct_answer: string;
            value: number; category: string; is_daily_double: boolean;
            bot_buzz_times: Record<string, number>
        }>(`/api/question/${gameId}`, 'POST', {category, value}),

    submitAnswer: (gameId: string, category: string, value: number, answer: string, player_buzz_time: number, bot_buzz_times: Record<string, number>) =>
        req<{
            player_buzzed_first: boolean; player_correct: boolean; correct_answer: string;
            results: {
                name: string;
                display_name: string;
                is_player: boolean;
                answer: string;
                correct: boolean;
                buzz_time: number
            }[];
            all_buzz_times: { name: string; buzz_time: number; is_player: boolean }[];
            round_winner: string | null; remaining: number; game_over: boolean
        }>(`/api/answer/${gameId}`, 'POST', {category, value, answer, player_buzz_time, bot_buzz_times}),

    submitPlayerAnswer: (gameId: string, category: string, value: number, answer: string) =>
        req<{
            correct_answer: string; round_winner: string | null;
            results: {
                name: string;
                display_name: string;
                is_player: boolean;
                answer: string;
                correct: boolean;
                buzz_time: number
            }[];
            game_over: boolean
        }>(`/api/player-answer/${gameId}`, 'POST', {category, value, answer}),

    dailyDouble: (gameId: string, category: string, value: number, wager: number, answer: string) =>
        req<{
            player_correct: boolean;
            correct_answer: string;
            wager: number;
            delta: number;
            remaining: number;
            game_over: boolean
        }>(
            `/api/daily-double/${gameId}`, 'POST', {category, value, wager, answer}
        ),

    getFinal: (gameId: string) =>
        req<{ question: string; answers: string[]; status: string; player_score: number }>(`/api/final/${gameId}`),

    submitFinal: (gameId: string, wager: number, answer: string) =>
        req<{
            correct_answer: string;
            reveal: {
                name: string;
                is_player: boolean;
                correct: boolean;
                wager: number;
                delta: number;
                answer: string
            }[]
        }>(`/api/final/${gameId}`, 'POST', {wager, answer}),

    endGame: (gameId: string) =>
        req<{
            winner: { name: string; score: number };
            all_scores: { name: string; score: number }[]
        }>(`/api/end-game/${gameId}`, 'POST'),
}