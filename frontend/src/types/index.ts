export interface Player {
  id: string;
  name: string;
  isBot: boolean;
  isConnected: boolean;
}

export interface GameState {
  id: string;
  status: 'waiting' | 'in_progress' | 'finished';
  players: Player[];
  currentTurn?: string;
  timeRemaining?: number;
  location?: string;
  role?: string;
  isSpy: boolean;
}

export interface Message {
  id: string;
  type: 'question' | 'answer' | 'system';
  from: string;
  to?: string;
  content: string;
  timestamp: number;
}

export interface WebSocketMessage {
  type: 'join_game' | 'start_game' | 'send_message' | 'vote' | 'game_joined' | 'game_started' | 'message' | 'vote_cast' | 'player_left';
  game_id?: string;
  content?: string;
  target?: string;
  from?: string;
  players?: string[];
  voter?: string;
  player?: string;
  timestamp?: number;
}