import React, { useState, useEffect, useCallback } from 'react';
import { GameState, WebSocketMessage, GAME_STATUS, MESSAGE_TYPES, GAME_CONSTANTS } from '../types';
import { useWebSocket } from '../hooks/useWebSocket';
import { GameService } from '../services/gameService';

interface GameBoardProps {
  gameState: GameState;
  playerId: string;
  playerName: string;
  onGameStateUpdate: (newState: GameState) => void;
}

const GameBoard: React.FC<GameBoardProps> = ({
  gameState,
  playerId,
  playerName,
  onGameStateUpdate
}) => {
  const [currentQuestion, setCurrentQuestion] = useState('');
  const [selectedTarget, setSelectedTarget] = useState('');
  const [showAccuseModal, setShowAccuseModal] = useState(false);
  const [accuseTarget, setAccuseTarget] = useState('');
  const [showSpyRevealModal, setShowSpyRevealModal] = useState(false);
  const [guessedLocation, setGuessedLocation] = useState('');

  const { sendMessage, lastMessage: wsMessage } = useWebSocket(
    `ws://localhost:${GAME_CONSTANTS.DEFAULT_PORT}/ws/${playerId}`
  );

  // Create game service instance
  const gameService = new GameService(sendMessage);

  // Handle WebSocket messages
  useEffect(() => {
    if (wsMessage) {
      const message: WebSocketMessage = JSON.parse(wsMessage.data);
      GameService.handleWebSocketMessage(message, {
        onGameState: onGameStateUpdate
      });
    }
  }, [wsMessage, onGameStateUpdate]);


  const sendQuestion = () => {
    if (currentQuestion.trim() && selectedTarget) {
      console.log('Sending question to:', selectedTarget);
      console.log('Current turn:', gameState.currentTurn, 'My ID:', playerId);
      gameService.askQuestion(gameState.id, currentQuestion, selectedTarget);
      setCurrentQuestion('');
      setSelectedTarget('');
    }
  };

  const sendAnswer = () => {
    if (currentQuestion.trim()) {
      gameService.giveAnswer(gameState.id, currentQuestion);
      setCurrentQuestion('');
    }
  };

  const handleAccuse = () => {
    if (accuseTarget) {
      gameService.accusePlayer(gameState.id, accuseTarget);
      setShowAccuseModal(false);
      setAccuseTarget('');
    }
  };

  const handleVote = (guilty: boolean) => {
    gameService.vote(gameState.id, guilty);
  };

  const handleSpyReveal = () => {
    if (guessedLocation.trim()) {
      gameService.spyGuessLocation(gameState.id, guessedLocation.trim());
      setShowSpyRevealModal(false);
      setGuessedLocation('');
    }
  };


  const isMyTurn = gameState.currentTurn === playerId;
  const otherPlayers = gameState.players.filter(p => p.id !== playerId);
  const lastChatMessage = gameState.messages[gameState.messages.length - 1];
  const waitingForAnswer = lastChatMessage?.type === MESSAGE_TYPES.QUESTION && lastChatMessage.to === playerId;
  const currentPlayer = gameState.players.find(p => p.id === playerId);
  const hasAlreadyAccused = currentPlayer?.hasAccusedThisRound || false;

  // Helper function to get player name from ID
  const getPlayerName = React.useCallback((playerId: string) => {
    return GameService.getPlayerName(gameState, playerId);
  }, [gameState]);

  // Helper function to get spy player name
  const getSpyName = React.useCallback(() => {
    // If I'm the spy, return "You"
    if (gameState.isSpy) {
      return "You";
    }
    // If game is finished and we have the spy ID, find the spy player
    if (gameState.status === GAME_STATUS.FINISHED && gameState.spyId) {
      const spyPlayer = gameState.players.find(p => p.id === gameState.spyId);
      return spyPlayer ? spyPlayer.name : "The spy";
    }
    return "The spy";
  }, [gameState]);

  return (
    <div className="max-w-6xl mx-auto bg-white rounded-lg shadow p-6">
      {/* Game Results (only shown when game is finished) */}
      {gameState.status === GAME_STATUS.FINISHED && (
        <div className="mb-6 bg-gray-100 rounded-lg p-6">
          <h2 className="text-2xl font-bold text-center mb-4">🎮 GAME OVER</h2>
          <div className="text-center">
            <div className={`inline-block px-6 py-3 rounded-lg text-xl font-bold ${
              gameState.winner === 'spy' ? 'bg-red-100 text-red-800' : 'bg-green-100 text-green-800'
            }`}>
              {gameState.winner === 'spy' ? `🕵️ ${getSpyName().toUpperCase()} WIN${gameState.isSpy ? '' : 'S'}!` : '👥 INNOCENTS WIN!'}
            </div>
            {gameState.endReason && (
              <p className="mt-3 text-gray-600">
                {gameState.endReason === 'spy_accused' && 'The spy was successfully identified!'}
                {gameState.endReason === 'innocent_accused' && 'An innocent player was wrongly accused!'}
                {gameState.endReason === 'time_expired' && 'Time ran out and no one was convicted!'}
                {gameState.endReason === 'spy_guessed_location' && 'The spy correctly guessed the location!'}
                {gameState.endReason === 'spy_failed_guess' && 'The spy failed to guess the location!'}
              </p>
            )}
          </div>
          <div className="mt-4 text-center">
            <p className="text-lg">
              <strong>Location:</strong> {gameState.location}
            </p>
          </div>
        </div>
      )}

      {/* Header with role and timer */}
      <div className="flex justify-between items-center mb-6">
        <div className="flex items-center space-x-4">
          <div className={`p-4 rounded-lg ${gameState.isSpy ? 'bg-spy-red text-white' : 'bg-innocent-blue text-white'}`}>
            <h3 className="text-lg font-bold">
              {gameState.isSpy ? '🕵️ SPY' : `📍 ${gameState.location || 'INNOCENT'}`}
            </h3>
            {!gameState.isSpy && gameState.role && (
              <p className="text-sm opacity-90">Role: {gameState.role}</p>
            )}
          </div>

          <div className="text-center">
            {gameState.status === GAME_STATUS.END_OF_ROUND_VOTING || gameState.status === GAME_STATUS.FINISHED ? (
              <>
                <div className="text-2xl font-bold text-orange-600">
                  End of Round
                </div>
                <div className="text-sm text-gray-500">Final Accusations</div>
              </>
            ) : (
              <>
                <div className="text-2xl font-bold text-blue-600">
                  Round {(gameState.qaRoundsCompleted || 0) + 1} / {gameState.maxQaRounds || 3}
                </div>
                <div className="text-sm text-gray-500">Q&A Rounds</div>
              </>
            )}</div>
        </div>


      </div>

      {/* Players list */}
      <div className="mb-6">
        <h3 className="text-lg font-semibold mb-3">Players ({gameState.players.length})</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
          {gameState.players.map((player) => (
            <div
              key={player.id}
              className={`p-3 rounded border-2 ${
                player.id === gameState.currentTurn ? 'border-blue-500 bg-blue-50' : 'border-gray-200'
              }`}
            >
              <div className="flex items-center justify-between">
                <span className={`font-medium ${player.id === playerId ? 'text-blue-600' : ''}`}>
                  {player.name} {player.id === playerId && '(You)'}
                </span>
                {player.isBot && (
                  <span className="px-1 py-0.5 text-xs bg-purple-100 text-purple-800 rounded">BOT</span>
                )}
              </div>
              {player.id === gameState.currentTurn && (
                <div className="text-xs text-blue-600 mt-1">Current Turn</div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Messages/Q&A History */}
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

      {/* Input Section */}
      <div className="bg-gray-50 rounded-lg p-4">
        {gameState.status === GAME_STATUS.VOTING ? (
          <div className="text-center text-gray-600">
            <p>🚨 Q&A paused during accusation voting</p>
          </div>
        ) : gameState.status === GAME_STATUS.END_OF_ROUND_VOTING ? (
          <div className="text-center text-gray-600">
            <p>⏰ Time's up! End-of-round accusation phase</p>
          </div>
        ) : waitingForAnswer ? (
          <div>
            <h4 className="font-semibold mb-2 text-orange-600">
              You need to answer: {lastChatMessage.content}
            </h4>
            <div className="flex space-x-2">
              <input
                type="text"
                value={currentQuestion}
                onChange={(e) => setCurrentQuestion(e.target.value)}
                placeholder="Type your answer..."
                className="flex-1 px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                onKeyPress={(e) => e.key === 'Enter' && sendAnswer()}
              />
              <button
                onClick={sendAnswer}
                disabled={!currentQuestion.trim()}
                className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 disabled:bg-gray-400"
              >
                Answer
              </button>
            </div>
          </div>
        ) : isMyTurn ? (
          <div>
            <h4 className="font-semibold mb-2 text-blue-600">Your turn to ask a question</h4>
            <div className="space-y-2">
              <select
                value={selectedTarget}
                onChange={(e) => setSelectedTarget(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">Select who to ask...</option>
                {otherPlayers.map((player) => (
                  <option
                    key={player.id}
                    value={player.id}
                    disabled={player.id === gameState.lastQuestionedBy}
                  >
                    {player.name} {player.isBot ? '(Bot)' : ''} {player.id === gameState.lastQuestionedBy ? '(just asked you)' : ''}
                  </option>
                ))}
              </select>
              <div className="flex space-x-2">
                <input
                  type="text"
                  value={currentQuestion}
                  onChange={(e) => setCurrentQuestion(e.target.value)}
                  placeholder="What's your question?"
                  className="flex-1 px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                  onKeyPress={(e) => e.key === 'Enter' && sendQuestion()}
                />
                <button
                  onClick={sendQuestion}
                  disabled={!currentQuestion.trim() || !selectedTarget}
                  className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:bg-gray-400"
                >
                  Ask
                </button>
              </div>
            </div>
          </div>
        ) : gameState.status === GAME_STATUS.FINISHED ? (
          <div className="text-center text-gray-600">
            <p>Game has ended</p>
          </div>
        ) : (
          <div className="text-center text-gray-600">
            <p>It's <strong>{getPlayerName(gameState.currentTurn || '')}</strong>'s turn</p>
          </div>
        )}
      </div>

      {/* Voting Section (shown during voting phases) */}
      {(gameState.status === GAME_STATUS.VOTING || gameState.status === GAME_STATUS.END_OF_ROUND_VOTING) && gameState.currentAccusation && (
        <div className={`mt-6 rounded-lg p-6 ${
          gameState.status === GAME_STATUS.END_OF_ROUND_VOTING
            ? 'bg-orange-50 border border-orange-200'
            : 'bg-red-50 border border-red-200'
        }`}>
          <h3 className={`text-xl font-bold mb-4 ${
            gameState.status === GAME_STATUS.END_OF_ROUND_VOTING
              ? 'text-orange-700'
              : 'text-red-700'
          }`}>
            {gameState.status === GAME_STATUS.END_OF_ROUND_VOTING ? '⏰ END OF ROUND ACCUSATION' : '🚨 ACCUSATION MADE'}
          </h3>
          <p className="text-gray-700 mb-4">
            <strong>{getPlayerName(gameState.currentAccusation.accuser)}</strong> has accused{' '}
            <strong>{getPlayerName(gameState.currentAccusation.accused)}</strong> of being the spy!
          </p>

          {playerId === gameState.currentAccusation.accused ? (
            <div className="text-center">
              <p className="text-lg font-semibold text-red-600 mb-2">You have been accused!</p>
              <p className="text-gray-600">You cannot vote. Wait for the others to decide your fate...</p>
            </div>
          ) : gameState.currentAccusation.votes[playerId] !== undefined ? (
            <div className="text-center">
              <p className="text-lg font-semibold text-green-600 mb-2">You voted: {gameState.currentAccusation.votes[playerId] ? 'GUILTY' : 'INNOCENT'}</p>
              <p className="text-gray-600">Waiting for other players to vote...</p>
            </div>
          ) : (
            <div className="text-center">
              <p className="text-lg font-semibold mb-4">Cast your vote:</p>
              <div className="flex justify-center space-x-4">
                <button
                  onClick={() => handleVote(true)}
                  className="px-8 py-3 bg-red-600 text-white rounded-lg hover:bg-red-700 font-semibold"
                >
                  GUILTY (Spy)
                </button>
                <button
                  onClick={() => handleVote(false)}
                  className="px-8 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 font-semibold"
                >
                  INNOCENT
                </button>
              </div>
            </div>
          )}

          {/* Vote Status */}
          <div className="mt-4 pt-4 border-t border-red-200">
            <p className="text-sm text-gray-600 text-center">
              Votes cast: {Object.keys(gameState.currentAccusation.votes).length} / {gameState.players.length - 1}
              {Object.keys(gameState.currentAccusation.votes).length === gameState.players.length - 1 && (
                <span className="block mt-1 font-semibold">All votes received! Resolving...</span>
              )}
            </p>
          </div>
        </div>
      )}

      {/* End-of-Round Accusation Making (when no current accusation) */}
      {gameState.status === GAME_STATUS.END_OF_ROUND_VOTING && !gameState.currentAccusation && (
        <div className="mt-6 bg-orange-50 border border-orange-200 rounded-lg p-6">
          <h3 className="text-xl font-bold text-orange-700 mb-4">⏰ END OF ROUND ACCUSATION</h3>
          <div className="text-center">
            {isMyTurn ? (
              <>
                <p className="text-lg font-semibold mb-4 text-orange-600">It's your turn to make an accusation!</p>
                <button
                  onClick={() => setShowAccuseModal(true)}
                  className="px-6 py-3 bg-orange-600 text-white rounded-lg hover:bg-orange-700 font-semibold"
                >
                  Make Accusation
                </button>
              </>
            ) : (
              <p className="text-gray-600">
                Waiting for <strong>{getPlayerName(gameState.currentTurn || '')}</strong> to make an accusation...
              </p>
            )}
          </div>
        </div>
      )}

      {/* Action Buttons (accusation available during normal gameplay, regardless of turn) */}
      {gameState.status === GAME_STATUS.IN_PROGRESS && (
        <div className="mt-4 flex justify-center space-x-4">
          <button
            onClick={() => setShowAccuseModal(true)}
            disabled={hasAlreadyAccused}
            className={`px-6 py-2 rounded ${
              hasAlreadyAccused
                ? 'bg-gray-400 text-gray-700 cursor-not-allowed'
                : 'bg-red-600 text-white hover:bg-red-700'
            }`}
            title={hasAlreadyAccused ? 'You have already made an accusation this round' : ''}
          >
            🚨 {hasAlreadyAccused ? 'Already Accused' : 'Accuse Player'}
          </button>

          {/* Spy Reveal Button - only shown to spies during active gameplay */}
          {gameState.isSpy && (
            <button
              onClick={() => setShowSpyRevealModal(true)}
              className="px-6 py-2 bg-purple-600 text-white rounded hover:bg-purple-700"
              title="Reveal your identity and guess the location to win"
            >
              🎭 Reveal & Guess Location
            </button>
          )}
        </div>
      )}

      {/* Accusation Modal */}
      {showAccuseModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
            <h3 className="text-xl font-bold mb-4 text-red-600">🚨 Accuse Player</h3>
            <p className="text-gray-600 mb-4">
              Who do you think is the spy? This will immediately stop the clock and start a voting phase.
            </p>

            <select
              value={accuseTarget}
              onChange={(e) => setAccuseTarget(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-red-500 mb-4"
            >
              <option value="">Select player to accuse...</option>
              {otherPlayers.map((player) => (
                <option key={player.id} value={player.id}>
                  {player.name} {player.isBot ? '(Bot)' : ''}
                </option>
              ))}
            </select>

            <div className="flex space-x-3">
              <button
                onClick={handleAccuse}
                disabled={!accuseTarget}
                className="flex-1 px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 disabled:bg-gray-400"
              >
                Accuse
              </button>
              <button
                onClick={() => {
                  setShowAccuseModal(false);
                  setAccuseTarget('');
                }}
                className="flex-1 px-4 py-2 bg-gray-500 text-white rounded hover:bg-gray-600"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Spy Reveal Modal */}
      {showSpyRevealModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
            <h3 className="text-xl font-bold mb-4 text-purple-600">🎭 Reveal Your Identity</h3>
            <p className="text-gray-600 mb-4">
              As the spy, you can reveal your identity and guess the location to win the game.
              If you guess correctly, you win! If you guess incorrectly, the innocents win.
            </p>

            <select
              value={guessedLocation}
              onChange={(e) => setGuessedLocation(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-purple-500 mb-4"
            >
              <option value="">Select a location...</option>
              {gameState.availableLocations?.map((location) => (
                <option key={location} value={location}>
                  {location}
                </option>
              ))}
            </select>

            <div className="flex space-x-3">
              <button
                onClick={handleSpyReveal}
                disabled={!guessedLocation}
                className="flex-1 px-4 py-2 bg-purple-600 text-white rounded hover:bg-purple-700 disabled:bg-gray-400"
              >
                Reveal & Guess
              </button>
              <button
                onClick={() => {
                  setShowSpyRevealModal(false);
                  setGuessedLocation('');
                }}
                className="flex-1 px-4 py-2 bg-gray-500 text-white rounded hover:bg-gray-600"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default GameBoard;
