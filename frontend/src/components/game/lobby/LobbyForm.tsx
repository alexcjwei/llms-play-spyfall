import React from 'react';
import { GAME_CONSTANTS } from '../../../types';
import { Button } from '../../ui/Button';
import { ConnectionStatus } from '../../ui/ConnectionStatus';

interface LobbyFormProps {
  playerName: string;
  gameIdInput: string;
  isConnected: boolean;
  onPlayerNameChange: (name: string) => void;
  onGameIdInputChange: (id: string) => void;
  onCreateNewGame: () => void;
  onJoinExistingGame: () => void;
}

export function LobbyForm({
  playerName,
  gameIdInput,
  isConnected,
  onPlayerNameChange,
  onGameIdInputChange,
  onCreateNewGame,
  onJoinExistingGame
}: LobbyFormProps) {
  return (
    <div className="max-w-md mx-auto bg-white rounded-lg shadow p-6">
      <h2 className="text-2xl font-bold mb-4">Join Game</h2>
      <div className="space-y-4">
        <div>
          <label htmlFor="playerName" className="block text-sm font-medium text-gray-700">
            Your Name
          </label>
          <input
            type="text"
            id="playerName"
            value={playerName}
            onChange={(e) => onPlayerNameChange(e.target.value)}
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
            placeholder="Enter your name"
          />
        </div>

        <ConnectionStatus isConnected={isConnected} />

        <div className="border-t pt-4">
          <Button
            variant="success"
            onClick={onCreateNewGame}
            disabled={!playerName || !isConnected}
            className="w-full mb-3"
          >
            Create New Game
          </Button>

          <div className="text-center text-gray-500 mb-3">or</div>

          <div>
            <input
              type="text"
              value={gameIdInput}
              onChange={(e) => onGameIdInputChange(e.target.value.toUpperCase())}
              className="w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 mb-2"
              placeholder="Enter Game ID (e.g. ABC123)"
              maxLength={GAME_CONSTANTS.GAME_ID_LENGTH}
            />
            <Button
              variant="primary"
              onClick={onJoinExistingGame}
              disabled={!playerName || !gameIdInput || !isConnected}
              className="w-full"
            >
              Join Game
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}