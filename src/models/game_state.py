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
    # questions: List[Question] = field(default_factory=list)  # Удалено для ленивой генерации
    answers: List[str] = field(default_factory=list)
    
    # Store all answers by question index for results display
    all_question_answers: Dict[int, Dict[UserID, Answer]] = field(default_factory=dict)
    
    # Scoring
    total_score: int = 0
    total_fast_bonus: int = 0
    
    # State flags
    awaiting_theme: bool = False
    awaiting_answer: bool = False
    awaiting_text_answer: bool = False
    awaiting_language: bool = False
    is_generating_question: bool = False  # Новый флаг для асинхронной генерации
    
    # Current question state
    current_question: Optional[Question] = None
    question_start_time: Optional[float] = None
    current_question_message_id: Optional[MessageID] = None
    current_question_id: Optional[str] = None  # Unique ID for timeout tracking
    current_question_answers: Dict[UserID, Answer] = field(default_factory=dict)  # Track answers per user
    
    # UI state for unified settings
    settings_message_id: Optional[MessageID] = None
    registration_message_id: Optional[MessageID] = None
    in_registration_mode: bool = False
    
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
        # Save current question answers before clearing
        if self.current_question_answers:
            self.all_question_answers[self.question_index] = self.current_question_answers.copy()
        
        self.question_index += 1
        self.current_question = None
        self.question_start_time = None
        self.current_question_id = None
        self.current_question_answers.clear()  # Clear answers for new question
        self.awaiting_answer = False
        self.awaiting_text_answer = False
        self.is_generating_question = False  # Сброс флага генерации

    def next_round(self) -> None:
        """Move to next round"""
        self.current_round += 1
        self.question_index = 0
        # self.questions.clear()  # Удалено
        self.answers.clear()
        self.all_question_answers.clear()  # Clear stored answers for new round
        self.current_question = None
        self.is_generating_question = False

    def start_question(self, question: Question) -> str:
        """Start a new question and return unique question ID"""
        import uuid
        question_id = str(uuid.uuid4())[:8]  # Short unique ID
        
        self.current_question = question
        self.question_start_time = time.time()
        self.current_question_id = question_id
        self.awaiting_answer = True
        
        return question_id

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

    def add_user_answer(self, user_id: UserID, username: str, answer_text: str, is_correct: bool) -> None:
        """Add answer from specific user for current question"""
        if not self.current_question:
            return
        
        answer_time = self.calculate_answer_time()
        fast_bonus = is_correct and self.is_fast_answer()
        
        answer = Answer(
            user_id=user_id,
            username=username,
            answer_text=answer_text,
            is_correct=is_correct,
            time_to_answer=answer_time,
            fast_bonus=fast_bonus
        )
        
        self.current_question_answers[user_id] = answer

    def has_user_answered(self, user_id: UserID) -> bool:
        """Check if user has already answered current question"""
        return user_id in self.current_question_answers

    def get_unanswered_participants(self) -> Set[Participant]:
        """Get participants who haven't answered current question yet"""
        answered_users = set(self.current_question_answers.keys())
        return {p for p in self.participants if p.user_id not in answered_users}

    def all_participants_answered(self) -> bool:
        """Check if all participants have answered current question"""
        if not self.participants:
            return False
        return len(self.current_question_answers) >= len(self.participants)

    def should_wait_for_more_answers(self) -> bool:
        """Determine if we should wait for more answers"""
        # In team mode, only captain answers
        if self.settings and self.settings.mode == GameMode.TEAM:
            return len(self.current_question_answers) == 0
        
        # In individual mode, wait for all participants
        return not self.all_participants_answered()

    def reset(self) -> None:
        """Reset game state"""
        self.settings = None
        self.participants.clear()
        self.captain_id = None
        self.session_admin = None
        self.current_round = 1
        self.question_index = 0
        # self.questions.clear() # Удалено
        self.answers.clear()
        self.total_score = 0
        self.total_fast_bonus = 0
        self.awaiting_theme = False
        self.awaiting_answer = False
        self.awaiting_text_answer = False
        self.awaiting_language = False
        self.current_question = None
        self.question_start_time = None
        self.current_question_id = None
        self.current_question_answers.clear()
        self.all_question_answers.clear() # Clear stored answers on reset
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