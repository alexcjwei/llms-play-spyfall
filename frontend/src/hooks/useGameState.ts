import { useMemo } from 'react';
import { GameState, MESSAGE_TYPES } from '../types';
import { GameService } from '../services/gameService';

/**
 * Hook that provides computed values and derived state from the game state
 */
export function useGameState(gameState: GameState | null, playerId: string) {
  return useMemo(() => {
    if (!gameState) {
      return {
        isMyTurn: false,
        otherPlayers: [],
        currentPlayer: null,
        waitingForAnswer: false,
        lastMessage: null,
        hasAlreadyAccused: false,
        getPlayerName: (id: string) => id,
        isGameActive: false,
        canMakeAccusation: false,
        canRevealSpy: false,
      };
    }

    const isMyTurn = gameState.currentTurn === playerId;
    const otherPlayers = gameState.players.filter(p => p.id !== playerId);
    const currentPlayer = gameState.players.find(p => p.id === playerId) || null;
    const lastEvent = gameState.events?.[gameState.events.length - 1] || null;
    const waitingForAnswer = lastEvent?.type === MESSAGE_TYPES.QUESTION && lastEvent.content?.to_id === playerId;
    const hasAlreadyAccused = currentPlayer?.hasAccusedThisRound || false;

    const getPlayerName = (id: string) => GameService.getPlayerName(gameState, id);

    const isGameActive = gameState.status === 'in_progress';
    const canMakeAccusation = isGameActive && !hasAlreadyAccused;
    const canRevealSpy = isGameActive && gameState.isSpy;

    return {
      isMyTurn,
      otherPlayers,
      currentPlayer,
      waitingForAnswer,
      lastMessage: lastEvent,
      hasAlreadyAccused,
      getPlayerName,
      isGameActive,
      canMakeAccusation,
      canRevealSpy,
    };
  }, [gameState, playerId]);
}