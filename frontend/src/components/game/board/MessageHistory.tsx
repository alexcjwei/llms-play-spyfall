import React from 'react';
import { GameState, MESSAGE_TYPES } from '../../../types';
import { GameService } from '../../../services/gameService';

interface MessageHistoryProps {
  gameState: GameState;
}

export function MessageHistory({ gameState }: MessageHistoryProps) {
  const getPlayerName = (playerId: string) => {
    return GameService.getPlayerName(gameState, playerId);
  };

  return (
    <div className="mb-6">
      <h3 className="text-lg font-semibold mb-3">Q&A History</h3>
      <div className="bg-gray-50 rounded-lg p-4 h-64 overflow-y-auto">
        {gameState.messages.length === 0 ? (
          <div className="text-center text-gray-500 py-8">
            No questions asked yet. The game begins now!
          </div>
        ) : (
          <div className="space-y-3">
            {gameState.messages.map((message) => (
              <div key={message.id} className="bg-white p-3 rounded shadow-sm">
                <div className="flex justify-between items-start mb-1">
                  <span className="font-medium text-gray-800">{getPlayerName(message.from)}</span>
                  <span className="text-xs text-gray-500">
                    {new Date(message.timestamp).toLocaleTimeString()}
                  </span>
                </div>
                {message.type === MESSAGE_TYPES.QUESTION && message.to && (
                  <div className="text-sm text-blue-600 mb-1">→ {getPlayerName(message.to)}</div>
                )}
                <div className="text-gray-700">{message.content}</div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}