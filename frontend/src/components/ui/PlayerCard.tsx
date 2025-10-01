import React from 'react';
import { Player } from '../../types';
import { StatusBadge } from './StatusBadge';

interface PlayerCardProps {
  player: Player;
  isCurrentPlayer?: boolean;
  isCurrentTurn?: boolean;
  showCurrentTurnIndicator?: boolean;
  className?: string;
}

export function PlayerCard({
  player,
  isCurrentPlayer = false,
  isCurrentTurn = false,
  showCurrentTurnIndicator = false,
  className = ''
}: PlayerCardProps) {
  const borderClass = isCurrentTurn ? 'border-blue-500 bg-blue-50' : 'border-gray-200';
  const nameClass = isCurrentPlayer ? 'text-blue-600' : '';

  return (
    <div className={`p-3 rounded border-2 ${borderClass} ${className}`}>
      <div className="flex items-center justify-between">
        <span className={`font-medium ${nameClass}`}>
          {player.name} {isCurrentPlayer && '(You)'}
        </span>
        <div className="flex items-center space-x-2">
          {player.isBot && (
            <StatusBadge variant="purple" size="sm">
              BOT
            </StatusBadge>
          )}
          <div className={`w-2 h-2 rounded-full ${player.isConnected ? 'bg-green-500' : 'bg-red-500'}`} />
        </div>
      </div>
      {showCurrentTurnIndicator && isCurrentTurn && (
        <div className="text-xs text-blue-600 mt-1">Current Turn</div>
      )}
    </div>
  );
}