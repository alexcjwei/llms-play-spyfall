import React from 'react';
import { GameState, GAME_STATUS } from '../../../types';
import { GameService } from '../../../services/gameService';
import { Button } from '../../ui/Button';

interface VotingSectionProps {
  gameState: GameState;
  playerId: string;
  onVote: (guilty: boolean) => void;
  onAccuse: () => void;
}

export function VotingSection({
  gameState,
  playerId,
  onVote,
  onAccuse
}: VotingSectionProps) {
  const getPlayerName = (playerId: string) => {
    return GameService.getPlayerName(gameState, playerId);
  };

  const isMyTurn = gameState.currentTurn === playerId;

  // Regular voting section during active accusation
  if ((gameState.status === GAME_STATUS.VOTING || gameState.status === GAME_STATUS.END_OF_ROUND_VOTING) && gameState.currentAccusation) {
    return (
      <div className={`mt-6 rounded-lg p-6 ${
        gameState.status === GAME_STATUS.END_OF_ROUND_VOTING
          ? 'bg-orange-50 border border-orange-200'
          : 'bg-red-50 border border-red-200'
      }`}>
        <h3 className={`text-xl font-bold mb-4 ${
          gameState.status === GAME_STATUS.END_OF_ROUND_VOTING
            ? 'text-orange-700'
            : 'text-red-700'
        }`}>
          {gameState.status === GAME_STATUS.END_OF_ROUND_VOTING ? '⏰ END OF ROUND ACCUSATION' : '🚨 ACCUSATION MADE'}
        </h3>
        <p className="text-gray-700 mb-4">
          <strong>{getPlayerName(gameState.currentAccusation.accuser)}</strong> has accused{' '}
          <strong>{getPlayerName(gameState.currentAccusation.accused)}</strong> of being the spy!
        </p>

        {playerId === gameState.currentAccusation.accused ? (
          <div className="text-center">
            <p className="text-lg font-semibold text-red-600 mb-2">You have been accused!</p>
            <p className="text-gray-600">You cannot vote. Wait for the others to decide your fate...</p>
          </div>
        ) : gameState.currentAccusation.votes[playerId] !== undefined ? (
          <div className="text-center">
            <p className="text-lg font-semibold text-green-600 mb-2">
              You voted: {gameState.currentAccusation.votes[playerId] ? 'GUILTY' : 'INNOCENT'}
            </p>
            <p className="text-gray-600">Waiting for other players to vote...</p>
          </div>
        ) : (
          <div className="text-center">
            <p className="text-lg font-semibold mb-4">Cast your vote:</p>
            <div className="flex justify-center space-x-4">
              <Button
                variant="danger"
                onClick={() => onVote(true)}
                size="lg"
              >
                GUILTY (Spy)
              </Button>
              <Button
                variant="success"
                onClick={() => onVote(false)}
                size="lg"
              >
                INNOCENT
              </Button>
            </div>
          </div>
        )}

        {/* Vote Status */}
        <div className="mt-4 pt-4 border-t border-red-200">
          <p className="text-sm text-gray-600 text-center">
            Votes cast: {Object.keys(gameState.currentAccusation.votes).length} / {gameState.players.length - 1}
            {Object.keys(gameState.currentAccusation.votes).length === gameState.players.length - 1 && (
              <span className="block mt-1 font-semibold">All votes received! Resolving...</span>
            )}
          </p>
        </div>
      </div>
    );
  }

  // End-of-Round Accusation Making (when no current accusation)
  if (gameState.status === GAME_STATUS.END_OF_ROUND_VOTING && !gameState.currentAccusation) {
    return (
      <div className="mt-6 bg-orange-50 border border-orange-200 rounded-lg p-6">
        <h3 className="text-xl font-bold text-orange-700 mb-4">⏰ END OF ROUND ACCUSATION</h3>
        <div className="text-center">
          {isMyTurn ? (
            <>
              <p className="text-lg font-semibold mb-4 text-orange-600">It's your turn to make an accusation!</p>
              <Button
                variant="warning"
                onClick={onAccuse}
                size="lg"
              >
                Make Accusation
              </Button>
            </>
          ) : (
            <p className="text-gray-600">
              Waiting for <strong>{getPlayerName(gameState.currentTurn || '')}</strong> to make an accusation...
            </p>
          )}
        </div>
      </div>
    );
  }

  return null;
}