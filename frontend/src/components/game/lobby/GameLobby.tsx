import React from 'react';
import { GAME_STATUS } from '../../../types';
import { useGameContext } from '../../../context/GameContext';
import { Button } from '../../ui/Button';
import { StatusBadge } from '../../ui/StatusBadge';
import { LobbyForm } from './LobbyForm';
import { PlayersList } from './PlayersList';
import { GameConfig } from './GameConfig';
import GameBoard from '../board/GameBoard';

export function GameLobby() {
  const {
    gameState,
    playerName,
    playerId,
    isConnected,
    playerCount,
    setPlayerName,
    setPlayerCount,
    createNewGame,
    startGame
  } = useGameContext();

  // If no game state, show the create form
  if (!gameState) {
    return (
      <LobbyForm
        playerName={playerName}
        isConnected={isConnected}
        onPlayerNameChange={setPlayerName}
        onCreateNewGame={createNewGame}
      />
    );
  }

  // If game is in progress, show the game board
  if (gameState.status === GAME_STATUS.IN_PROGRESS ||
      gameState.status === GAME_STATUS.VOTING ||
      gameState.status === GAME_STATUS.END_OF_ROUND_VOTING ||
      gameState.status === GAME_STATUS.FINISHED) {
    return <GameBoard />;
  }

  // Show the lobby interface
  return (
    <div className="max-w-2xl mx-auto bg-white rounded-lg shadow p-6">
      <h2 className="text-2xl font-bold mb-4">Game Lobby</h2>

      <PlayersList
        players={gameState.players}
        currentPlayerId={playerId}
        className="mb-6"
      />

      {gameState.status === GAME_STATUS.WAITING && (
        <GameConfig
          playerCount={playerCount}
          currentPlayers={gameState.players.length}
          onPlayerCountChange={setPlayerCount}
        />
      )}

      <div className="mb-6 p-4 bg-green-50 rounded-lg">
        <h4 className="text-md font-medium mb-3">Game Locations</h4>
        <div>
          <label htmlFor="locationsList" className="block text-sm font-medium text-gray-700 mb-1">
            Available Locations ({gameState.availableLocations?.length || 0})
          </label>
          <select
            id="locationsList"
            className="block w-full rounded-md border-gray-300 shadow-sm bg-gray-50 text-gray-700 cursor-pointer"
            defaultValue=""
          >
            <option value="" disabled>Browse locations...</option>
            {(gameState.availableLocations || []).map(location => (
              <option key={location} value={location}>
                {location}
              </option>
            ))}
          </select>
          <div className="text-xs text-gray-600 mt-1">
            One location will be randomly selected for the game
          </div>
        </div>
      </div>

      <div className="mb-4 mt-6">
        <StatusBadge
          variant={gameState.status === GAME_STATUS.WAITING ? 'yellow' : 'gray'}
          size="md"
          className="w-full text-center p-3 rounded"
        >
          Status: {gameState.status.toUpperCase()}
        </StatusBadge>
      </div>

      {gameState.status === GAME_STATUS.WAITING && (
        <Button
          variant="success"
          onClick={startGame}
          className="w-full"
        >
          Start Game
        </Button>
      )}
    </div>
  );
}