import React, { useState } from 'react';
import { GameState, GAME_STATUS, MESSAGE_TYPES } from '../../../types';
import { GameService } from '../../../services/gameService';
import { Button } from '../../ui/Button';

interface InputSectionProps {
  gameState: GameState;
  playerId: string;
  onAskQuestion: (content: string, target: string) => void;
  onGiveAnswer: (content: string) => void;
}

export function InputSection({
  gameState,
  playerId,
  onAskQuestion,
  onGiveAnswer
}: InputSectionProps) {
  const [currentQuestion, setCurrentQuestion] = useState('');
  const [selectedTarget, setSelectedTarget] = useState('');

  const isMyTurn = gameState.currentTurn === playerId;
  const otherPlayers = gameState.players.filter(p => p.id !== playerId);

  // Check if player has an unanswered question by finding the most recent question TO this player
  // and checking if there's an answer FROM this player after that question
  const waitingForAnswer = (() => {
    if (!gameState.lastQuestionedBy || !isMyTurn) return false;

    // Find the most recent question event to this player
    let lastQuestionIdx = -1;
    for (let i = gameState.events.length - 1; i >= 0; i--) {
      const event = gameState.events[i];
      if (event.type === 'question' && event.content?.to_id === playerId) {
        lastQuestionIdx = i;
        break;
      }
    }

    if (lastQuestionIdx === -1) return false;

    // Check if there's an answer from this player after that question
    for (let i = lastQuestionIdx + 1; i < gameState.events.length; i++) {
      const event = gameState.events[i];
      if (event.type === 'answer' && event.playerId === playerId) {
        return false; // Already answered
      }
    }

    return true; // Question found, no answer yet
  })();

  const lastEvent = gameState.events?.[gameState.events.length - 1];

  const getPlayerName = (playerId: string) => {
    return GameService.getPlayerName(gameState, playerId);
  };

  const sendQuestion = () => {
    if (currentQuestion.trim() && selectedTarget) {
      onAskQuestion(currentQuestion, selectedTarget);
      setCurrentQuestion('');
      setSelectedTarget('');
    }
  };

  const sendAnswer = () => {
    if (currentQuestion.trim()) {
      onGiveAnswer(currentQuestion);
      setCurrentQuestion('');
    }
  };

  if (gameState.status === GAME_STATUS.FINISHED) {
    return null;
  }

  return (
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
            You need to answer: {lastEvent?.content?.text}
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
            <Button
              variant="success"
              onClick={sendAnswer}
              disabled={!currentQuestion.trim()}
            >
              Answer
            </Button>
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
              <Button
                variant="primary"
                onClick={sendQuestion}
                disabled={!currentQuestion.trim() || !selectedTarget}
              >
                Ask
              </Button>
            </div>
          </div>
        </div>
      ) : (
        <div className="text-center text-gray-600">
          <p>It's <strong>{getPlayerName(gameState.currentTurn || '')}</strong>'s turn</p>
        </div>
      )}
    </div>
  );
}