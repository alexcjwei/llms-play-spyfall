// Game constants
export const GAME_CONSTANTS = {
  MAX_PLAYERS: 8,
  MIN_PLAYERS: 3,
  DEFAULT_QA_ROUNDS: 3,
  GAME_ID_LENGTH: 6,
  DEFAULT_PORT: 8000,
  DEFAULT_BOT_DELAY: 2000, // ms
} as const;

export const GAME_STATUS = {
  WAITING: 'waiting',
  IN_PROGRESS: 'in_progress',
  VOTING: 'voting',
  END_OF_ROUND_VOTING: 'end_of_round_voting',
  FINISHED: 'finished',
} as const;

export const MESSAGE_TYPES = {
  QUESTION: 'question',
  ANSWER: 'answer',
} as const;

export interface Player {
  id: string;
  name: string;
  isBot: boolean;
  isConnected: boolean;
  points?: number;
  hasAccusedThisRound?: boolean;
}

export type GameStatusType = typeof GAME_STATUS[keyof typeof GAME_STATUS];
export type MessageType = typeof MESSAGE_TYPES[keyof typeof MESSAGE_TYPES];

export interface GameState {
  id: string;
  status: GameStatusType;
  players: Player[];
  currentTurn?: string;
  location?: string;
  role?: string;
  isSpy: boolean;
  availableLocations?: string[];
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
  spyId?: string;
}

export interface Message {
  id: string;
  type: MessageType;
  from: string;
  to?: string;
  content: string;
  timestamp: number;
}


// WebSocket message types
export type ClientMessageType =
  | 'join_game'
  | 'start_game'
  | 'ask_question'
  | 'give_answer'
  | 'vote'
  | 'accuse_player'
  | 'spy_guess_location';

export type ServerMessageType =
  | 'game_state'
  | 'join_success'
  | 'rejoin_success'
  | 'join_error'
  | 'start_error'
  | 'game_started'
  | 'player_left'
  | 'player_disconnected'
  | 'question_error'
  | 'answer_error'
  | 'accusation_made'
  | 'accusation_error'
  | 'end_of_round_accusation_made'
  | 'spy_revealed'
  | 'spy_guess_error';

// Base message interface
interface BaseMessage {
  type: ClientMessageType | ServerMessageType;
  game_id?: string;
  timestamp?: number;
}

// Client message interfaces
export interface JoinGameMessage extends BaseMessage {
  type: 'join_game';
  game_id: string;
  player_name: string;
  is_bot?: boolean;
}

export interface StartGameMessage extends BaseMessage {
  type: 'start_game';
  game_id: string;
  player_count?: number;
}

export interface AskQuestionMessage extends BaseMessage {
  type: 'ask_question';
  game_id: string;
  content: string;
  target: string;
}

export interface GiveAnswerMessage extends BaseMessage {
  type: 'give_answer';
  game_id: string;
  content: string;
}

export interface VoteMessage extends BaseMessage {
  type: 'vote';
  game_id: string;
  vote: boolean;
}

export interface AccusePlayerMessage extends BaseMessage {
  type: 'accuse_player';
  game_id: string;
  target: string;
}

export interface SpyGuessLocationMessage extends BaseMessage {
  type: 'spy_guess_location';
  game_id: string;
  location: string;
}

// Server message interfaces
export interface GameStateMessage extends BaseMessage {
  type: 'game_state';
  data: GameState;
}

export interface JoinSuccessMessage extends BaseMessage {
  type: 'join_success' | 'rejoin_success';
  game_id: string;
  player_id: string;
}

export interface ErrorMessage extends BaseMessage {
  type: 'join_error' | 'start_error' | 'question_error' | 'answer_error' | 'accusation_error' | 'spy_guess_error';
  message: string;
}

export interface GameStartedMessage extends BaseMessage {
  type: 'game_started';
  game_id: string;
}

export interface PlayerStatusMessage extends BaseMessage {
  type: 'player_left' | 'player_disconnected';
  player_id: string;
  player_name?: string;
}

export interface AccusationMadeMessage extends BaseMessage {
  type: 'accusation_made' | 'end_of_round_accusation_made';
  accuser: string;
  accused: string;
  game_id: string;
}

export interface SpyRevealedMessage extends BaseMessage {
  type: 'spy_revealed';
  spy: string;
  guessed_location: string;
  actual_location: string;
  correct: boolean;
  game_id: string;
}

// Union type for all possible messages
export type WebSocketMessage =
  | JoinGameMessage
  | StartGameMessage
  | AskQuestionMessage
  | GiveAnswerMessage
  | VoteMessage
  | AccusePlayerMessage
  | SpyGuessLocationMessage
  | GameStateMessage
  | JoinSuccessMessage
  | ErrorMessage
  | GameStartedMessage
  | PlayerStatusMessage
  | AccusationMadeMessage
  | SpyRevealedMessage;