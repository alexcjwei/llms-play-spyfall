export interface Player {
  id: string;
  name: string;
  isBot: boolean;
  isConnected: boolean;
  points?: number;
}

export interface GameState {
  id: string;
  status: 'waiting' | 'in_progress' | 'voting' | 'finished';
  players: Player[];
  currentTurn?: string;
  location?: string;
  role?: string;
  isSpy: boolean;
  messages: Message[];
  clockStopped: boolean;
  lastQuestionedBy?: string;
  qaRoundsCompleted?: number;
  maxQaRounds?: number;
  currentAccusation?: {
    accuser: string;
    accused: string;
    votes: Record<string, boolean>;
  };
  winner?: string;
  endReason?: string;
}

export interface Message {
  id: string;
  type: 'question' | 'answer';
  from: string;
  to?: string;
  content: string;
  timestamp: number;
}


export interface WebSocketMessage {
  type: 'join_game' | 'start_game' | 'ask_question' | 'give_answer' | 'vote' | 'accuse_player' | 'game_state' | 'join_success' | 'rejoin_success' | 'join_error' | 'start_error' | 'game_started' | 'player_left' | 'player_disconnected' | 'question_error' | 'answer_error' | 'accusation_made' | 'accusation_error';
  game_id?: string;
  player_name?: string;
  is_bot?: boolean;
  content?: string;
  target?: string;
  from?: string;
  data?: GameState;
  message?: string;
  player_id?: string;
  player_name_left?: string;
  timestamp?: number;
  vote?: boolean;
}