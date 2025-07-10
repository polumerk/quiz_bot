"""
Type definitions for Quiz Bot
"""

from enum import Enum
from typing import Dict, List, Optional, Set, Tuple, Any, NamedTuple
from dataclasses import dataclass, field
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
    interesting_fact: str = ""  # Новое поле для интересного факта
    source_type: str = "general"  # Новое поле для типа источника
    difficulty_level: int = 5  # Новое поле для численной оценки сложности (1-10)
    tags: List[str] = field(default_factory=list)  # Новое поле для тегов

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for compatibility"""
        return {
            'question': self.question,
            'correct_answer': self.correct_answer,
            'difficulty': self.difficulty.value,
            'explanation': self.explanation,
            'interesting_fact': self.interesting_fact,
            'source_type': self.source_type,
            'difficulty_level': self.difficulty_level,
            'tags': self.tags
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Question':
        """Create Question from dictionary"""
        if not isinstance(data, dict):
            raise ValueError(f"Expected dict, got {type(data)}: {data}")
        
        if 'question' not in data:
            raise ValueError(f"Question data missing 'question' field: {data}")
        
        question = data['question']
        if not question or not isinstance(question, str):
            raise ValueError(f"Question field must be non-empty string: {question}")
        
        # Get answer from different possible fields
        correct_answer = data.get('answer', data.get('correct_answer', ''))
        if not correct_answer:
            # If no answer provided, use a default
            correct_answer = 'Не указан'
        
        # Parse difficulty safely
        difficulty_str = data.get('difficulty', 'medium')
        try:
            difficulty = Difficulty(difficulty_str)
        except ValueError:
            difficulty = Difficulty.MEDIUM
        
        return cls(
            question=question,
            correct_answer=correct_answer,
            difficulty=difficulty,
            explanation=data.get('explanation', ''),
            interesting_fact=data.get('interesting_fact', ''),
            source_type=data.get('source_type', 'general'),
            difficulty_level=data.get('difficulty_level', 5),
            tags=data.get('tags', [])
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