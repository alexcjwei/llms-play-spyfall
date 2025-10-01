import React from 'react';
import { GameState, GAME_STATUS } from '../../../types';
import GameTimer from '../shared/GameTimer';

interface GameHeaderProps {
  gameState: GameState;
}

export function GameHeader({ gameState }: GameHeaderProps) {
  return (
    <div className="flex justify-between items-center mb-6">
      {/* Role Card */}
      <div className={`p-4 rounded-lg ${gameState.isSpy ? 'bg-spy-red text-white' : 'bg-innocent-blue text-white'}`}>
        <h3 className="text-lg font-bold">
          {gameState.isSpy ? '🕵️ SPY' : `📍 ${gameState.location || 'INNOCENT'}`}
        </h3>
        {!gameState.isSpy && gameState.role && (
          <p className="text-sm opacity-90">Role: {gameState.role}</p>
        )}
      </div>

      {/* Game Timer - centered */}
      {gameState.timer && (
        <div className="bg-white rounded-lg shadow p-4 min-w-[200px]">
          <GameTimer
            timerState={gameState.timer}
            showProgressBar={true}
          />
        </div>
      )}

      {/* Game Status */}
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
              In Progress
            </div>
            <div className="text-sm text-gray-500">Q&A Phase</div>
          </>
        )}
      </div>
    </div>
  );
}