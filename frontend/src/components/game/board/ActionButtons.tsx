import React from 'react';
import { GameState, GAME_STATUS } from '../../../types';
import { Button } from '../../ui/Button';

interface ActionButtonsProps {
  gameState: GameState;
  onAccuse: () => void;
  onSpyReveal: () => void;
  hasAlreadyAccused: boolean;
}

export function ActionButtons({
  gameState,
  onAccuse,
  onSpyReveal,
  hasAlreadyAccused
}: ActionButtonsProps) {
  if (gameState.status !== GAME_STATUS.IN_PROGRESS) {
    return null;
  }

  return (
    <div className="mt-4 flex justify-center space-x-4">
      <Button
        variant="danger"
        onClick={onAccuse}
        disabled={hasAlreadyAccused}
        title={hasAlreadyAccused ? 'You have already made an accusation this round' : ''}
      >
        🚨 {hasAlreadyAccused ? 'Already Accused' : 'Accuse Player'}
      </Button>

      {/* Spy Reveal Button - only shown to spies during active gameplay */}
      {gameState.isSpy && (
        <Button
          variant="warning"
          onClick={onSpyReveal}
          className="bg-purple-600 hover:bg-purple-700 focus:ring-purple-500"
          title="Reveal your identity and guess the location to win"
        >
          🎭 Reveal & Guess Location
        </Button>
      )}
    </div>
  );
}