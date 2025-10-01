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
    gameIdInput,
    playerCount,
    setPlayerName,
    setGameIdInput,
    setPlayerCount,
    createNewGame,
    joinExistingGame,
    startGame
  } = useGameContext();

  // If no game state, show the join form
  if (!gameState) {
    return (
      <LobbyForm
        playerName={playerName}
        gameIdInput={gameIdInput}
        isConnected={isConnected}
        onPlayerNameChange={setPlayerName}
        onGameIdInputChange={setGameIdInput}
        onCreateNewGame={createNewGame}
        onJoinExistingGame={joinExistingGame}
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