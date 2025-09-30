from typing import List, Optional, Dict, Any, Set
from dataclasses import dataclass, field
import random
import time
from enum import Enum
from timer import GameTimer

class GameStatus(Enum):
    WAITING = "waiting"
    IN_PROGRESS = "in_progress"
    VOTING = "voting"
    END_OF_ROUND_VOTING = "end_of_round_voting"
    FINISHED = "finished"

class PlayerRole(Enum):
    SPY = "spy"
    INNOCENT = "innocent"

class GameEndReason(Enum):
    TIME_EXPIRED = "time_expired"
    SPY_ACCUSED = "spy_accused"
    INNOCENT_ACCUSED = "innocent_accused"
    SPY_GUESSED_LOCATION = "spy_guessed_location"
    SPY_FAILED_GUESS = "spy_failed_guess"

@dataclass
class Player:
    id: str
    name: str
    is_bot: bool = False
    is_connected: bool = True
    role: Optional[PlayerRole] = None
    location_role: Optional[str] = None  # Specific role at location (e.g., "Pilot")
    points: int = 0
    has_accused_this_round: bool = False  # Can only accuse once per round

@dataclass
class Location:
    name: str
    roles: List[str]

@dataclass
class Message:
    id: str
    type: str  # "question" or "answer"
    from_id: str
    to_id: Optional[str]  # None for answers
    content: str
    timestamp: float

@dataclass
class Accusation:
    accuser_id: str
    accused_id: str
    votes: Dict[str, bool] = field(default_factory=dict)  # player_id -> True/False
    timestamp: float = field(default_factory=time.time)
    is_active: bool = True

@dataclass
class Game:
    id: str
    players: List[Player] = field(default_factory=list)
    status: GameStatus = GameStatus.WAITING
    current_turn: Optional[str] = None
    location: Optional[Location] = None
    spy_id: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    messages: List[Message] = field(default_factory=list)
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

        # Create message
        message = Message(
            id=f"{time.time()}_{from_player_id}",
            type="question",
            from_id=from_player_id,
            to_id=to_player_id,
            content=content,
            timestamp=time.time()
        )
        self.messages.append(message)

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

        # Create answer message - answer goes back to the player who asked the question
        message = Message(
            id=f"{time.time()}_{from_player_id}",
            type="answer",
            from_id=from_player_id,
            to_id=self.last_questioned_by,
            content=content,
            timestamp=time.time()
        )
        self.messages.append(message)

        # Increment Q&A round counter (a round = question + answer)
        self.qa_rounds_completed += 1

        # Player can now ask the next question (turn stays with them)
        return True

    def stop_clock_for_accusation(self, accuser_id: str, accused_id: str) -> bool:
        """Player stops the clock to make an accusation."""
        if self.status != GameStatus.IN_PROGRESS or self.clock_stopped:
            return False

        # Check if player has already accused this round
        accuser = next((p for p in self.players if p.id == accuser_id), None)
        if not accuser or accuser.has_accused_this_round:
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

        accuser.has_accused_this_round = True
        return True

    def vote_on_accusation(self, voter_id: str, vote: bool) -> bool:
        """Player votes on the current accusation."""
        if self.status != GameStatus.VOTING or not self.current_accusation:
            return False

        # Accused player cannot vote
        if voter_id == self.current_accusation.accused_id:
            return False

        self.current_accusation.votes[voter_id] = vote

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

        if unanimous_guilty:
            # Accusation successful - reveal the accused player's role
            accused_player = next((p for p in self.players if p.id == self.current_accusation.accused_id), None)
            if accused_player:
                if accused_player.role == PlayerRole.SPY:
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

        # Check guess
        if guessed_location.lower() == self.location.name.lower():
            # Spy wins
            self._end_game(GameEndReason.SPY_GUESSED_LOCATION, "spy")
            # Spy gets 4 points
            spy = next((p for p in self.players if p.id == self.spy_id), None)
            if spy:
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
            # Time expired - start final accusation phase
            self._handle_time_expiry()
            return True

        return False

    def _handle_time_expiry(self):
        """Handle the end-of-time accusation phase."""
        # Start end-of-round accusation phase
        self._start_end_of_round_voting()

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

        # Find accuser
        accuser = next((p for p in self.players if p.id == accuser_id), None)
        if not accuser or accuser.has_accused_this_round:
            return False

        # Create accusation
        accusation = Accusation(
            accuser_id=accuser_id,
            accused_id=accused_id,
            votes={},
            is_active=True
        )

        self.accusations.append(accusation)
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
        if not voter:
            return False

        # Record vote
        accusation.votes[voter_id] = vote

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

        if all_votes_guilty and len(accusation.votes) > 0:
            # Unanimous guilty vote - reveal the accused
            accused = next((p for p in self.players if p.id == accusation.accused_id), None)
            if accused and accused.role == PlayerRole.SPY:
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
            # Not unanimous - move to next accuser
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
            "messages": [
                {
                    "id": m.id,
                    "type": m.type,
                    "from": m.from_id,
                    "to": m.to_id,
                    "content": m.content,
                    "timestamp": m.timestamp
                }
                for m in self.messages
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

# Game locations with their specific roles (from rulebook)
LOCATIONS = [
    Location("Airplane", ["Pilot", "Flight Attendant", "Passenger", "Air Marshal", "Mechanic", "Tourist", "Businessman"]),
    Location("Amusement Park", ["Ride Operator", "Parent", "Food Vendor", "Teenager", "Janitor", "Security Guard", "Mascot"]),
    Location("Bank", ["Teller", "Security Guard", "Manager", "Customer", "Robber", "Consultant", "Armored Car Driver"]),
    Location("Beach", ["Lifeguard", "Surfer", "Photographer", "Tourist", "Ice Cream Vendor", "Kite Surfer", "Beach Volleyball Player"]),
    Location("Carnival", ["Ring Toss Operator", "Visitor", "Fire Eater", "Fortune Teller", "Bouncer", "Candy Seller", "Clown"]),
    Location("Casino", ["Dealer", "Gambler", "Security", "Cocktail Waitress", "Pit Boss", "Card Counter", "Slot Machine Addict"]),
    Location("Circus Tent", ["Acrobat", "Animal Trainer", "Magician", "Fire Eater", "Clown", "Juggler", "Ringmaster"]),
    Location("Corporate Party", ["CEO", "Manager", "Employee", "Secretary", "Security", "Bartender", "Caterer"]),
    Location("Crusader Army", ["Knight", "Archer", "Priest", "Peasant", "Squire", "Cook", "Prisoner"]),
    Location("Day Spa", ["Masseuse", "Customer", "Dermatologist", "Beautician", "Receptionist", "Aromatherapist", "Manicurist"]),
    Location("Embassy", ["Ambassador", "Security Officer", "Tourist", "Refugee", "Diplomat", "Government Official", "Secretary"]),
    Location("Hospital", ["Doctor", "Nurse", "Patient", "Surgeon", "Anesthesiologist", "Intern", "Therapist"]),
    Location("Hotel", ["Guest", "Bellhop", "Manager", "Housekeeper", "Bartender", "Doorman", "Concierge"]),
    Location("Military Base", ["Soldier", "Medic", "Engineer", "Sniper", "Officer", "Tank Operator", "Radioman"]),
    Location("Movie Studio", ["Director", "Actor", "Cameraman", "Producer", "Sound Engineer", "Stuntman", "Make-up Artist"]),
    Location("Nightclub", ["DJ", "Bouncer", "Dancer", "Bartender", "VIP", "Party Girl", "Waiter"]),
    Location("Ocean Liner", ["Captain", "Bartender", "Musician", "Wealthy Passenger", "Poor Passenger", "Waiter", "Lifeguard"]),
    Location("Passenger Train", ["Mechanic", "Border Patrol", "Passenger", "Restaurant Chef", "Engineer", "Stoker", "Conductor"]),
    Location("Pirate Ship", ["Captain", "Mate", "Cabin Boy", "Gunner", "Cook", "Prisoner", "Sailor"]),
    Location("Police Station", ["Detective", "Lawyer", "Journalist", "Criminalist", "Archivist", "Patrol Officer", "Criminal"]),
    Location("Polar Station", ["Medic", "Expedition Leader", "Biologist", "Radioman", "Hydrologist", "Meteorologist", "Geologist"]),
    Location("Restaurant", ["Musician", "Customer", "Bouncer", "Hostess", "Head Chef", "Food Critic", "Waiter"]),
    Location("School", ["Gym Teacher", "Student", "Principal", "Security Guard", "Janitor", "Lunch Lady", "Maintenance Man"]),
    Location("Service Station", ["Manager", "Tire Specialist", "Biker", "Car Owner", "Car Wash Operator", "Electrician", "Auto Mechanic"]),
    Location("Space Station", ["Engineer", "Alien", "Space Tourist", "Pilot", "Commander", "Scientist", "Doctor"]),
    Location("Submarine", ["Cook", "Commander", "Sonar Technician", "Electronics Specialist", "Sailor", "Radioman", "Navigator"]),
    Location("Supermarket", ["Customer", "Cashier", "Butcher", "Janitor", "Security Guard", "Food Sample Demonstrator", "Shelf Stocker"]),
    Location("Theater", ["Coat Check Lady", "Prompter", "Cashier", "Director", "Actor", "Crewman", "Audience Member"]),
    Location("University", ["Graduate Student", "Professor", "Dean", "Psychologist", "Maintenance Man", "Student", "Janitor"]),
    Location("Zoo", ["Zookeeper", "Visitor", "Photographer", "Child", "Veterinarian", "Tour Guide", "Security Guard"])
]
