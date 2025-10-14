"""Game model and state management for Spyfall"""
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from enum import Enum
import random
import time

from models.player import Player, PlayerRole
from models.location import Location, LOCATIONS
from models.message import GameEvent, Accusation, create_question_event, create_answer_event, create_accusation_event, create_vote_event, create_accusation_resolved_event, create_spy_guess_location_event, create_round_end_event, create_game_end_event
from models.timer import GameTimer
from models.commands import (
    GameCommand, StateChange, AskQuestionCommand, AnswerCommand, AccuseCommand,
    VoteCommand, GuessLocationCommand, EndOfRoundAccuseCommand, EndOfRoundVoteCommand,
    TimeExpiredCommand
)


class GameStatus(Enum):
    WAITING = "waiting"
    IN_PROGRESS = "in_progress"
    VOTING = "voting"
    END_OF_ROUND_VOTING = "end_of_round_voting"
    FINISHED = "finished"


class GameEndReason(Enum):
    TIME_EXPIRED = "time_expired"
    SPY_ACCUSED = "spy_accused"
    INNOCENT_ACCUSED = "innocent_accused"
    SPY_GUESSED_LOCATION = "spy_guessed_location"
    SPY_FAILED_GUESS = "spy_failed_guess"


@dataclass
class Game:
    id: str
    players: List[Player] = field(default_factory=list)
    status: GameStatus = GameStatus.WAITING
    current_turn: Optional[str] = None
    location: Optional[Location] = None
    spy_id: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    events: List[GameEvent] = field(default_factory=list)
    accusations: List[Accusation] = field(default_factory=list)
    clock_stopped: bool = False
    clock_stopped_by: Optional[str] = None
    winner: Optional[str] = None  # "spy" or "innocents"
    end_reason: Optional[GameEndReason] = None
    last_questioned_by: Optional[str] = None  # Prevents asking same player back
    qa_rounds_completed: int = 0  # Track completed Q&A rounds
    max_qa_rounds: int = 3  # Game ends after this many Q&A rounds
    timer: GameTimer = field(default_factory=lambda: GameTimer(duration=480.0))  # 8 minutes

    @property
    def current_accusation(self) -> Optional[Accusation]:
        """Get the most recent active accusation"""
        active_accusations = [acc for acc in self.accusations if acc.is_active]
        return active_accusations[-1] if active_accusations else None

    def add_player(self, player: Player) -> bool:
        """Add a player to the game. Returns True if successful."""
        if len(self.players) >= 8:  # Max 8 players as per typical Spyfall rules
            return False

        if self.status != GameStatus.WAITING:
            return False

        if any(p.id == player.id for p in self.players):
            return False

        self.players.append(player)
        return True

    def remove_player(self, player_id: str) -> bool:
        """Remove a player from the game."""
        self.players = [p for p in self.players if p.id != player_id]

        # If it's the current turn player, advance turn
        if self.current_turn == player_id:
            self._advance_turn()

        # If spy left during game, innocents win
        if self.spy_id == player_id and self.status == GameStatus.IN_PROGRESS:
            self._end_game(GameEndReason.SPY_ACCUSED, "innocents")

        return True

    def start_game(self, random_order: bool = True) -> bool:
        """Start the game with role assignment. Minimum 3 players required."""
        if len(self.players) < 3:
            return False

        if self.status != GameStatus.WAITING:
            return False

        # Shuffle players
        if random_order:
            random.shuffle(self.players)

        # Assign spy and location roles
        self._assign_roles()

        # Dealer (first player) starts the round
        if self.players:
            self.current_turn = self.players[0].id

        self.status = GameStatus.IN_PROGRESS

        # Start the timer
        self.timer.start()

        return True

    # =========================================================================
    # STATE MACHINE INTERFACE
    # =========================================================================

    def process_event(self, command: GameCommand) -> StateChange:
        """
        Process a game command and update state atomically.
        This is the ONLY public method that should mutate game state.

        Args:
            command: The command to process

        Returns:
            StateChange with success status, generated events, and any errors
        """
        # Validate command
        validation_error = self._validate_command(command)
        if validation_error:
            return StateChange(success=False, events=[], error=validation_error)

        # Dispatch to appropriate handler
        handlers = {
            "ask_question": self._handle_ask_question,
            "answer": self._handle_answer,
            "accuse": self._handle_accuse,
            "vote": self._handle_vote,
            "guess_location": self._handle_guess_location,
            "end_of_round_accuse": self._handle_end_of_round_accuse,
            "end_of_round_vote": self._handle_end_of_round_vote,
            "time_expired": self._handle_time_expired,
        }

        handler = handlers.get(command.command_type)
        if not handler:
            return StateChange(
                success=False,
                events=[],
                error=f"Unknown command type: {command.command_type}"
            )

        # Execute handler
        return handler(command)

    def replay_commands(self, commands: List[GameCommand]) -> 'Game':
        """
        Replay a sequence of commands to reconstruct game state.
        Useful for testing and debugging.

        Args:
            commands: List of commands to replay

        Returns:
            Self (for chaining)

        Raises:
            ValueError: If any command fails to replay
        """
        for i, command in enumerate(commands):
            result = self.process_event(command)
            if not result.success:
                raise ValueError(
                    f"Failed to replay command {i} ({command.command_type}): {result.error}"
                )
        return self

    # =========================================================================
    # COMMAND VALIDATORS
    # =========================================================================

    def _validate_command(self, command: GameCommand) -> Optional[str]:
        """
        Validate a command against current game state.

        Returns:
            Error message if invalid, None if valid
        """
        validators = {
            "ask_question": self._validate_ask_question,
            "answer": self._validate_answer,
            "accuse": self._validate_accuse,
            "vote": self._validate_vote,
            "guess_location": self._validate_guess_location,
            "end_of_round_accuse": self._validate_end_of_round_accuse,
            "end_of_round_vote": self._validate_end_of_round_vote,
            "time_expired": self._validate_time_expired,
        }

        validator = validators.get(command.command_type)
        if not validator:
            return f"No validator for command type: {command.command_type}"

        return validator(command)

    def _validate_ask_question(self, cmd: AskQuestionCommand) -> Optional[str]:
        """Validate ask question command"""
        if self.status != GameStatus.IN_PROGRESS:
            return "Game is not in progress"
        if self.clock_stopped:
            return "Clock is stopped"
        if self.current_turn != cmd.player_id:
            return f"Not {cmd.player_id}'s turn"
        if self.last_questioned_by == cmd.target_player_id:
            return "Cannot ask the player who just asked you"
        if not self._get_player(cmd.player_id):
            return f"Player {cmd.player_id} not found"
        if not self._get_player(cmd.target_player_id):
            return f"Target player {cmd.target_player_id} not found"
        if cmd.player_id == cmd.target_player_id:
            return "Cannot ask yourself"
        return None

    def _validate_answer(self, cmd: AnswerCommand) -> Optional[str]:
        """Validate answer command"""
        if self.status != GameStatus.IN_PROGRESS:
            return "Game is not in progress"
        if self.clock_stopped:
            return "Clock is stopped"
        if self.current_turn != cmd.player_id:
            return f"Not {cmd.player_id}'s turn"
        if not self._get_player(cmd.player_id):
            return f"Player {cmd.player_id} not found"
        if not self.last_questioned_by:
            return "No question to answer"
        return None

    def _validate_accuse(self, cmd: AccuseCommand) -> Optional[str]:
        """Validate accuse command"""
        if self.status != GameStatus.IN_PROGRESS:
            return "Game is not in progress"
        if self.clock_stopped:
            return "Clock is already stopped"
        if cmd.player_id == cmd.accused_id:
            return "Cannot accuse yourself"

        accuser = self._get_player(cmd.player_id)
        if not accuser:
            return f"Player {cmd.player_id} not found"
        if accuser.has_accused_this_round:
            return "Player has already accused this round"
        if not self._get_player(cmd.accused_id):
            return f"Accused player {cmd.accused_id} not found"
        return None

    def _validate_vote(self, cmd: VoteCommand) -> Optional[str]:
        """Validate vote command"""
        if self.status != GameStatus.VOTING:
            return "Game is not in voting phase"
        if not self.current_accusation:
            return "No active accusation"
        if cmd.player_id == self.current_accusation.accused_id:
            return "Accused player cannot vote"
        if not self._get_player(cmd.player_id):
            return f"Player {cmd.player_id} not found"
        if cmd.player_id in self.current_accusation.votes:
            return "Player has already voted"
        return None

    def _validate_guess_location(self, cmd: GuessLocationCommand) -> Optional[str]:
        """Validate guess location command"""
        if self.status != GameStatus.IN_PROGRESS:
            return "Game is not in progress"
        if self.clock_stopped:
            return "Clock is stopped"
        if cmd.player_id != self.spy_id:
            return "Only the spy can guess the location"
        if not self.location:
            return "No location set"
        return None

    def _validate_end_of_round_accuse(self, cmd: EndOfRoundAccuseCommand) -> Optional[str]:
        """Validate end of round accuse command"""
        if self.status != GameStatus.END_OF_ROUND_VOTING:
            return "Not in end-of-round voting phase"
        if cmd.player_id != self.current_turn:
            return f"Not {cmd.player_id}'s turn to accuse"
        if cmd.player_id == cmd.accused_id:
            return "Cannot accuse yourself"

        accuser = self._get_player(cmd.player_id)
        if not accuser:
            return f"Player {cmd.player_id} not found"
        if accuser.has_accused_this_round:
            return "Player has already accused this round"
        if not self._get_player(cmd.accused_id):
            return f"Accused player {cmd.accused_id} not found"
        return None

    def _validate_end_of_round_vote(self, cmd: EndOfRoundVoteCommand) -> Optional[str]:
        """Validate end of round vote command"""
        if self.status != GameStatus.END_OF_ROUND_VOTING:
            return "Not in end-of-round voting phase"
        if not self.current_accusation:
            return "No active accusation"
        if cmd.player_id == self.current_accusation.accused_id:
            return "Accused player cannot vote"
        if not self._get_player(cmd.player_id):
            return f"Player {cmd.player_id} not found"
        if cmd.player_id in self.current_accusation.votes:
            return "Player has already voted"
        return None

    def _validate_time_expired(self, cmd: TimeExpiredCommand) -> Optional[str]:
        """Validate time expired command"""
        if self.status != GameStatus.IN_PROGRESS:
            return "Game is not in progress"
        if self.clock_stopped:
            return "Clock is already stopped"
        if not self.timer.is_expired():
            return "Timer has not expired yet"
        return None

    # =========================================================================
    # COMMAND HANDLERS
    # =========================================================================

    def _handle_ask_question(self, cmd: AskQuestionCommand) -> StateChange:
        """Handle ask question command"""
        from_player = self._get_player(cmd.player_id)
        to_player = self._get_player(cmd.target_player_id)

        # Create event
        event = create_question_event(
            from_player_id=cmd.player_id,
            from_player_name=from_player.name,
            to_player_id=cmd.target_player_id,
            to_player_name=to_player.name,
            question_text=cmd.question
        )

        # Atomically update all related state
        self.events.append(event)
        self.current_turn = cmd.target_player_id
        self.last_questioned_by = cmd.player_id

        return StateChange(
            success=True,
            events=[event],
            state_changes={
                "current_turn": cmd.target_player_id,
                "last_questioned_by": cmd.player_id
            }
        )

    def _handle_answer(self, cmd: AnswerCommand) -> StateChange:
        """Handle answer command"""
        from_player = self._get_player(cmd.player_id)

        # Create event
        event = create_answer_event(
            from_player_id=cmd.player_id,
            from_player_name=from_player.name,
            to_player_id=self.last_questioned_by,
            answer_text=cmd.answer
        )

        # Atomically update state
        self.events.append(event)
        self.qa_rounds_completed += 1
        # Turn stays with answerer, last_questioned_by stays to prevent asking back

        return StateChange(
            success=True,
            events=[event],
            state_changes={
                "qa_rounds_completed": self.qa_rounds_completed
            }
        )

    def _handle_accuse(self, cmd: AccuseCommand) -> StateChange:
        """Handle accuse command"""
        accuser = self._get_player(cmd.player_id)
        accused = self._get_player(cmd.accused_id)

        # Pause the timer
        self.timer.pause()

        # Create accusation
        accusation = Accusation(
            accuser_id=cmd.player_id,
            accused_id=cmd.accused_id
        )
        self.accusations.append(accusation)

        # Create event
        event = create_accusation_event(
            accuser_id=cmd.player_id,
            accuser_name=accuser.name,
            accused_id=cmd.accused_id,
            accused_name=accused.name
        )

        # Atomically update state
        self.events.append(event)
        self.clock_stopped = True
        self.clock_stopped_by = cmd.player_id
        self.status = GameStatus.VOTING
        accuser.has_accused_this_round = True

        return StateChange(
            success=True,
            events=[event],
            state_changes={
                "status": GameStatus.VOTING,
                "clock_stopped": True,
                "clock_stopped_by": cmd.player_id
            }
        )

    def _handle_vote(self, cmd: VoteCommand) -> StateChange:
        """Handle vote command"""
        voter = self._get_player(cmd.player_id)
        accused = self._get_player(self.current_accusation.accused_id)

        # Record vote
        self.current_accusation.votes[cmd.player_id] = cmd.vote

        # Create event
        event = create_vote_event(
            voter_id=cmd.player_id,
            voter_name=voter.name,
            vote=cmd.vote,
            accused_name=accused.name
        )
        self.events.append(event)

        # Check if all eligible players have voted
        eligible_voters = [p.id for p in self.players if p.id != self.current_accusation.accused_id]
        all_voted = len(self.current_accusation.votes) == len(eligible_voters)

        state_changes = {"vote_recorded": True}

        # If all voted, resolve immediately
        if all_voted:
            self._resolve_accusation()
            state_changes["accusation_resolved"] = True

        return StateChange(
            success=True,
            events=[event],
            state_changes=state_changes
        )

    def _handle_guess_location(self, cmd: GuessLocationCommand) -> StateChange:
        """Handle guess location command"""
        spy = self._get_player(cmd.player_id)

        # Check guess
        correct = cmd.location.lower() == self.location.name.lower()

        # Create event
        event = create_spy_guess_location_event(
            spy_id=cmd.player_id,
            spy_name=spy.name,
            guess=cmd.location,
            correct=correct,
            actual_location=self.location.name if not correct else None
        )
        self.events.append(event)

        # End game based on result
        if correct:
            self._end_game(GameEndReason.SPY_GUESSED_LOCATION, "spy")
            spy.points += 4
        else:
            self._end_game(GameEndReason.SPY_FAILED_GUESS, "innocents")
            for player in self.players:
                if player.role == PlayerRole.INNOCENT:
                    player.points += 1

        return StateChange(
            success=True,
            events=[event],
            state_changes={
                "game_ended": True,
                "winner": self.winner,
                "end_reason": self.end_reason
            }
        )

    def _handle_end_of_round_accuse(self, cmd: EndOfRoundAccuseCommand) -> StateChange:
        """Handle end of round accuse command"""
        accuser = self._get_player(cmd.player_id)
        accused = self._get_player(cmd.accused_id)

        # Create accusation
        accusation = Accusation(
            accuser_id=cmd.player_id,
            accused_id=cmd.accused_id,
            votes={},
            is_active=True
        )
        self.accusations.append(accusation)

        # Create event
        event = create_accusation_event(
            accuser_id=cmd.player_id,
            accuser_name=accuser.name,
            accused_id=cmd.accused_id,
            accused_name=accused.name
        )
        self.events.append(event)

        # Update state
        accuser.has_accused_this_round = True

        return StateChange(
            success=True,
            events=[event],
            state_changes={
                "accusation_created": True
            }
        )

    def _handle_end_of_round_vote(self, cmd: EndOfRoundVoteCommand) -> StateChange:
        """Handle end of round vote command"""
        voter = self._get_player(cmd.player_id)
        accused = self._get_player(self.current_accusation.accused_id)

        # Record vote
        self.current_accusation.votes[cmd.player_id] = cmd.vote

        # Create event
        event = create_vote_event(
            voter_id=cmd.player_id,
            voter_name=voter.name,
            vote=cmd.vote,
            accused_name=accused.name
        )
        self.events.append(event)

        # Check if all eligible players have voted
        eligible_voters = [p.id for p in self.players if p.id != self.current_accusation.accused_id]
        all_voted = len(self.current_accusation.votes) == len(eligible_voters)

        state_changes = {"vote_recorded": True}

        # If all voted, resolve immediately
        if all_voted:
            self._resolve_end_of_round_accusation()
            state_changes["accusation_resolved"] = True

        return StateChange(
            success=True,
            events=[event],
            state_changes=state_changes
        )

    def _handle_time_expired(self, cmd: TimeExpiredCommand) -> StateChange:
        """Handle time expired command"""
        # Create event
        event = create_round_end_event(reason="time_expired")
        self.events.append(event)

        # Start end-of-round voting
        self._start_end_of_round_voting()

        return StateChange(
            success=True,
            events=[event],
            state_changes={
                "status": GameStatus.END_OF_ROUND_VOTING,
                "time_expired": True
            }
        )

    # =========================================================================
    # HELPER METHODS
    # =========================================================================

    def _get_player(self, player_id: str) -> Optional[Player]:
        """Get player by ID"""
        return next((p for p in self.players if p.id == player_id), None)

    def _assign_roles(self):
        """Randomly assign spy role and location with roles to other players."""
        # Choose spy randomly
        spy_player = random.choice(self.players)
        self.spy_id = spy_player.id
        spy_player.role = PlayerRole.SPY

        # Choose location randomly
        self.location = random.choice(LOCATIONS)

        # Assign location roles to non-spy players
        available_roles = self.location.roles.copy()
        random.shuffle(available_roles)

        for player in self.players:
            if player.id != self.spy_id:
                player.role = PlayerRole.INNOCENT
                # Assign role, cycling through if more players than roles
                if available_roles:
                    player.location_role = available_roles.pop()
                else:
                    # Reuse roles if needed
                    player.location_role = random.choice(self.location.roles)

    def ask_question(self, from_player_id: str, to_player_id: str, content: str) -> bool:
        """Player asks a question to another player."""
        if self.status != GameStatus.IN_PROGRESS or self.clock_stopped:
            return False

        if self.current_turn != from_player_id:
            return False

        # Can't ask the player who just asked you
        if self.last_questioned_by == to_player_id:
            return False

        # Get player names
        from_player = next((p for p in self.players if p.id == from_player_id), None)
        to_player = next((p for p in self.players if p.id == to_player_id), None)

        if not from_player or not to_player:
            return False

        # Create event
        event = create_question_event(
            from_player_id=from_player_id,
            from_player_name=from_player.name,
            to_player_id=to_player_id,
            to_player_name=to_player.name,
            question_text=content
        )
        self.events.append(event)

        # Switch turn to the questioned player
        self.current_turn = to_player_id
        self.last_questioned_by = from_player_id

        return True

    def give_answer(self, from_player_id: str, content: str) -> bool:
        """Player gives an answer and can then ask the next question."""
        if self.status != GameStatus.IN_PROGRESS or self.clock_stopped:
            return False

        if self.current_turn != from_player_id:
            return False

        # Get player names
        from_player = next((p for p in self.players if p.id == from_player_id), None)
        if not from_player:
            return False

        # Create answer event
        event = create_answer_event(
            from_player_id=from_player_id,
            from_player_name=from_player.name,
            to_player_id=self.last_questioned_by,
            answer_text=content
        )
        self.events.append(event)

        # Increment Q&A round counter (a round = question + answer)
        self.qa_rounds_completed += 1

        # Player can now ask the next question (turn stays with them)
        # Note: last_questioned_by is kept to prevent asking the same player back
        return True

    def stop_clock_for_accusation(self, accuser_id: str, accused_id: str) -> bool:
        """Player stops the clock to make an accusation."""
        if self.status != GameStatus.IN_PROGRESS or self.clock_stopped:
            return False

        # Check if player has already accused this round
        accuser = next((p for p in self.players if p.id == accuser_id), None)
        accused = next((p for p in self.players if p.id == accused_id), None)

        if not accuser or not accused or accuser.has_accused_this_round:
            return False

        # Pause the timer
        self.timer.pause()

        # Stop the clock and create accusation
        self.clock_stopped = True
        self.clock_stopped_by = accuser_id
        self.status = GameStatus.VOTING
        accusation = Accusation(
            accuser_id=accuser_id,
            accused_id=accused_id
        )
        self.accusations.append(accusation)

        # Create accusation event
        event = create_accusation_event(
            accuser_id=accuser_id,
            accuser_name=accuser.name,
            accused_id=accused_id,
            accused_name=accused.name
        )
        self.events.append(event)

        accuser.has_accused_this_round = True
        return True

    def vote_on_accusation(self, voter_id: str, vote: bool) -> bool:
        """Player votes on the current accusation."""
        if self.status != GameStatus.VOTING or not self.current_accusation:
            return False

        # Accused player cannot vote
        if voter_id == self.current_accusation.accused_id:
            return False

        # Get player names
        voter = next((p for p in self.players if p.id == voter_id), None)
        accused = next((p for p in self.players if p.id == self.current_accusation.accused_id), None)

        if not voter or not accused:
            return False

        self.current_accusation.votes[voter_id] = vote

        # Create vote event
        event = create_vote_event(
            voter_id=voter_id,
            voter_name=voter.name,
            vote=vote,
            accused_name=accused.name
        )
        self.events.append(event)

        # Check if all eligible players have voted
        eligible_voters = [p.id for p in self.players if p.id != self.current_accusation.accused_id]
        if len(self.current_accusation.votes) == len(eligible_voters):
            self._resolve_accusation()

        return True

    def _resolve_accusation(self):
        """Resolve the current accusation based on votes."""
        if not self.current_accusation:
            return

        # Check if unanimous agreement
        votes = list(self.current_accusation.votes.values())
        unanimous_guilty = all(votes) and len(votes) > 0

        # Get accused player
        accused_player = next((p for p in self.players if p.id == self.current_accusation.accused_id), None)
        if not accused_player:
            return

        if unanimous_guilty:
            # Accusation successful - reveal the accused player's role
            was_spy = accused_player.role == PlayerRole.SPY

            # Create accusation resolved event
            event = create_accusation_resolved_event(
                result="unanimous_guilty",
                accused_id=accused_player.id,
                accused_name=accused_player.name,
                was_spy=was_spy
            )
            self.events.append(event)

            if was_spy:
                # Spy caught - innocents win
                self._end_game(GameEndReason.SPY_ACCUSED, "innocents")
                # Award points: accuser gets 2, others get 1
                for player in self.players:
                    if player.role == PlayerRole.INNOCENT:
                        if player.id == self.current_accusation.accuser_id:
                            player.points += 2
                        else:
                            player.points += 1
            else:
                # Innocent accused - spy wins
                self._end_game(GameEndReason.INNOCENT_ACCUSED, "spy")
                # Spy gets 4 points
                spy = next((p for p in self.players if p.id == self.spy_id), None)
                if spy:
                    spy.points += 4
        else:
            # Accusation failed - resume game
            # Create accusation resolved event
            event = create_accusation_resolved_event(
                result="not_unanimous",
                accused_id=accused_player.id,
                accused_name=accused_player.name,
                was_spy=False
            )
            self.events.append(event)

            self.timer.resume()
            self.clock_stopped = False
            self.clock_stopped_by = None
            self.status = GameStatus.IN_PROGRESS
            # Mark current accusation as inactive
            if self.current_accusation:
                self.current_accusation.is_active = False

    def spy_guess_location(self, spy_id: str, guessed_location: str) -> bool:
        """Spy attempts to guess the location to win."""
        if self.status != GameStatus.IN_PROGRESS:
            return False

        if spy_id != self.spy_id:
            return False

        if not self.location:
            return False

        # Spy can only guess when clock is running
        if self.clock_stopped:
            return False

        # Get spy player
        spy = next((p for p in self.players if p.id == spy_id), None)
        if not spy:
            return False

        # Check guess
        correct = guessed_location.lower() == self.location.name.lower()

        # Create spy guess location event
        event = create_spy_guess_location_event(
            spy_id=spy_id,
            spy_name=spy.name,
            guess=guessed_location,
            correct=correct,
            actual_location=self.location.name if not correct else None
        )
        self.events.append(event)

        if correct:
            # Spy wins
            self._end_game(GameEndReason.SPY_GUESSED_LOCATION, "spy")
            # Spy gets 4 points
            spy.points += 4
        else:
            # Spy loses
            self._end_game(GameEndReason.SPY_FAILED_GUESS, "innocents")
            # Each innocent gets 1 point
            for player in self.players:
                if player.role == PlayerRole.INNOCENT:
                    player.points += 1

        return True

    def check_time_expired(self) -> bool:
        """Check if the round time has expired."""
        if (self.status != GameStatus.IN_PROGRESS or
            self.clock_stopped):
            return False

        if self.timer.is_expired():
            # Time expired - process through state machine
            command = TimeExpiredCommand()
            result = self.process_event(command)
            return result.success

        return False

    def _advance_turn(self):
        """Move to the next player's turn."""
        if not self.players or not self.current_turn:
            return

        current_index = next((i for i, p in enumerate(self.players) if p.id == self.current_turn), 0)
        next_index = (current_index + 1) % len(self.players)
        self.current_turn = self.players[next_index].id


    def _start_end_of_round_voting(self):
        """Start the end-of-round accusation and voting phase."""
        # Clear any existing accusation
        if self.current_accusation:
            self.current_accusation.is_active = False

        # Reset accusation flags for end-of-round voting
        for player in self.players:
            player.has_accused_this_round = False

        # Start with dealer (first player) making the accusation
        self.current_turn = self.players[0].id if self.players else None
        self.status = GameStatus.END_OF_ROUND_VOTING
        self.clock_stopped = True
        self.clock_stopped_by = "time_expired"

    def make_end_of_round_accusation(self, accuser_id: str, accused_id: str) -> bool:
        """Handle end-of-round accusation by current accuser."""
        if self.status != GameStatus.END_OF_ROUND_VOTING:
            return False

        if accuser_id != self.current_turn:
            return False

        if accuser_id == accused_id:
            return False

        # Find accuser and accused
        accuser = next((p for p in self.players if p.id == accuser_id), None)
        accused = next((p for p in self.players if p.id == accused_id), None)

        if not accuser or not accused or accuser.has_accused_this_round:
            return False

        # Create accusation
        accusation = Accusation(
            accuser_id=accuser_id,
            accused_id=accused_id,
            votes={},
            is_active=True
        )

        self.accusations.append(accusation)

        # Create accusation event
        event = create_accusation_event(
            accuser_id=accuser_id,
            accuser_name=accuser.name,
            accused_id=accused_id,
            accused_name=accused.name
        )
        self.events.append(event)

        accuser.has_accused_this_round = True

        return True

    def vote_on_end_of_round_accusation(self, voter_id: str, vote: bool) -> bool:
        """Vote on the current end-of-round accusation."""
        if self.status != GameStatus.END_OF_ROUND_VOTING:
            return False

        accusation = self.current_accusation
        if not accusation:
            return False

        # Accused player cannot vote
        if voter_id == accusation.accused_id:
            return False

        # Check if voter is in the game
        voter = next((p for p in self.players if p.id == voter_id), None)
        accused = next((p for p in self.players if p.id == accusation.accused_id), None)

        if not voter or not accused:
            return False

        # Record vote
        accusation.votes[voter_id] = vote

        # Create vote event
        event = create_vote_event(
            voter_id=voter_id,
            voter_name=voter.name,
            vote=vote,
            accused_name=accused.name
        )
        self.events.append(event)

        # Check if all eligible players have voted
        eligible_voters = [p.id for p in self.players if p.id != accusation.accused_id]
        if len(accusation.votes) == len(eligible_voters):
            self._resolve_end_of_round_accusation()

        return True

    def _resolve_end_of_round_accusation(self):
        """Resolve the current end-of-round accusation."""
        accusation = self.current_accusation
        if not accusation:
            return

        # Check if unanimous guilty vote
        all_votes_guilty = all(vote for vote in accusation.votes.values())

        # Get accused player
        accused = next((p for p in self.players if p.id == accusation.accused_id), None)
        if not accused:
            return

        if all_votes_guilty and len(accusation.votes) > 0:
            # Unanimous guilty vote - reveal the accused
            was_spy = accused.role == PlayerRole.SPY

            # Create accusation resolved event
            event = create_accusation_resolved_event(
                result="unanimous_guilty",
                accused_id=accused.id,
                accused_name=accused.name,
                was_spy=was_spy
            )
            self.events.append(event)

            if was_spy:
                # Correctly accused the spy - innocents win
                self._end_game(GameEndReason.SPY_ACCUSED, "innocents")
                # Each innocent gets 1 point, accuser gets 2 points
                for player in self.players:
                    if player.role == PlayerRole.INNOCENT:
                        player.points += 1
                    if player.id == accusation.accuser_id:
                        player.points += 1  # Additional point for successful accusation
            else:
                # Wrongly accused an innocent - spy wins
                self._end_game(GameEndReason.INNOCENT_ACCUSED, "spy")
                # Spy gets 4 points for innocent being accused
                spy = next((p for p in self.players if p.id == self.spy_id), None)
                if spy:
                    spy.points += 4
        else:
            # Not unanimous - create event and move to next accuser
            event = create_accusation_resolved_event(
                result="not_unanimous",
                accused_id=accused.id,
                accused_name=accused.name,
                was_spy=False
            )
            self.events.append(event)
            self._move_to_next_end_of_round_accuser()

    def _move_to_next_end_of_round_accuser(self):
        """Move to the next player to make an end-of-round accusation."""
        accusation = self.current_accusation
        if accusation:
            accusation.is_active = False

        # Find next player who hasn't accused yet
        current_index = next((i for i, p in enumerate(self.players) if p.id == self.current_turn), 0)

        for i in range(1, len(self.players)):
            next_index = (current_index + i) % len(self.players)
            next_player = self.players[next_index]

            if not next_player.has_accused_this_round:
                self.current_turn = next_player.id
                return

        # Everyone has accused without unanimous decision - spy wins
        self._end_game(GameEndReason.TIME_EXPIRED, "spy")
        # Spy gets 2 points for not being caught
        spy = next((p for p in self.players if p.id == self.spy_id), None)
        if spy:
            spy.points += 2

    def _end_game(self, reason: GameEndReason, winner: str):
        """End the game with specified reason and winner."""
        self.status = GameStatus.FINISHED
        self.end_reason = reason
        self.winner = winner

        # Create game end event with details
        details = self._get_game_end_details(reason, winner)
        event = create_game_end_event(
            winner=winner,
            reason=reason.value,
            details=details
        )
        self.events.append(event)

        # Stop the timer when game ends
        self.timer.stop()

    def _get_game_end_details(self, reason: GameEndReason, winner: str) -> str:
        """Get detailed message for game end"""
        if reason == GameEndReason.SPY_ACCUSED:
            return "The spy was correctly identified!"
        elif reason == GameEndReason.INNOCENT_ACCUSED:
            return "An innocent was wrongly accused!"
        elif reason == GameEndReason.SPY_GUESSED_LOCATION:
            return "The spy guessed the location correctly!"
        elif reason == GameEndReason.SPY_FAILED_GUESS:
            return "The spy's guess was incorrect!"
        elif reason == GameEndReason.TIME_EXPIRED:
            return "Time ran out and the spy was not caught!"
        return ""


    def to_dict(self) -> Dict[str, Any]:
        """Convert game to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "status": self.status.value,
            "players": [
                {
                    "id": p.id,
                    "name": p.name,
                    "isBot": p.is_bot,
                    "isConnected": p.is_connected,
                    "points": p.points,
                    "hasAccusedThisRound": p.has_accused_this_round
                }
                for p in self.players
            ],
            "currentTurn": self.current_turn,
            "location": self.location.name if self.location else None,
            "availableLocations": [loc.name for loc in LOCATIONS],
            "events": [
                {
                    "type": e.type,
                    "playerId": e.player_id,
                    "content": e.content,
                    "timestamp": e.timestamp,
                    "formattedText": e.formatted_text
                }
                for e in self.events
            ],
            "clockStopped": self.clock_stopped,
            "lastQuestionedBy": self.last_questioned_by,
            "qaRoundsCompleted": self.qa_rounds_completed,
            "maxQaRounds": self.max_qa_rounds,
            "currentAccusation": {
                "accuser": self.current_accusation.accuser_id,
                "accused": self.current_accusation.accused_id,
                "votes": self.current_accusation.votes
            } if self.current_accusation else None,
            "winner": self.winner,
            "endReason": self.end_reason.value if self.end_reason else None,
            "spyId": self.spy_id if self.status == GameStatus.FINISHED else None,
            "timer": self.timer.to_dict()
        }

    def to_player_dict(self, player_id: str) -> Dict[str, Any]:
        """Convert game to dictionary with player-specific information."""
        base_dict = self.to_dict()

        # Find the requesting player
        player = next((p for p in self.players if p.id == player_id), None)
        if not player:
            return base_dict

        # Add player-specific role information
        base_dict["isSpy"] = player.role == PlayerRole.SPY
        base_dict["role"] = player.location_role if player.role == PlayerRole.INNOCENT else None
        if player.role == PlayerRole.SPY and self.status != GameStatus.FINISHED:
            base_dict["location"] = None

        return base_dict
