"""Command types for game state machine"""
from dataclasses import dataclass, field
from typing import Literal, List, Dict, Any, Optional
from models.message import GameEvent


@dataclass
class GameCommand:
    """Base class for game commands (inputs to state machine)"""
    player_id: str
    command_type: str


@dataclass
class AskQuestionCommand(GameCommand):
    """Command to ask another player a question"""
    target_player_id: str
    question: str
    command_type: Literal["ask_question"] = field(default="ask_question", init=False)


@dataclass
class AnswerCommand(GameCommand):
    """Command to answer a question"""
    answer: str
    command_type: Literal["answer"] = field(default="answer", init=False)


@dataclass
class AccuseCommand(GameCommand):
    """Command to accuse another player of being the spy"""
    accused_id: str
    command_type: Literal["accuse"] = field(default="accuse", init=False)


@dataclass
class VoteCommand(GameCommand):
    """Command to vote on an accusation"""
    vote: bool  # True = guilty, False = innocent
    command_type: Literal["vote"] = field(default="vote", init=False)


@dataclass
class GuessLocationCommand(GameCommand):
    """Command for spy to guess the location"""
    location: str
    command_type: Literal["guess_location"] = field(default="guess_location", init=False)


@dataclass
class EndOfRoundAccuseCommand(GameCommand):
    """Command to make an accusation during end-of-round phase"""
    accused_id: str
    command_type: Literal["end_of_round_accuse"] = field(default="end_of_round_accuse", init=False)


@dataclass
class EndOfRoundVoteCommand(GameCommand):
    """Command to vote during end-of-round phase"""
    vote: bool
    command_type: Literal["end_of_round_vote"] = field(default="end_of_round_vote", init=False)


@dataclass
class TimeExpiredCommand(GameCommand):
    """Command triggered when timer expires"""
    command_type: Literal["time_expired"] = field(default="time_expired", init=False)
    player_id: str = "system"  # System-generated command


@dataclass
class StateChange:
    """Result of processing a command through the state machine"""
    success: bool
    events: List[GameEvent] = field(default_factory=list)
    error: Optional[str] = None

    # Optional: state changes for debugging/logging
    state_changes: Dict[str, Any] = field(default_factory=dict)
