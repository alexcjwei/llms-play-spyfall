import {
  WebSocketMessage,
  GameState,
  JoinGameMessage,
  StartGameMessage,
  AskQuestionMessage,
  GiveAnswerMessage,
  VoteMessage,
  AccusePlayerMessage,
  SpyGuessLocationMessage,
  GAME_CONSTANTS
} from '../types';

export class GameService {
  private sendMessage: (message: string) => void;

  constructor(sendMessage: (message: string) => void) {
    this.sendMessage = sendMessage;
  }

  // Game management actions
  joinGame(gameId: string, playerName: string): void {
    const message: JoinGameMessage = {
      type: 'join_game',
      game_id: gameId,
      player_name: playerName
    };
    this.sendMessage(JSON.stringify(message));
  }

  startGame(gameId: string): void {
    const message: StartGameMessage = {
      type: 'start_game',
      game_id: gameId
    };
    this.sendMessage(JSON.stringify(message));
  }

  // Gameplay actions
  askQuestion(gameId: string, content: string, target: string): void {
    const message: AskQuestionMessage = {
      type: 'ask_question',
      game_id: gameId,
      content: content.trim(),
      target
    };
    this.sendMessage(JSON.stringify(message));
  }

  giveAnswer(gameId: string, content: string): void {
    const message: GiveAnswerMessage = {
      type: 'give_answer',
      game_id: gameId,
      content: content.trim()
    };
    this.sendMessage(JSON.stringify(message));
  }

  vote(gameId: string, guilty: boolean): void {
    const message: VoteMessage = {
      type: 'vote',
      game_id: gameId,
      vote: guilty
    };
    this.sendMessage(JSON.stringify(message));
  }

  accusePlayer(gameId: string, target: string): void {
    const message: AccusePlayerMessage = {
      type: 'accuse_player',
      game_id: gameId,
      target
    };
    this.sendMessage(JSON.stringify(message));
  }

  spyGuessLocation(gameId: string, location: string): void {
    const message: SpyGuessLocationMessage = {
      type: 'spy_guess_location',
      game_id: gameId,
      location: location.trim()
    };
    this.sendMessage(JSON.stringify(message));
  }

  // Utility functions
  static generateGameId(): string {
    const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';
    let result = '';
    for (let i = 0; i < GAME_CONSTANTS.GAME_ID_LENGTH; i++) {
      result += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    return result;
  }

  static getPlayerName(gameState: GameState, playerId: string): string {
    const player = gameState.players.find(p => p.id === playerId);
    return player ? player.name : playerId;
  }

  // Message handling helper
  static handleWebSocketMessage(
    message: WebSocketMessage,
    callbacks: {
      onGameState?: (state: GameState) => void;
      onJoinSuccess?: (gameId: string, playerId: string) => void;
      onError?: (error: string) => void;
      onGameStarted?: (gameId: string) => void;
      onPlayerDisconnected?: (playerId: string, playerName?: string) => void;
      onAccusationMade?: (accuser: string, accused: string) => void;
      onSpyRevealed?: (spy: string, guessedLocation: string, actualLocation: string, correct: boolean) => void;
    }
  ): void {
    console.log('Received message:', message);

    switch (message.type) {
      case 'join_success':
      case 'rejoin_success':
        console.log('Successfully joined/rejoined game:', message.game_id);
        if (callbacks.onJoinSuccess && message.game_id && message.player_id) {
          callbacks.onJoinSuccess(message.game_id, message.player_id);
        }
        break;

      case 'join_error':
      case 'start_error':
      case 'question_error':
      case 'answer_error':
      case 'accusation_error':
      case 'spy_guess_error':
        console.error('Error:', message.message);
        if (callbacks.onError && message.message) {
          callbacks.onError(message.message);
        }
        break;

      case 'game_state':
        console.log('Game state update:', message.data);
        if (callbacks.onGameState && message.data) {
          callbacks.onGameState(message.data);
        }
        break;

      case 'game_started':
        console.log('Game started');
        if (callbacks.onGameStarted && message.game_id) {
          callbacks.onGameStarted(message.game_id);
        }
        break;

      case 'player_left':
      case 'player_disconnected':
        console.log('Player left/disconnected:', message.player_id);
        if (callbacks.onPlayerDisconnected && message.player_id) {
          callbacks.onPlayerDisconnected(message.player_id, message.player_name);
        }
        break;

      case 'accusation_made':
      case 'end_of_round_accusation_made':
        console.log('Accusation made:', message.accuser, 'vs', message.accused);
        if (callbacks.onAccusationMade && message.accuser && message.accused) {
          callbacks.onAccusationMade(message.accuser, message.accused);
        }
        break;

      case 'spy_revealed':
        console.log('Spy revealed:', message.spy, 'guessed:', message.guessed_location, 'actual:', message.actual_location, 'correct:', message.correct);
        if (callbacks.onSpyRevealed && message.spy && message.guessed_location && message.actual_location !== undefined) {
          callbacks.onSpyRevealed(message.spy, message.guessed_location, message.actual_location, message.correct);
        }
        break;

      default:
        console.log('Unhandled message type:', message.type);
    }
  }
}