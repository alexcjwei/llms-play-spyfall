"""Message and accusation models for Spyfall game"""
from dataclasses import dataclass, field
from typing import Optional, Dict
import time


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
