import React, { useState, useEffect } from 'react';
import { GameState, WebSocketMessage } from '../types';
import { useWebSocket } from '../hooks/useWebSocket';

const GameLobby: React.FC = () => {
  const [gameState, setGameState] = useState<GameState | null>(null);
  const [playerName, setPlayerName] = useState('');
  const [isConnected, setIsConnected] = useState(false);

  const { sendMessage, lastMessage, connectionStatus } = useWebSocket(
    'ws://localhost:8000/ws/' + (playerName || 'anonymous')
  );

  useEffect(() => {
    setIsConnected(connectionStatus === 'Open');
  }, [connectionStatus]);

  useEffect(() => {
    if (lastMessage) {
      const message: WebSocketMessage = JSON.parse(lastMessage.data);
      handleWebSocketMessage(message);
    }
  }, [lastMessage]);

  const handleWebSocketMessage = (message: WebSocketMessage) => {
    switch (message.type) {
      case 'game_joined':
        setGameState(prev => ({
          ...prev,
          id: message.game_id || 'default',
          status: 'waiting',
          players: (message.players || []).map(id => ({
            id,
            name: id,
            isBot: id.includes('bot'),
            isConnected: true
          })),
          isSpy: false
        } as GameState));
        break;
      case 'game_started':
        setGameState(prev => prev ? { ...prev, status: 'in_progress' } : null);
        break;
      case 'player_left':
        setGameState(prev => prev ? {
          ...prev,
          players: prev.players.filter(p => p.id !== message.player)
        } : null);
        break;
      default:
        console.log('Unhandled message type:', message.type);
    }
  };

  const joinGame = () => {
    if (playerName && isConnected) {
      const message: WebSocketMessage = {
        type: 'join_game',
        game_id: 'default'
      };
      sendMessage(JSON.stringify(message));
    }
  };

  const startGame = () => {
    if (gameState && isConnected) {
      const message: WebSocketMessage = {
        type: 'start_game',
        game_id: gameState.id
      };
      sendMessage(JSON.stringify(message));
    }
  };

  if (!gameState) {
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
              onChange={(e) => setPlayerName(e.target.value)}
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
              placeholder="Enter your name"
            />
          </div>
          <div className="flex items-center space-x-2">
            <div className={`w-3 h-3 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`}></div>
            <span className="text-sm text-gray-600">
              {isConnected ? 'Connected' : 'Disconnected'}
            </span>
          </div>
          <button
            onClick={joinGame}
            disabled={!playerName || !isConnected}
            className="w-full bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
          >
            Join Game
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto bg-white rounded-lg shadow p-6">
      <h2 className="text-2xl font-bold mb-4">Game Lobby</h2>

      <div className="mb-6">
        <h3 className="text-lg font-semibold mb-2">Players ({gameState.players.length})</h3>
        <div className="space-y-2">
          {gameState.players.map((player) => (
            <div key={player.id} className="flex items-center justify-between p-2 bg-gray-50 rounded">
              <span className="font-medium">{player.name}</span>
              <div className="flex items-center space-x-2">
                {player.isBot && (
                  <span className="px-2 py-1 text-xs bg-purple-100 text-purple-800 rounded">BOT</span>
                )}
                <div className={`w-2 h-2 rounded-full ${player.isConnected ? 'bg-green-500' : 'bg-red-500'}`}></div>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="mb-4">
        <div className={`p-3 rounded ${
          gameState.status === 'waiting' ? 'bg-yellow-100 text-yellow-800' :
          gameState.status === 'in_progress' ? 'bg-green-100 text-green-800' :
          'bg-gray-100 text-gray-800'
        }`}>
          Status: {gameState.status.toUpperCase()}
        </div>
      </div>

      {gameState.status === 'waiting' && (
        <button
          onClick={startGame}
          className="w-full bg-green-600 text-white py-2 px-4 rounded-md hover:bg-green-700"
        >
          Start Game
        </button>
      )}

      {gameState.status === 'in_progress' && (
        <div className="text-center">
          <p className="text-lg text-gray-600">Game in progress...</p>
          <p className="text-sm text-gray-500 mt-2">Game components will be implemented next</p>
        </div>
      )}
    </div>
  );
};

export default GameLobby;