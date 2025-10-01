import React from 'react';
import { GameState, GAME_STATUS } from '../../../types';

interface GameResultsProps {
  gameState: GameState;
}

export function GameResults({ gameState }: GameResultsProps) {
  if (gameState.status !== GAME_STATUS.FINISHED) {
    return null;
  }

  const getSpyName = () => {
    // If I'm the spy, return "You"
    if (gameState.isSpy) {
      return "You";
    }
    // If game is finished and we have the spy ID, find the spy player
    if (gameState.spyId) {
      const spyPlayer = gameState.players.find(p => p.id === gameState.spyId);
      return spyPlayer ? spyPlayer.name : "The spy";
    }
    return "The spy";
  };

  const getEndReasonText = () => {
    switch (gameState.endReason) {
      case 'spy_accused':
        return 'The spy was successfully identified!';
      case 'innocent_accused':
        return 'An innocent player was wrongly accused!';
      case 'time_expired':
        return 'Time ran out and no one was convicted!';
      case 'spy_guessed_location':
        return 'The spy correctly guessed the location!';
      case 'spy_failed_guess':
        return 'The spy failed to guess the location!';
      default:
        return '';
    }
  };

  return (
    <div className="mb-6 bg-gray-100 rounded-lg p-6">
      <h2 className="text-2xl font-bold text-center mb-4">🎮 GAME OVER</h2>
      <div className="text-center">
        <div className={`inline-block px-6 py-3 rounded-lg text-xl font-bold ${
          gameState.winner === 'spy' ? 'bg-red-100 text-red-800' : 'bg-green-100 text-green-800'
        }`}>
          {gameState.winner === 'spy'
            ? `🕵️ ${getSpyName().toUpperCase()} WIN${gameState.isSpy ? '' : 'S'}!`
            : '👥 INNOCENTS WIN!'
          }
        </div>
        {gameState.endReason && (
          <p className="mt-3 text-gray-600">
            {getEndReasonText()}
          </p>
        )}
      </div>
      <div className="mt-4 text-center">
        <p className="text-lg">
          <strong>Location:</strong> {gameState.location}
        </p>
      </div>
    </div>
  );
}