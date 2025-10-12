"""Event models for Spyfall game"""
from dataclasses import dataclass, field
from typing import Dict, Any
import time


@dataclass
class GameEvent:
    """Represents a game event in the append-only event log"""
    type: str  # "question", "answer", "accusation", "vote", "accusation_resolved", "spy_guess_location", "round_end", "game_end"
    player_id: str
    content: Dict[str, Any]  # event-specific data
    timestamp: float = field(default_factory=time.time)
    formatted_text: str = ""  # pre-formatted text for bot consumption

    def __post_init__(self):
        """Format the event text after initialization if not provided"""
        if not self.formatted_text:
            self.formatted_text = self._format()

    def _format(self) -> str:
        """Format event as human-readable text"""
        # This will be populated with player names when the event is created
        # For now, just use player IDs
        return f"Event: {self.type} by {self.player_id}"


def create_question_event(from_player_id: str, from_player_name: str, to_player_id: str, to_player_name: str, question_text: str) -> GameEvent:
    """Create a question event"""
    return GameEvent(
        type="question",
        player_id=from_player_id,
        content={
            "to_id": to_player_id,
            "text": question_text
        },
        formatted_text=f"**{from_player_name}** asked **{to_player_name}**: \"{question_text}\""
    )


def create_answer_event(from_player_id: str, from_player_name: str, to_player_id: str, answer_text: str) -> GameEvent:
    """Create an answer event"""
    return GameEvent(
        type="answer",
        player_id=from_player_id,
        content={
            "to_id": to_player_id,
            "text": answer_text
        },
        formatted_text=f"**{from_player_name}** answered: \"{answer_text}\""
    )


def create_accusation_event(accuser_id: str, accuser_name: str, accused_id: str, accused_name: str) -> GameEvent:
    """Create an accusation event"""
    return GameEvent(
        type="accusation",
        player_id=accuser_id,
        content={
            "accused_id": accused_id
        },
        formatted_text=f"**{accuser_name}** accused **{accused_name}** of being the spy!"
    )


def create_vote_event(voter_id: str, voter_name: str, vote: bool, accused_name: str) -> GameEvent:
    """Create a vote event"""
    vote_text = "guilty" if vote else "innocent"
    return GameEvent(
        type="vote",
        player_id=voter_id,
        content={
            "vote": vote
        },
        formatted_text=f"**{voter_name}** voted **{vote_text}** for {accused_name}"
    )


def create_accusation_resolved_event(result: str, accused_id: str, accused_name: str, was_spy: bool) -> GameEvent:
    """Create an accusation resolved event"""
    if result == "unanimous_guilty":
        role_text = "spy" if was_spy else "innocent"
        formatted = f"Accusation successful! **{accused_name}** was revealed to be the **{role_text}**."
    else:
        formatted = f"Accusation failed. Voting was not unanimous. Game continues."

    return GameEvent(
        type="accusation_resolved",
        player_id=accused_id,
        content={
            "result": result,
            "was_spy": was_spy
        },
        formatted_text=formatted
    )


def create_spy_guess_location_event(spy_id: str, spy_name: str, guess: str, correct: bool, actual_location: str = None) -> GameEvent:
    """Create a spy guess location event"""
    if correct:
        formatted = f"**{spy_name}** (the spy) correctly guessed the location: **{guess}**!"
    else:
        formatted = f"**{spy_name}** (the spy) incorrectly guessed **{guess}**. The location was **{actual_location}**."

    return GameEvent(
        type="spy_guess_location",
        player_id=spy_id,
        content={
            "guess": guess,
            "correct": correct,
            "actual_location": actual_location
        },
        formatted_text=formatted
    )


def create_round_end_event(reason: str) -> GameEvent:
    """Create a round end event (accusation phase starts)"""
    return GameEvent(
        type="round_end",
        player_id="system",
        content={
            "reason": reason
        },
        formatted_text=f"Time expired! Final accusation phase begins."
    )


def create_game_end_event(winner: str, reason: str, details: str = "") -> GameEvent:
    """Create a game end event"""
    winner_text = "The spy" if winner == "spy" else "The innocents"
    formatted = f"Game over! **{winner_text}** won. {details}" if details else f"Game over! **{winner_text}** won."

    return GameEvent(
        type="game_end",
        player_id="system",
        content={
            "winner": winner,
            "reason": reason
        },
        formatted_text=formatted
    )


# Keep Accusation dataclass for backward compatibility with game state
# This will be removed once all accusation logic is migrated to events
@dataclass
class Accusation:
    accuser_id: str
    accused_id: str
    votes: Dict[str, bool] = field(default_factory=dict)  # player_id -> True/False
    timestamp: float = field(default_factory=time.time)
    is_active: bool = True
