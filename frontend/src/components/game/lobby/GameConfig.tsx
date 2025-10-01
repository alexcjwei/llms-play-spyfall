import React from 'react';
import { GAME_CONSTANTS } from '../../../types';

interface GameConfigProps {
  playerCount: number;
  currentPlayers: number;
  onPlayerCountChange: (count: number) => void;
}

export function GameConfig({
  playerCount,
  currentPlayers,
  onPlayerCountChange
}: GameConfigProps) {
  const playerOptions = [];
  for (let i = GAME_CONSTANTS.MIN_PLAYERS; i <= GAME_CONSTANTS.MAX_PLAYERS; i++) {
    playerOptions.push(i);
  }

  return (
    <div className="p-4 bg-blue-50 rounded-lg">
      <h4 className="text-md font-medium mb-3">Game Configuration</h4>
      <div className="space-y-3">
        <div>
          <label htmlFor="playerCount" className="block text-sm font-medium text-gray-700 mb-1">
            Total Players (including you)
          </label>
          <select
            id="playerCount"
            value={playerCount}
            onChange={(e) => onPlayerCountChange(parseInt(e.target.value))}
            className="block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
          >
            {playerOptions.map(count => (
              <option key={count} value={count}>
                {count} Players ({count - 1} bots)
              </option>
            ))}
          </select>
        </div>
        <div className="text-xs text-gray-600">
          {playerCount - currentPlayers} bot(s) will be added when the game starts
        </div>
      </div>
    </div>
  );
}