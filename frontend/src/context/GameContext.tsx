import React, { createContext, useContext, useReducer, useEffect, useCallback, ReactNode } from 'react';
import { GameState, WebSocketMessage, GAME_CONSTANTS } from '../types';
import { useWebSocket } from '../hooks/useWebSocket';
import { GameService } from '../services/gameService';

interface GameContextState {
  gameState: GameState | null;
  playerName: string;
  playerId: string;
  isConnected: boolean;
  error: string | null;
  gameIdInput: string;
  playerCount: number;
}

interface GameContextActions {
  setPlayerName: (name: string) => void;
  setGameIdInput: (id: string) => void;
  setPlayerCount: (count: number) => void;
  createNewGame: () => void;
  joinExistingGame: () => void;
  startGame: () => void;
  askQuestion: (content: string, target: string) => void;
  giveAnswer: (content: string) => void;
  accusePlayer: (target: string) => void;
  vote: (guilty: boolean) => void;
  spyGuessLocation: (location: string) => void;
  clearError: () => void;
}

type GameContextValue = GameContextState & GameContextActions;

const GameContext = createContext<GameContextValue | null>(null);

type GameAction =
  | { type: 'SET_GAME_STATE'; payload: GameState }
  | { type: 'SET_PLAYER_NAME'; payload: string }
  | { type: 'SET_GAME_ID_INPUT'; payload: string }
  | { type: 'SET_PLAYER_COUNT'; payload: number }
  | { type: 'SET_CONNECTION_STATUS'; payload: boolean }
  | { type: 'SET_ERROR'; payload: string }
  | { type: 'CLEAR_ERROR' };

const initialState: GameContextState = {
  gameState: null,
  playerName: '',
  playerId: '',
  isConnected: false,
  error: null,
  gameIdInput: '',
  playerCount: 3,
};

function gameReducer(state: GameContextState, action: GameAction): GameContextState {
  switch (action.type) {
    case 'SET_GAME_STATE':
      return { ...state, gameState: action.payload };
    case 'SET_PLAYER_NAME':
      return { ...state, playerName: action.payload };
    case 'SET_GAME_ID_INPUT':
      return { ...state, gameIdInput: action.payload.toUpperCase() };
    case 'SET_PLAYER_COUNT':
      return { ...state, playerCount: action.payload };
    case 'SET_CONNECTION_STATUS':
      return { ...state, isConnected: action.payload };
    case 'SET_ERROR':
      return { ...state, error: action.payload };
    case 'CLEAR_ERROR':
      return { ...state, error: null };
    default:
      return state;
  }
}

function generatePlayerId(): string {
  return `player_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}

interface GameProviderProps {
  children: ReactNode;
}

export function GameProvider({ children }: GameProviderProps) {
  const [state, dispatch] = useReducer(gameReducer, {
    ...initialState,
    playerId: generatePlayerId(),
  });

  const { sendMessage, lastMessage, connectionStatus } = useWebSocket(
    state.playerId ? `ws://localhost:${GAME_CONSTANTS.DEFAULT_PORT}/ws/${state.playerId}` : null
  );

  const gameService = React.useMemo(() => new GameService(sendMessage), [sendMessage]);

  // Update connection status
  useEffect(() => {
    dispatch({ type: 'SET_CONNECTION_STATUS', payload: connectionStatus === 'Open' });
  }, [connectionStatus]);

  // Handle WebSocket messages
  useEffect(() => {
    if (lastMessage) {
      const message: WebSocketMessage = JSON.parse(lastMessage.data);
      GameService.handleWebSocketMessage(message, {
        onGameState: (gameState) => {
          dispatch({ type: 'SET_GAME_STATE', payload: gameState });
        },
        onJoinSuccess: (gameId, playerId) => {
          console.log('Successfully joined/rejoined game:', gameId);
          dispatch({ type: 'CLEAR_ERROR' });
        },
        onError: (error) => {
          console.error('Game error:', error);
          dispatch({ type: 'SET_ERROR', payload: error });
        },
        onGameStarted: (gameId) => {
          console.log('Game started:', gameId);
        },
        onPlayerDisconnected: (playerId, playerName) => {
          console.log('Player disconnected:', playerId, playerName);
        },
        onSpyRevealed: (spy, guessedLocation, actualLocation, correct) => {
          console.log('Spy revealed:', spy, 'guessed:', guessedLocation, 'actual:', actualLocation, 'correct:', correct);
          // The game state update will be sent separately by the backend
        }
      });
    }
  }, [lastMessage]);

  // Actions
  const setPlayerName = useCallback((name: string) => {
    dispatch({ type: 'SET_PLAYER_NAME', payload: name });
  }, []);

  const setGameIdInput = useCallback((id: string) => {
    dispatch({ type: 'SET_GAME_ID_INPUT', payload: id });
  }, []);

  const setPlayerCount = useCallback((count: number) => {
    dispatch({ type: 'SET_PLAYER_COUNT', payload: count });
  }, []);

  const createNewGame = useCallback(() => {
    if (state.playerName && state.isConnected && state.playerId) {
      const newGameId = GameService.generateGameId();
      gameService.joinGame(newGameId, state.playerName);
    }
  }, [state.playerName, state.isConnected, state.playerId, gameService]);

  const joinExistingGame = useCallback(() => {
    if (state.playerName && state.gameIdInput && state.isConnected && state.playerId) {
      console.log('Attempting to join game:', state.gameIdInput, 'as player:', state.playerName);
      gameService.joinGame(state.gameIdInput, state.playerName);
    } else {
      console.log('Join conditions not met:', {
        playerName: state.playerName,
        gameIdInput: state.gameIdInput,
        isConnected: state.isConnected,
        playerId: state.playerId
      });
    }
  }, [state.playerName, state.gameIdInput, state.isConnected, state.playerId, gameService]);

  const startGame = useCallback(() => {
    if (state.gameState && state.isConnected) {
      gameService.startGame(state.gameState.id, state.playerCount);
    }
  }, [state.gameState, state.isConnected, state.playerCount, gameService]);

  const askQuestion = useCallback((content: string, target: string) => {
    if (state.gameState && content.trim() && target) {
      gameService.askQuestion(state.gameState.id, content, target);
    }
  }, [state.gameState, gameService]);

  const giveAnswer = useCallback((content: string) => {
    if (state.gameState && content.trim()) {
      gameService.giveAnswer(state.gameState.id, content);
    }
  }, [state.gameState, gameService]);

  const accusePlayer = useCallback((target: string) => {
    if (state.gameState && target) {
      gameService.accusePlayer(state.gameState.id, target);
    }
  }, [state.gameState, gameService]);

  const vote = useCallback((guilty: boolean) => {
    if (state.gameState) {
      gameService.vote(state.gameState.id, guilty);
    }
  }, [state.gameState, gameService]);

  const spyGuessLocation = useCallback((location: string) => {
    if (state.gameState && location.trim()) {
      gameService.spyGuessLocation(state.gameState.id, location.trim());
    }
  }, [state.gameState, gameService]);

  const clearError = useCallback(() => {
    dispatch({ type: 'CLEAR_ERROR' });
  }, []);

  const contextValue: GameContextValue = {
    ...state,
    setPlayerName,
    setGameIdInput,
    setPlayerCount,
    createNewGame,
    joinExistingGame,
    startGame,
    askQuestion,
    giveAnswer,
    accusePlayer,
    vote,
    spyGuessLocation,
    clearError,
  };

  return (
    <GameContext.Provider value={contextValue}>
      {children}
    </GameContext.Provider>
  );
}

export function useGameContext(): GameContextValue {
  const context = useContext(GameContext);
  if (!context) {
    throw new Error('useGameContext must be used within a GameProvider');
  }
  return context;
}