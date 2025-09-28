import React, { useState, useEffect } from 'react';
import { GameState, WebSocketMessage } from '../types';
import { useWebSocket } from '../hooks/useWebSocket';
import GameBoard from './GameBoard';

const GameLobby: React.FC = () => {
  const [gameState, setGameState] = useState<GameState | null>(null);
  const [playerName, setPlayerName] = useState('');
  const [playerId, setPlayerId] = useState('');
  const [isConnected, setIsConnected] = useState(false);
  const [gameIdInput, setGameIdInput] = useState('');

  // Generate a unique player ID
  useEffect(() => {
    if (!playerId) {
      setPlayerId(`player_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`);
    }
  }, [playerId]);

  const { sendMessage, lastMessage, connectionStatus } = useWebSocket(
    playerId ? `ws://localhost:8000/ws/${playerId}` : null
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
    console.log('Received message:', message);
    switch (message.type) {
      case 'join_success':
      case 'rejoin_success':
        console.log('Successfully joined/rejoined game:', message.game_id);
        break;
      case 'join_error':
        console.error('Failed to join game:', message.message);
        break;
      case 'game_state':
        if (message.data) {
          console.log('Game state update:', message.data);
          setGameState(message.data);
        }
        break;
      case 'game_started':
        console.log('Game started');
        break;
      case 'start_error':
        console.error('Failed to start game:', message.message);
        break;
      case 'question_error':
        console.error('Question error:', message.message);
        break;
      case 'answer_error':
        console.error('Answer error:', message.message);
        break;
      case 'player_left':
      case 'player_disconnected':
        console.log('Player left/disconnected:', message.player_id);
        break;
      default:
        console.log('Unhandled message type:', message.type);
    }
  };

  const generateGameId = () => {
    const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';
    let result = '';
    for (let i = 0; i < 6; i++) {
      result += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    return result;
  };

  const createNewGame = () => {
    if (playerName && isConnected && playerId) {
      const newGameId = generateGameId();
      const message: WebSocketMessage = {
        type: 'join_game',
        game_id: newGameId,
        player_name: playerName
      };
      sendMessage(JSON.stringify(message));
    }
  };

  const joinExistingGame = () => {
    if (playerName && gameIdInput && isConnected && playerId) {
      const message: WebSocketMessage = {
        type: 'join_game',
        game_id: gameIdInput,
        player_name: playerName
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

  const leaveGame = () => {
    setGameState(null);
    setGameIdInput('');
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
          <div className="border-t pt-4">
            <button
              onClick={createNewGame}
              disabled={!playerName || !isConnected}
              className="w-full bg-green-600 text-white py-2 px-4 rounded-md hover:bg-green-700 disabled:bg-gray-400 disabled:cursor-not-allowed mb-3"
            >
              Create New Game
            </button>

            <div className="text-center text-gray-500 mb-3">or</div>

            <div>
              <input
                type="text"
                value={gameIdInput}
                onChange={(e) => setGameIdInput(e.target.value.toUpperCase())}
                className="w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 mb-2"
                placeholder="Enter Game ID (e.g. ABC123)"
                maxLength={6}
              />
              <button
                onClick={joinExistingGame}
                disabled={!playerName || !gameIdInput || !isConnected}
                className="w-full bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
              >
                Join Game
              </button>
            </div>
          </div>
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
        <GameBoard
          gameState={gameState}
          playerId={playerId}
          playerName={playerName}
          onLeaveGame={leaveGame}
          onGameStateUpdate={setGameState}
        />
      )}
    </div>
  );
};

export default GameLobby;