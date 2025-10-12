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

  // Convert markdown bold syntax to HTML
  const formatMarkdown = (text: string): string => {
    // Replace **text** with <strong>text</strong>
    return text.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  };

  return (
    <div className="mb-6">
      <h3 className="text-lg font-semibold mb-3">Game Events</h3>
      <div className="bg-gray-50 rounded-lg p-4 h-64 overflow-y-auto">
        {!gameState.events || gameState.events.length === 0 ? (
          <div className="text-center text-gray-500 py-8">
            No events yet. The game begins now!
          </div>
        ) : (
          <div className="space-y-3">
            {gameState.events.map((event, index) => (
              <div key={`${event.playerId}-${event.timestamp}-${index}`} className="bg-white p-3 rounded shadow-sm">
                <div className="flex justify-between items-start mb-1">
                  <span className="text-xs text-gray-500">
                    {new Date(event.timestamp * 1000).toLocaleTimeString()}
                  </span>
                </div>
                <div
                  className="text-gray-700"
                  dangerouslySetInnerHTML={{ __html: formatMarkdown(event.formattedText) }}
                />
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}