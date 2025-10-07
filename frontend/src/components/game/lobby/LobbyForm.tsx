import React from 'react';
import { Button } from '../../ui/Button';
import { ConnectionStatus } from '../../ui/ConnectionStatus';

interface LobbyFormProps {
  playerName: string;
  isConnected: boolean;
  onPlayerNameChange: (name: string) => void;
  onCreateNewGame: () => void;
}

export function LobbyForm({
  playerName,
  isConnected,
  onPlayerNameChange,
  onCreateNewGame
}: LobbyFormProps) {
  return (
    <div className="max-w-md mx-auto bg-white rounded-lg shadow p-6">
      <h2 className="text-2xl font-bold mb-4">Create Game</h2>
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

        <Button
          variant="success"
          onClick={onCreateNewGame}
          disabled={!playerName || !isConnected}
          className="w-full"
        >
          Create New Game
        </Button>
      </div>
    </div>
  );
}