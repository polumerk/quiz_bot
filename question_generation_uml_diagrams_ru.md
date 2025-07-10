# 🎯 UML Диаграммы и схемы Quiz Bot 2.0

## 📐 Диаграмма классов

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            CLASS DIAGRAM                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                           MODELS LAYER                                  ││
│  │                                                                         ││
│  │  ┌─────────────────────┐   ┌─────────────────────┐   ┌─────────────────┐││
│  │  │     GameState       │   │     Question        │   │   Participant   │││
│  │  │                     │   │                     │   │                 │││
│  │  │ - settings          │   │ - question: str     │   │ - user_id: int  │││
│  │  │ - participants      │   │ - correct_answer    │   │ - username: str │││
│  │  │ - current_round     │   │ - difficulty        │   │                 │││
│  │  │ - question_index    │   │ - explanation       │   │ + __hash__()    │││
│  │  │ - questions[]       │   │                     │   │ + __eq__()      │││
│  │  │ - awaiting_answer   │   │ + from_dict()       │   │ + to_tuple()    │││
│  │  │                     │   │ + to_dict()         │   │                 │││
│  │  │ + add_participant() │   │                     │   │                 │││
│  │  │ + start_question()  │   │                     │   │                 │││
│  │  │ + next_question()   │   │                     │   │                 │││
│  │  │ + add_user_answer() │   │                     │   │                 │││
│  │  └─────────────────────┘   └─────────────────────┘   └─────────────────┘││
│  │                                                                         ││
│  │  ┌─────────────────────┐   ┌─────────────────────┐   ┌─────────────────┐││
│  │  │    GameSettings     │   │       Answer        │   │   GameResult    │││
│  │  │                     │   │                     │   │                 │││
│  │  │ - mode: GameMode    │   │ - user_id: int      │   │ - question      │││
│  │  │ - difficulty        │   │ - username: str     │   │ - answer        │││
│  │  │ - rounds: int       │   │ - answer_text: str  │   │ - explanation   │││
│  │  │ - questions_per_r   │   │ - is_correct: bool  │   │                 │││
│  │  │ - time_per_question │   │ - time_to_answer    │   │ + to_dict()     │││
│  │  │ - theme: str        │   │ - fast_bonus: bool  │   │                 │││
│  │  │                     │   │                     │   │                 │││
│  │  │ + get_fast_bonus()  │   │ + to_dict()         │   │                 │││
│  │  └─────────────────────┘   └─────────────────────┘   └─────────────────┘││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                         GAME LOGIC LAYER                                ││
│  │                                                                         ││
│  │  ┌─────────────────────┐   ┌─────────────────────┐   ┌─────────────────┐││
│  │  │    game.logic       │   │    questions.py     │   │  handlers.*     │││
│  │  │                     │   │                     │   │                 │││
│  │  │ + start_round()     │   │ + openai_generate   │   │ + commands      │││
│  │  │ + ask_next_quest()  │   │ + build_openai_prmt │   │ + callbacks     │││
│  │  │ + question_timeout()│   │ + openai_check_ans  │   │ + messages      │││
│  │  │ + finish_round()    │   │                     │   │                 │││
│  │  │                     │   │                     │   │                 │││
│  │  └─────────────────────┘   └─────────────────────┘   └─────────────────┘││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                         DATA STORAGE LAYER                             ││
│  │                                                                         ││
│  │  ┌─────────────────────┐   ┌─────────────────────┐   ┌─────────────────┐││
│  │  │       db.py         │   │  questions_history  │   │   game_states   │││
│  │  │                     │   │                     │   │                 │││
│  │  │ + init_db()         │   │ - id                │   │ - chat_id       │││
│  │  │ + get_questions_h() │   │ - theme             │   │ - game_state    │││
│  │  │ + add_question_h()  │   │ - question          │   │                 │││
│  │  │ + get_last_game()   │   │ - created_at        │   │                 │││
│  │  │ + insert_answers()  │   │                     │   │                 │││
│  │  │ + update_stats()    │   │                     │   │                 │││
│  │  └─────────────────────┘   └─────────────────────┘   └─────────────────┘││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 🔄 Диаграмма последовательности генерации вопросов

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        QUESTION GENERATION SEQUENCE                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  User        Bot         GameLogic    Questions     OpenAI      Database    │
│   │           │             │            │           │            │         │
│   │ /start    │             │            │           │            │         │
│   │──────────▶│             │            │           │            │         │
│   │           │ setup_game()│            │           │            │         │
│   │           │────────────▶│            │           │            │         │
│   │           │             │get_history()          │            │         │
│   │           │             │───────────────────────────────────▶│         │
│   │           │             │            │           │    history│         │
│   │           │             │            │           │◀───────────         │
│   │           │             │start_round()          │            │         │
│   │           │             │────────────▶│          │            │         │
│   │           │             │             │generate_ │            │         │
│   │           │             │             │questions()            │         │
│   │           │             │             │──────────▶│           │         │
│   │           │             │             │           │ API call  │         │
│   │           │             │             │           │────────▶ │         │
│   │           │             │             │           │◀──────── │         │
│   │           │             │             │           │ response  │         │
│   │           │             │             │◀──────────│           │         │
│   │           │             │             │parse &    │           │         │
│   │           │             │             │validate   │           │         │
│   │           │             │◀────────────│           │           │         │
│   │           │             │save_to_history()       │           │         │
│   │           │             │───────────────────────────────────▶│         │
│   │           │             │ask_next_question()     │           │         │
│   │           │             │────────────▶│          │           │         │
│   │           │ display_q() │             │          │           │         │
│   │           │◀────────────│             │          │           │         │
│   │◀──────────│             │             │          │           │         │
│   │ "Question"│             │             │          │           │         │
│   │           │             │             │          │           │         │
│   │ reply     │             │             │          │           │         │
│   │──────────▶│             │             │          │           │         │
│   │           │ answer_handler()          │          │           │         │
│   │           │────────────▶│             │          │           │         │
│   │           │             │check_answer()          │           │         │
│   │           │             │────────────▶│          │           │         │
│   │           │             │             │fuzzy_match()        │         │
│   │           │             │             │──────────▶│         │         │
│   │           │             │             │◀──────────│         │         │
│   │           │             │◀────────────│          │         │         │
│   │           │             │update_scores()         │         │         │
│   │           │             │────────────▶│          │         │         │
│   │           │             │save_answer()           │         │         │
│   │           │             │───────────────────────────────────▶│         │
│   │           │ confirm()   │             │          │         │         │
│   │           │◀────────────│             │          │         │         │
│   │◀──────────│             │             │          │         │         │
│   │           │             │             │          │         │         │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 🎮 Диаграмма состояний игры

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                             GAME STATE DIAGRAM                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌─────────────┐     /start      ┌─────────────────┐                      │
│   │    IDLE     │ ─────────────── ▶│    SETTINGS     │                      │
│   │             │                  │                 │                      │
│   └─────────────┘                  │ • Mode          │                      │
│                                    │ • Difficulty    │                      │
│                                    │ • Rounds        │                      │
│                                    │ • Questions     │                      │
│                                    │ • Time          │                      │
│                                    │ • Theme         │                      │
│                                    └─────────────────┘                      │
│                                             │                              │
│                                             │ complete                     │
│                                             ▼                              │
│                                    ┌─────────────────┐                      │
│                                    │  REGISTRATION   │                      │
│                                    │                 │                      │
│                                    │ • Join/Leave    │                      │
│                                    │ • Captain       │                      │
│                                    │ • Countdown     │                      │
│                                    └─────────────────┘                      │
│                                             │                              │
│                                             │ start_game                   │
│                                             ▼                              │
│       ┌─────────────────┐           ┌─────────────────┐                      │
│       │   GENERATING    │◀──────────│   ROUND_START   │                      │
│       │   QUESTIONS     │           │                 │                      │
│       │                 │           │ • Generate Q's  │                      │
│       │ • OpenAI call   │           │ • Setup state   │                      │
│       │ • Validation    │           │ • Participants  │                      │
│       │ • Parsing       │           └─────────────────┘                      │
│       └─────────────────┘                    │                              │
│                │                             │                              │
│                │ questions_ready             │                              │
│                ▼                             │                              │
│       ┌─────────────────┐                    │                              │
│       │   ASKING        │◀───────────────────┘                              │
│       │   QUESTION      │                                                   │
│       │                 │                                                   │
│       │ • Display Q     │                                                   │
│       │ • Start timer   │                                                   │
│       │ • Await answers │                                                   │
│       └─────────────────┘                                                   │
│                │                                                           │
│                │ answer_received                                           │
│                ▼                                                           │
│       ┌─────────────────┐                                                   │
│       │   PROCESSING    │                                                   │
│       │   ANSWERS       │                                                   │
│       │                 │                                                   │
│       │ • Fuzzy match   │                                                   │
│       │ • Score calc    │                                                   │
│       │ • Fast bonus    │                                                   │
│       └─────────────────┘                                                   │
│                │                                                           │
│                │ all_answered                                              │
│                ▼                                                           │
│       ┌─────────────────┐         ┌─────────────────┐                      │
│       │   NEXT_QUESTION │──────── ▶│   ROUND_END     │                      │
│       │                 │more_q's  │                 │                      │
│       │ • Q index++     │         │ • Show results  │                      │
│       │ • Continue      │         │ • Statistics    │                      │
│       └─────────────────┘         │ • Next round?   │                      │
│                │                  └─────────────────┘                      │
│                │                           │                              │
│                └───────────────────────────┘                              │
│                       next_question        │ more_rounds                   │
│                                           ▼                              │
│                                  ┌─────────────────┐                      │
│                                  │   GAME_END      │                      │
│                                  │                 │                      │
│                                  │ • Final results │                      │
│                                  │ • Rankings      │                      │
│                                  │ • Statistics    │                      │
│                                  └─────────────────┘                      │
│                                           │                              │
│                                           │ cleanup                      │
│                                           ▼                              │
│                                  ┌─────────────────┐                      │
│                                  │     IDLE        │                      │
│                                  │                 │                      │
│                                  │ Ready for new   │                      │
│                                  │ game            │                      │
│                                  └─────────────────┘                      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 🧠 Диаграмма компонентов OpenAI Integration

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         OPENAI INTEGRATION COMPONENTS                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                        PROMPT ENGINEERING                               ││
│  │                                                                         ││
│  │  ┌─────────────────────┐   ┌─────────────────────┐   ┌─────────────────┐││
│  │  │   SYSTEM_PROMPT     │   │   build_openai_     │   │   EXAMPLES      │││
│  │  │                     │   │   prompt()          │   │                 │││
│  │  │ "Ты AI-ведущий      │   │                     │   │ GOOD_QUESTION   │││
│  │  │ интеллектуального   │   │ • Theme injection   │   │ BAD_QUESTION    │││
│  │  │ квиза. Генерируй    │   │ • Difficulty setup  │   │                 │││
│  │  │ только однозначные  │   │ • History avoidance │   │                 │││
│  │  │ вопросы..."         │   │ • Format enforce    │   │                 │││
│  │  └─────────────────────┘   └─────────────────────┘   └─────────────────┘││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                          API INTERACTION                                ││
│  │                                                                         ││
│  │  ┌─────────────────────┐   ┌─────────────────────┐   ┌─────────────────┐││
│  │  │   Request Builder   │   │   Response Parser   │   │   Error Handler │││
│  │  │                     │   │                     │   │                 │││
│  │  │ • Model: gpt-4o     │   │ • JSON extraction   │   │ • HTTP errors   │││
│  │  │ • Max tokens: 1024  │   │ • Validation        │   │ • API errors    │││
│  │  │ • Temperature: 0.2  │   │ • Duplicate check   │   │ • Fallbacks     │││
│  │  │ • Headers setup     │   │ • Question objects  │   │ • Retry logic   │││
│  │  └─────────────────────┘   └─────────────────────┘   └─────────────────┘││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                        HISTORY MANAGEMENT                               ││
│  │                                                                         ││
│  │  ┌─────────────────────┐   ┌─────────────────────┐   ┌─────────────────┐││
│  │  │   get_questions_    │   │   add_question_     │   │   Duplicate     │││
│  │  │   history()         │   │   to_history()      │   │   Prevention    │││
│  │  │                     │   │                     │   │                 │││
│  │  │ • Theme filter      │   │ • Insert new Q      │   │ • Normalize     │││
│  │  │ • Limit recent      │   │ • Timestamp         │   │ • Compare       │││
│  │  │ • Return list       │   │ • Theme tag         │   │ • Filter        │││
│  │  └─────────────────────┘   └─────────────────────┘   └─────────────────┘││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 🎯 Диаграмма обработки ответов

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           ANSWER PROCESSING FLOW                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  User Reply ──────────────────────────────────────────────────────────────┐ │
│      │                                                                   │ │
│      ▼                                                                   │ │
│  ┌─────────────────────┐                                                 │ │
│  │   Message Handler   │                                                 │ │
│  │                     │                                                 │ │
│  │ • Check if reply    │                                                 │ │
│  │ • Validate user     │                                                 │ │
│  │ • Check answered    │                                                 │ │
│  │ • Team mode check   │                                                 │ │
│  └─────────────────────┘                                                 │ │
│            │                                                             │ │
│            ▼                                                             │ │
│  ┌─────────────────────┐     ┌─────────────────────┐                    │ │
│  │   is_answer_        │────▶│   normalize_answer  │                    │ │
│  │   correct()         │     │                     │                    │ │
│  │                     │     │ • Lower case        │                    │ │
│  │ Main logic entry    │     │ • Strip whitespace  │                    │ │
│  └─────────────────────┘     │ • Replace ё→е       │                    │ │
│            │                 │ • Replace й→и       │                    │ │
│            ▼                 └─────────────────────┘                    │ │
│  ┌─────────────────────┐                                                 │ │
│  │   Exact Match       │                                                 │ │
│  │                     │                                                 │ │
│  │ user_norm ==        │                                                 │ │
│  │ correct_norm        │                                                 │ │
│  └─────────────────────┘                                                 │ │
│            │                                                             │ │
│            ▼ (if not exact)                                              │ │
│  ┌─────────────────────┐                                                 │ │
│  │   Length Check      │                                                 │ │
│  │                     │                                                 │ │
│  │ Both >= 3 chars     │                                                 │ │
│  │ else return False   │                                                 │ │
│  └─────────────────────┘                                                 │ │
│            │                                                             │ │
│            ▼                                                             │ │
│  ┌─────────────────────┐                                                 │ │
│  │   High Similarity   │                                                 │ │
│  │                     │                                                 │ │
│  │ SequenceMatcher     │                                                 │ │
│  │ similarity >= 0.85  │                                                 │ │
│  └─────────────────────┘                                                 │ │
│            │                                                             │ │
│            ▼ (if not high similarity)                                    │ │
│  ┌─────────────────────┐                                                 │ │
│  │   Word Containment  │                                                 │ │
│  │                     │                                                 │ │
│  │ user_norm in        │                                                 │ │
│  │ correct_norm OR     │                                                 │ │
│  │ correct_norm in     │                                                 │ │
│  │ user_norm           │                                                 │ │
│  └─────────────────────┘                                                 │ │
│            │                                                             │ │
│            ▼ (if not contained)                                          │ │
│  ┌─────────────────────┐                                                 │ │
│  │   Word Intersection │                                                 │ │
│  │                     │                                                 │ │
│  │ Split into words    │                                                 │ │
│  │ Check if all user   │                                                 │ │
│  │ words are in        │                                                 │ │
│  │ correct OR vice     │                                                 │ │
│  │ versa               │                                                 │ │
│  └─────────────────────┘                                                 │ │
│            │                                                             │ │
│            ▼ (if no intersection)                                        │ │
│  ┌─────────────────────┐                                                 │ │
│  │   Individual Word   │                                                 │ │
│  │   Similarity        │                                                 │ │
│  │                     │                                                 │ │
│  │ For each word pair  │                                                 │ │
│  │ check if similarity │                                                 │ │
│  │ >= 0.85             │                                                 │ │
│  └─────────────────────┘                                                 │ │
│            │                                                             │ │
│            ▼                                                             │ │
│  ┌─────────────────────┐                                                 │ │
│  │   Result & Scoring  │                                                 │ │
│  │                     │                                                 │ │
│  │ • Store answer      │                                                 │ │
│  │ • Calculate time    │                                                 │ │
│  │ • Fast bonus check  │                                                 │ │
│  │ • Update scores     │                                                 │ │
│  └─────────────────────┘                                                 │ │
│            │                                                             │ │
│            ▼                                                             │ │
│  ┌─────────────────────┐                                                 │ │
│  │   Response to User  │                                                 │ │
│  │                     │                                                 │ │
│  │ • Confirmation      │                                                 │ │
│  │ • Wait status       │                                                 │ │
│  │ • Next question     │                                                 │ │
│  └─────────────────────┘                                                 │ │
│                                                                          │ │
│                                                                          │ │
│  ┌─────────────────────────────────────────────────────────────────────┐ │ │
│  │                        EXAMPLE CASES                                │ │ │
│  │                                                                     │ │ │
│  │  "Реал" + "Реал Мадрид" ────────────────────────────── ✅ MATCH     │ │ │
│  │  (Word containment: "реал" in "реал мадрид")                       │ │ │
│  │                                                                     │ │ │
│  │  "Месси" + "Лионель Месси" ────────────────────────── ✅ MATCH     │ │ │
│  │  (Word containment: "месси" in "лионель месси")                    │ │ │
│  │                                                                     │ │ │
│  │  "Гренландия" + "Гринландия" ─────────────────────── ✅ MATCH     │ │ │
│  │  (High similarity: 0.91 >= 0.85)                                   │ │ │
│  │                                                                     │ │ │
│  │  "Иван" + "Петр" ──────────────────────────────────── ❌ NO MATCH  │ │ │
│  │  (No similarity, containment, or intersection)                     │ │ │
│  └─────────────────────────────────────────────────────────────────────┘ │ │
│                                                                            │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 📋 Таблица API методов

| Компонент | Метод | Описание | Параметры |
|-----------|--------|----------|-----------|
| **questions.py** | `openai_generate_questions()` | Генерация вопросов через OpenAI | theme, round_num, chat_id, difficulty, questions_count |
| **questions.py** | `build_openai_prompt()` | Построение промпта для OpenAI | theme, round_num, questions_per_round, history_text, difficulty |
| **questions.py** | `openai_check_answers()` | Проверка ответов через OpenAI | theme, questions, answers |
| **game/logic.py** | `start_round()` | Запуск нового раунда | context, chat_id |
| **game/logic.py** | `ask_next_question()` | Показ следующего вопроса | context, chat_id |
| **game/logic.py** | `question_timeout()` | Обработка таймаута вопроса | context |
| **game/logic.py** | `finish_round()` | Завершение раунда | context, chat_id |
| **handlers/messages.py** | `answer_message_handler()` | Обработка ответов пользователей | update, context |
| **handlers/messages.py** | `is_answer_correct()` | Проверка правильности ответа | user_answer, correct_answer |
| **models/game_state.py** | `get_game_state()` | Получение состояния игры | chat_id |
| **models/game_state.py** | `add_user_answer()` | Добавление ответа пользователя | user_id, username, answer_text, is_correct |
| **db.py** | `get_questions_history()` | Получение истории вопросов | theme, limit |
| **db.py** | `add_question_to_history()` | Добавление вопроса в историю | theme, question |

---

**Дата создания диаграмм:** 2025-07-10  
**Версия:** Quiz Bot 2.0 UML  
**Статус:** ✅ Архитектурная документация