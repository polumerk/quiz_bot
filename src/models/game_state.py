"""
Game state management
"""

import time
from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass, field

from .types import (
    ChatID, UserID, MessageID, GameMode, Difficulty, 
    GameSettings, Question, Participant, Answer
)


@dataclass
class GameState:
    """Complete game state for a chat"""
    # Game configuration
    settings: Optional[GameSettings] = None
    
    # Participants and roles
    participants: Set[Participant] = field(default_factory=set)
    captain_id: Optional[UserID] = None
    session_admin: Optional[Participant] = None
    
    # Game progress
    current_round: int = 1
    question_index: int = 0
    questions: List[Question] = field(default_factory=list)
    answers: List[str] = field(default_factory=list)
    
    # Scoring
    total_score: int = 0
    total_fast_bonus: int = 0
    
    # State flags
    awaiting_theme: bool = False
    awaiting_answer: bool = False
    awaiting_text_answer: bool = False
    
    # Current question state
    current_question: Optional[Question] = None
    question_start_time: Optional[float] = None
    current_question_message_id: Optional[MessageID] = None
    
    # UI state
    service_messages: List[MessageID] = field(default_factory=list)

    def add_participant(self, user_id: UserID, username: str) -> None:
        """Add a participant to the game"""
        participant = Participant(user_id=user_id, username=username)
        self.participants.add(participant)

    def remove_participant(self, user_id: UserID) -> bool:
        """Remove a participant from the game"""
        for participant in self.participants:
            if participant.user_id == user_id:
                self.participants.remove(participant)
                return True
        return False

    def get_participant(self, user_id: UserID) -> Optional[Participant]:
        """Get participant by user ID"""
        for participant in self.participants:
            if participant.user_id == user_id:
                return participant
        return None

    def set_captain(self, user_id: UserID) -> bool:
        """Set captain if participant exists"""
        if self.get_participant(user_id):
            self.captain_id = user_id
            return True
        return False

    def add_answer(self, answer: str) -> None:
        """Add an answer to the current round"""
        self.answers.append(answer)

    def add_score(self, points: int) -> None:
        """Add points to total score"""
        self.total_score += points

    def add_fast_bonus(self, bonus: int = 1) -> None:
        """Add fast answer bonus"""
        self.total_fast_bonus += bonus

    def next_question(self) -> None:
        """Move to next question"""
        self.question_index += 1
        self.current_question = None
        self.question_start_time = None
        self.awaiting_answer = False
        self.awaiting_text_answer = False

    def next_round(self) -> None:
        """Move to next round"""
        self.current_round += 1
        self.question_index = 0
        self.questions.clear()
        self.answers.clear()

    def start_question(self, question: Question) -> None:
        """Start a new question"""
        self.current_question = question
        self.question_start_time = time.time()
        self.awaiting_answer = True

    def calculate_answer_time(self) -> float:
        """Calculate time taken to answer current question"""
        if self.question_start_time is None:
            return 0.0
        return time.time() - self.question_start_time

    def is_fast_answer(self) -> bool:
        """Check if current answer qualifies for fast bonus"""
        if not self.settings or not self.question_start_time:
            return False
        
        answer_time = self.calculate_answer_time()
        fast_bonus_time = self.settings.get_fast_bonus_time()
        return answer_time <= fast_bonus_time

    def get_total_points(self) -> int:
        """Get total points (score + bonuses)"""
        return self.total_score + self.total_fast_bonus

    def reset(self) -> None:
        """Reset game state"""
        self.settings = None
        self.participants.clear()
        self.captain_id = None
        self.session_admin = None
        self.current_round = 1
        self.question_index = 0
        self.questions.clear()
        self.answers.clear()
        self.total_score = 0
        self.total_fast_bonus = 0
        self.awaiting_theme = False
        self.awaiting_answer = False
        self.awaiting_text_answer = False
        self.current_question = None
        self.question_start_time = None
        self.service_messages.clear()


# Global game state storage
_game_states: Dict[ChatID, GameState] = {}


def get_game_state(chat_id: ChatID) -> GameState:
    """Get or create game state for a chat"""
    if chat_id not in _game_states:
        _game_states[chat_id] = GameState()
    return _game_states[chat_id]


def reset_game_state(chat_id: ChatID) -> None:
    """Reset game state for a chat"""
    if chat_id in _game_states:
        _game_states[chat_id].reset()
    else:
        _game_states[chat_id] = GameState()


def has_game_state(chat_id: ChatID) -> bool:
    """Check if chat has active game state"""
    return chat_id in _game_states


def remove_game_state(chat_id: ChatID) -> None:
    """Remove game state for a chat"""
    if chat_id in _game_states:
        del _game_states[chat_id]


# Backward compatibility functions
def get_participants(chat_id: ChatID) -> Set[Participant]:
    """Get participants set (backward compatibility)"""
    return get_game_state(chat_id).participants


def get_captain(chat_id: ChatID) -> Optional[UserID]:
    """Get captain ID (backward compatibility)"""
    return get_game_state(chat_id).captain_id


def set_captain(chat_id: ChatID, user_id: UserID) -> None:
    """Set captain (backward compatibility)"""
    get_game_state(chat_id).set_captain(user_id)


def get_round(chat_id: ChatID) -> int:
    """Get current round (backward compatibility)"""
    return get_game_state(chat_id).current_round


def set_round(chat_id: ChatID, value: int) -> None:
    """Set current round (backward compatibility)"""
    get_game_state(chat_id).current_round = value


def get_question_index(chat_id: ChatID) -> int:
    """Get question index (backward compatibility)"""
    return get_game_state(chat_id).question_index


def set_question_index(chat_id: ChatID, value: int) -> None:
    """Set question index (backward compatibility)"""
    get_game_state(chat_id).question_index = value


def get_questions(chat_id: ChatID) -> List[Question]:
    """Get questions list (backward compatibility)"""
    return get_game_state(chat_id).questions


def set_questions(chat_id: ChatID, questions: List[Question]) -> None:
    """Set questions list (backward compatibility)"""
    get_game_state(chat_id).questions = questions


def get_answers(chat_id: ChatID) -> List[str]:
    """Get answers list (backward compatibility)"""
    return get_game_state(chat_id).answers


def add_answer(chat_id: ChatID, answer: str) -> None:
    """Add answer (backward compatibility)"""
    get_game_state(chat_id).add_answer(answer)


def get_total_score(chat_id: ChatID) -> int:
    """Get total score (backward compatibility)"""
    return get_game_state(chat_id).total_score


def add_to_total_score(chat_id: ChatID, value: int) -> None:
    """Add to total score (backward compatibility)"""
    get_game_state(chat_id).add_score(value)


def get_total_fast_bonus(chat_id: ChatID) -> int:
    """Get total fast bonus (backward compatibility)"""
    return get_game_state(chat_id).total_fast_bonus


def add_to_total_fast_bonus(chat_id: ChatID, value: int) -> None:
    """Add to total fast bonus (backward compatibility)"""
    get_game_state(chat_id).add_fast_bonus(value)