import React, { useState, useEffect } from 'react';
import { GameState, WebSocketMessage, GAME_CONSTANTS, GAME_STATUS } from '../types';
import { useWebSocket } from '../hooks/useWebSocket';
import { GameService } from '../services/gameService';
import GameBoard from './GameBoard';

const GameLobby: React.FC = () => {
  const [gameState, setGameState] = useState<GameState | null>(null);
  const [playerName, setPlayerName] = useState('');
  const [playerId, setPlayerId] = useState('');
  const [isConnected, setIsConnected] = useState(false);
  const [gameIdInput, setGameIdInput] = useState('');
  const [playerCount, setPlayerCount] = useState(3);

  // Generate a unique player ID
  useEffect(() => {
    if (!playerId) {
      setPlayerId(`player_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`);
    }
  }, [playerId]);

  const { sendMessage, lastMessage, connectionStatus } = useWebSocket(
    playerId ? `ws://localhost:${GAME_CONSTANTS.DEFAULT_PORT}/ws/${playerId}` : null
  );

  // Create game service instance
  const gameService = new GameService(sendMessage);

  useEffect(() => {
    setIsConnected(connectionStatus === 'Open');
  }, [connectionStatus]);

  useEffect(() => {
    if (lastMessage) {
      const message: WebSocketMessage = JSON.parse(lastMessage.data);
      GameService.handleWebSocketMessage(message, {
        onGameState: setGameState,
        onJoinSuccess: (gameId, playerId) => {
          console.log('Successfully joined/rejoined game:', gameId);
        },
        onError: (error) => {
          console.error('Game error:', error);
        },
        onGameStarted: (gameId) => {
          console.log('Game started:', gameId);
        },
        onPlayerDisconnected: (playerId, playerName) => {
          console.log('Player disconnected:', playerId, playerName);
        }
      });
    }
  }, [lastMessage]);


  const createNewGame = () => {
    if (playerName && isConnected && playerId) {
      const newGameId = GameService.generateGameId();
      gameService.joinGame(newGameId, playerName);
    }
  };

  const joinExistingGame = () => {
    if (playerName && gameIdInput && isConnected && playerId) {
      console.log('Attempting to join game:', gameIdInput, 'as player:', playerName);
      gameService.joinGame(gameIdInput, playerName);
    } else {
      console.log('Join conditions not met:', { playerName, gameIdInput, isConnected, playerId });
    }
  };

  const startGame = () => {
    if (gameState && isConnected) {
      gameService.startGame(gameState.id, playerCount);
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
                maxLength={GAME_CONSTANTS.GAME_ID_LENGTH}
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

      {gameState.status === GAME_STATUS.WAITING && (
        <div className="mb-6 p-4 bg-blue-50 rounded-lg">
          <h4 className="text-md font-medium mb-3">Game Configuration</h4>
          <div className="space-y-3">
            <div>
              <label htmlFor="playerCount" className="block text-sm font-medium text-gray-700 mb-1">
                Total Players (including you)
              </label>
              <select
                id="playerCount"
                value={playerCount}
                onChange={(e) => setPlayerCount(parseInt(e.target.value))}
                className="block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
              >
                <option value={3}>3 Players (2 bots)</option>
                <option value={4}>4 Players (3 bots)</option>
                <option value={5}>5 Players (4 bots)</option>
                <option value={6}>6 Players (5 bots)</option>
                <option value={7}>7 Players (6 bots)</option>
                <option value={8}>8 Players (7 bots)</option>
              </select>
            </div>
            <div className="text-xs text-gray-600">
              {playerCount - gameState.players.length} bot(s) will be added when the game starts
            </div>
          </div>
        </div>
      )}

      <div className="mb-4">
        <div className={`p-3 rounded ${
          gameState.status === GAME_STATUS.WAITING ? 'bg-yellow-100 text-yellow-800' :
          gameState.status === GAME_STATUS.IN_PROGRESS ? 'bg-green-100 text-green-800' :
          'bg-gray-100 text-gray-800'
        }`}>
          Status: {gameState.status.toUpperCase()}
        </div>
      </div>

      {gameState.status === GAME_STATUS.WAITING && (
        <button
          onClick={startGame}
          className="w-full bg-green-600 text-white py-2 px-4 rounded-md hover:bg-green-700"
        >
          Start Game
        </button>
      )}

      {(gameState.status === GAME_STATUS.IN_PROGRESS ||
        gameState.status === GAME_STATUS.VOTING ||
        gameState.status === GAME_STATUS.END_OF_ROUND_VOTING ||
        gameState.status === GAME_STATUS.FINISHED) && (
        <GameBoard
          gameState={gameState}
          playerId={playerId}
          playerName={playerName}
          onGameStateUpdate={setGameState}
        />
      )}
    </div>
  );
};

export default GameLobby;