"""Player models for Spyfall game"""
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class PlayerRole(Enum):
    SPY = "spy"
    INNOCENT = "innocent"


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
