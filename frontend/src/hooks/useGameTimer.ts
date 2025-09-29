import { useState, useEffect, useRef } from 'react';
import { TimerState } from '../types';

export interface UseGameTimerReturn {
  remainingTime: number;
  formattedTime: string;
  timePercentage: number;
  isRunning: boolean;
  isPaused: boolean;
  isExpired: boolean;
  status: string;
}

export const useGameTimer = (serverTimerState?: TimerState): UseGameTimerReturn => {
  const [clientRemainingTime, setClientRemainingTime] = useState<number>(0);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const lastSyncRef = useRef<number>(Date.now());

  // Sync with server timer state when it updates
  useEffect(() => {
    if (serverTimerState) {
      setClientRemainingTime(serverTimerState.remaining_time);
      lastSyncRef.current = Date.now();
    }
  }, [serverTimerState]);

  // Client-side countdown
  useEffect(() => {
    if (!serverTimerState) {
      return;
    }

    // Clear existing interval
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
    }

    // Only run countdown if timer is running
    if (serverTimerState.is_running && serverTimerState.status === 'running') {
      intervalRef.current = setInterval(() => {
        setClientRemainingTime(prev => {
          const newTime = Math.max(0, prev - 1);
          return newTime;
        });
      }, 1000);
    }

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [serverTimerState?.is_running, serverTimerState?.status]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, []);

  // Calculate time percentage for progress bars
  const timePercentage = serverTimerState
    ? Math.max(0, Math.min(100, (clientRemainingTime / serverTimerState.duration) * 100))
    : 0;

  // Format time as MM:SS
  const formatTime = (seconds: number): string => {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = Math.floor(seconds % 60);
    return `${minutes.toString().padStart(2, '0')}:${remainingSeconds.toString().padStart(2, '0')}`;
  };

  // Get color class based on remaining time
  const getTimeColor = (percentage: number): string => {
    if (percentage > 50) return 'text-green-600';
    if (percentage > 25) return 'text-yellow-600';
    return 'text-red-600';
  };

  return {
    remainingTime: clientRemainingTime,
    formattedTime: formatTime(clientRemainingTime),
    timePercentage,
    isRunning: serverTimerState?.is_running ?? false,
    isPaused: serverTimerState?.status === 'paused',
    isExpired: serverTimerState?.status === 'expired' || clientRemainingTime <= 0,
    status: serverTimerState?.status ?? 'not_started'
  };
};

// Helper hook for timer display with colors
export const useTimerDisplay = (timerState?: TimerState) => {
  const timer = useGameTimer(timerState);

  const getTimerColorClass = (): string => {
    if (timer.isExpired) return 'text-red-600 font-bold';
    if (timer.isPaused) return 'text-orange-600';
    if (timer.timePercentage > 50) return 'text-green-600';
    if (timer.timePercentage > 25) return 'text-yellow-600';
    return 'text-red-600 font-bold';
  };

  const getTimerIcon = (): string => {
    if (timer.isExpired) return '⏰';
    if (timer.isPaused) return '⏸️';
    if (timer.timePercentage <= 25) return '⚠️';
    return '⏱️';
  };

  const getTimerStatus = (): string => {
    if (timer.isExpired) return 'TIME UP!';
    if (timer.isPaused) return 'PAUSED';
    if (timer.timePercentage <= 10) return 'HURRY!';
    return 'REMAINING';
  };

  return {
    ...timer,
    colorClass: getTimerColorClass(),
    icon: getTimerIcon(),
    statusText: getTimerStatus()
  };
};