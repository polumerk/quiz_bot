"""
Type definitions for Quiz Bot
"""

from enum import Enum
from typing import Dict, List, Optional, Set, Tuple, Any, NamedTuple
from dataclasses import dataclass
from datetime import datetime


class GameMode(Enum):
    """Game mode enumeration"""
    TEAM = "team"
    INDIVIDUAL = "individual"


class Difficulty(Enum):
    """Question difficulty levels"""
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


@dataclass
class GameSettings:
    """Game configuration settings"""
    mode: GameMode
    difficulty: Difficulty
    rounds: int
    questions_per_round: int
    time_per_question: int
    theme: str
    language: str = "ru"

    def get_fast_bonus_time(self) -> int:
        """Calculate time threshold for fast bonus"""
        return max(1, int(self.time_per_question * 0.2))


@dataclass
class Question:
    """Question data structure"""
    question: str
    correct_answer: str
    difficulty: Difficulty
    explanation: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for compatibility"""
        return {
            'question': self.question,
            'correct_answer': self.correct_answer,
            'difficulty': self.difficulty.value,
            'explanation': self.explanation
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Question':
        """Create Question from dictionary"""
        return cls(
            question=data['question'],
            correct_answer=data.get('answer', data.get('correct_answer', '')),
            difficulty=Difficulty(data.get('difficulty', 'medium')),
            explanation=data.get('explanation', '')
        )


@dataclass
class Answer:
    """Answer data structure"""
    user_id: int
    username: str
    answer_text: str
    is_correct: bool
    time_to_answer: float
    fast_bonus: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            'user_id': self.user_id,
            'username': self.username,
            'answer_text': self.answer_text,
            'correct': self.is_correct,
            'time_to_answer': self.time_to_answer,
            'fast_bonus': self.fast_bonus
        }


@dataclass
class Participant:
    """Game participant"""
    user_id: int
    username: str
    
    def __hash__(self) -> int:
        return hash(self.user_id)
    
    def __eq__(self, other: object) -> bool:
        if isinstance(other, Participant):
            return self.user_id == other.user_id
        return False

    def to_tuple(self) -> Tuple[int, str]:
        """Convert to tuple for compatibility with old code"""
        return (self.user_id, self.username)

    @classmethod
    def from_tuple(cls, data: Tuple[int, str]) -> 'Participant':
        """Create from tuple for compatibility"""
        return cls(user_id=data[0], username=data[1])


@dataclass
class GameResult:
    """Round or game result"""
    question: Question
    answer: Answer
    explanation: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for display"""
        return {
            'question': self.question.question,
            'answer': self.answer.answer_text,
            'correct': self.answer.is_correct,
            'correct_answer': self.question.correct_answer,
            'explanation': self.explanation or self.question.explanation
        }


class ChatID(int):
    """Type alias for chat ID"""
    pass


class UserID(int):
    """Type alias for user ID"""
    pass


class MessageID(int):
    """Type alias for message ID"""
    pass


# Type aliases for backward compatibility
ParticipantTuple = Tuple[int, str]
ScoreDict = Dict[int, int]
ExplanationDict = Dict[int, List[Dict[str, Any]]]