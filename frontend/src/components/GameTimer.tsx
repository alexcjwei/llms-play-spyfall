import React from 'react';
import { TimerState } from '../types';
import { useTimerDisplay } from '../hooks/useGameTimer';

interface GameTimerProps {
  timerState?: TimerState;
  className?: string;
  showProgressBar?: boolean;
}

const GameTimer: React.FC<GameTimerProps> = ({
  timerState,
  className = '',
  showProgressBar = true
}) => {
  const timer = useTimerDisplay(timerState);

  if (!timerState) {
    return (
      <div className={`text-center ${className}`}>
        <div className="text-lg font-bold text-gray-400">
          ⏱️ --:--
        </div>
      </div>
    );
  }

  // Simple emoji based on state
  const getEmoji = () => {
    if (timer.isExpired) return '⏰';
    if (timer.isPaused) return '⏸️';
    return '⏱️';
  };

  return (
    <div className={`text-center ${className}`}>
      {/* Timer Display */}
      <div className={`text-2xl font-bold ${timer.colorClass} flex items-center justify-center gap-2`}>
        <span>{getEmoji()}</span>
        <span>{timer.formattedTime}</span>
      </div>

      {/* Progress Bar */}
      {showProgressBar && (
        <div className="mt-3">
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className={`h-2 rounded-full transition-all duration-1000 ${
                timer.timePercentage > 50
                  ? 'bg-green-500'
                  : timer.timePercentage > 25
                  ? 'bg-yellow-500'
                  : 'bg-red-500'
              }`}
              style={{ width: `${timer.timePercentage}%` }}
            />
          </div>
        </div>
      )}
    </div>
  );
};

export default GameTimer;