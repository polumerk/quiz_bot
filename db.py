import sqlite3
from datetime import datetime

DB_PATH = 'quizbot.db'

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS questions_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            theme TEXT NOT NULL,
            question TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        conn.execute('''CREATE TABLE IF NOT EXISTS games (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            theme TEXT,
            started_at TIMESTAMP,
            finished_at TIMESTAMP,
            mode TEXT,
            winner_id INTEGER
        )''')
        conn.execute('''CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            total_score INTEGER DEFAULT 0,
            wins INTEGER DEFAULT 0
        )''')
        conn.execute('''CREATE TABLE IF NOT EXISTS answers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_id INTEGER,
            user_id INTEGER,
            question TEXT,
            answer_text TEXT,
            correct INTEGER,
            fast_bonus INTEGER,
            time_to_answer REAL
        )''')
        conn.execute('''CREATE TABLE IF NOT EXISTS game_participants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_id INTEGER,
            user_id INTEGER,
            username TEXT
        )''')
        conn.commit()

def get_questions_history(theme: str, limit: int = 50) -> list:
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute('SELECT question FROM questions_history WHERE theme=? ORDER BY id DESC LIMIT ?', (theme, limit))
        return [row[0] for row in c.fetchall()]

def add_question_to_history(theme: str, question: str):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute('INSERT INTO questions_history (theme, question) VALUES (?, ?)', (theme, question))
        conn.commit()

def get_last_game_id(chat_id):
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute('SELECT id FROM games WHERE chat_id=? ORDER BY id DESC LIMIT 1', (chat_id,))
        row = c.fetchone()
        return row[0] if row else None

def insert_answers(game_id, answers):
    with sqlite3.connect(DB_PATH) as conn:
        for ans in answers:
            conn.execute('''INSERT INTO answers (game_id, user_id, question, answer_text, correct, fast_bonus, time_to_answer)
                            VALUES (?, ?, ?, ?, ?, ?, ?)''',
                         (game_id, ans['user_id'], ans['question'], ans['answer_text'], ans['correct'], ans['fast_bonus'], ans['time_to_answer']))
        conn.commit()

def insert_game_participants(game_id, participants):
    with sqlite3.connect(DB_PATH) as conn:
        for uid, username in participants.items():
            conn.execute('INSERT INTO game_participants (game_id, user_id, username) VALUES (?, ?, ?)', (game_id, uid, username))
        conn.commit()

def update_user_stats(user_id, username, score, win=False):
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute('SELECT user_id FROM users WHERE user_id=?', (user_id,))
        if c.fetchone():
            c.execute('UPDATE users SET username=?, total_score=total_score+?, wins=wins+? WHERE user_id=?', (username, score, int(win), user_id))
        else:
            c.execute('INSERT INTO users (user_id, username, total_score, wins) VALUES (?, ?, ?, ?)', (user_id, username, score, int(win)))
        conn.commit()

def add_game_stat(chat_id, theme, mode, rounds, questions_per_round, winner_id):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute('''INSERT INTO games (chat_id, theme, started_at, finished_at, mode, winner_id)
                        VALUES (?, ?, ?, ?, ?, ?)''',
                     (chat_id, theme, datetime.now(), datetime.now(), mode, winner_id))
        conn.commit() 