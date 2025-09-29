import time
from typing import Dict, Optional
from dataclasses import dataclass
from enum import Enum


class TimerStatus(Enum):
    NOT_STARTED = "not_started"
    RUNNING = "running"
    PAUSED = "paused"
    EXPIRED = "expired"


@dataclass
class TimerState:
    """Represents the current state of a game timer"""
    duration: float  # Total duration in seconds (8 minutes = 480 seconds)
    started_at: Optional[float] = None  # When the timer was first started
    accumulated_paused_time: float = 0.0  # Total time spent paused
    is_running: bool = False
    last_pause_time: Optional[float] = None  # When it was last paused
    status: TimerStatus = TimerStatus.NOT_STARTED

    def to_dict(self) -> dict:
        """Convert timer state to dictionary for JSON serialization"""
        return {
            "duration": self.duration,
            "started_at": self.started_at,
            "accumulated_paused_time": self.accumulated_paused_time,
            "is_running": self.is_running,
            "status": self.status.value,
            "remaining_time": self.get_remaining_time(),
            "elapsed_time": self.get_elapsed_time()
        }

    def get_elapsed_time(self) -> float:
        """Get total elapsed time (running time, not including paused time)"""
        if not self.started_at:
            return 0.0

        if self.is_running:
            # Currently running: total time minus paused time
            return (time.time() - self.started_at) - self.accumulated_paused_time
        else:
            # Currently paused: calculate up to last pause
            if self.last_pause_time:
                return (self.last_pause_time - self.started_at) - self.accumulated_paused_time
            else:
                # Was started but never paused (shouldn't happen in normal flow)
                return (time.time() - self.started_at) - self.accumulated_paused_time

    def get_remaining_time(self) -> float:
        """Get remaining time in seconds"""
        if self.status == TimerStatus.EXPIRED:
            return 0.0

        elapsed = self.get_elapsed_time()
        remaining = max(0.0, self.duration - elapsed)

        # Update status if expired
        if remaining <= 0.0:
            self.status = TimerStatus.EXPIRED

        return remaining


class GameTimer:
    """Manages game timer with pause/resume functionality"""

    def __init__(self, duration: float = 480.0):  # 8 minutes default
        self.state = TimerState(duration=duration)

    def start(self) -> bool:
        """Start the timer. Returns True if successfully started."""
        if self.state.status != TimerStatus.NOT_STARTED:
            return False

        current_time = time.time()
        self.state.started_at = current_time
        self.state.is_running = True
        self.state.status = TimerStatus.RUNNING
        return True

    def pause(self) -> bool:
        """Pause the timer. Returns True if successfully paused."""
        if not self.state.is_running or self.state.status == TimerStatus.EXPIRED:
            return False

        current_time = time.time()
        self.state.last_pause_time = current_time
        self.state.is_running = False
        self.state.status = TimerStatus.PAUSED
        return True

    def resume(self) -> bool:
        """Resume the timer. Returns True if successfully resumed."""
        if self.state.is_running or self.state.status not in [TimerStatus.PAUSED]:
            return False

        if self.state.last_pause_time and self.state.started_at:
            # Add the paused duration to accumulated paused time
            pause_duration = time.time() - self.state.last_pause_time
            self.state.accumulated_paused_time += pause_duration

        self.state.is_running = True
        self.state.status = TimerStatus.RUNNING
        self.state.last_pause_time = None
        return True

    def stop(self):
        """Stop and reset the timer"""
        self.state = TimerState(duration=self.state.duration)

    def is_expired(self) -> bool:
        """Check if the timer has expired"""
        remaining = self.state.get_remaining_time()
        return remaining <= 0.0

    def get_status(self) -> TimerStatus:
        """Get current timer status"""
        # Update status based on remaining time
        if self.state.status != TimerStatus.EXPIRED:
            remaining = self.state.get_remaining_time()
            if remaining <= 0.0:
                self.state.status = TimerStatus.EXPIRED
                self.state.is_running = False

        return self.state.status

    def to_dict(self) -> dict:
        """Get timer state as dictionary"""
        # Update status before returning
        self.get_status()
        return self.state.to_dict()


class GameTimerManager:
    """Manages timers for multiple games"""

    def __init__(self):
        self.timers: Dict[str, GameTimer] = {}

    def create_timer(self, game_id: str, duration: float = 480.0) -> GameTimer:
        """Create a new timer for a game"""
        timer = GameTimer(duration)
        self.timers[game_id] = timer
        return timer

    def get_timer(self, game_id: str) -> Optional[GameTimer]:
        """Get timer for a game"""
        return self.timers.get(game_id)

    def remove_timer(self, game_id: str) -> bool:
        """Remove timer for a game"""
        if game_id in self.timers:
            del self.timers[game_id]
            return True
        return False

    def start_timer(self, game_id: str) -> bool:
        """Start timer for a game"""
        timer = self.get_timer(game_id)
        if timer:
            return timer.start()
        return False

    def pause_timer(self, game_id: str) -> bool:
        """Pause timer for a game"""
        timer = self.get_timer(game_id)
        if timer:
            return timer.pause()
        return False

    def resume_timer(self, game_id: str) -> bool:
        """Resume timer for a game"""
        timer = self.get_timer(game_id)
        if timer:
            return timer.resume()
        return False

    def get_timer_state(self, game_id: str) -> Optional[dict]:
        """Get timer state for a game"""
        timer = self.get_timer(game_id)
        if timer:
            return timer.get_state_dict()
        return None

    def check_expired_timers(self) -> list[str]:
        """Check for expired timers and return list of game IDs"""
        expired_games = []
        for game_id, timer in self.timers.items():
            if timer.is_expired():
                expired_games.append(game_id)
        return expired_games


# Global timer manager instance
timer_manager = GameTimerManager()