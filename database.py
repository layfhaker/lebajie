import sqlite3
import os
from config import DB_PATH, DATA_DIR, MAIN_ADMIN_ID


def get_connection():
    """Создать подключение к БД"""
    # Создаем папку data если она отсутствует
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Инициализация базы данных"""
    conn = get_connection()
    cursor = conn.cursor()

    # Таблица админов
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS admins (
            user_id INTEGER PRIMARY KEY,
            added_by INTEGER,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Таблица FAQ
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS faq (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Таблица реф-токенов
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ref_tokens (
            token TEXT PRIMARY KEY,
            created_by INTEGER NOT NULL,
            used INTEGER DEFAULT 0,
            used_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Таблица активных чатов поддержки
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS active_chats (
            user_id INTEGER PRIMARY KEY,
            in_support INTEGER DEFAULT 1,
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Добавляем главного админа если его нет
    cursor.execute('SELECT user_id FROM admins WHERE user_id = ?', (MAIN_ADMIN_ID,))
    if not cursor.fetchone():
        cursor.execute('INSERT INTO admins (user_id, added_by) VALUES (?, ?)', (MAIN_ADMIN_ID, MAIN_ADMIN_ID))

    # Добавляем FAQ по умолчанию если таблица пустая
    cursor.execute('SELECT COUNT(*) FROM faq')
    if cursor.fetchone()[0] == 0:
        default_faq = [
            (
                "Сколько стоит рыбалка?",
                "Дневная рыбалка — 1500 руб. (до 3-х кг), свыше 3-х кг — по 450 руб. за кг."
            ),
            (
                "Как добраться?",
                "Мы находимся у Лебяжьего озера.\n\n"
                "📍 Координаты: 44.576378, 33.957275\n"
                "🗺 Яндекс.Карты: https://yandex.ru/maps/-/CPAGZG2"
            ),
            (
                "Когда работает?",
                "Рыбалка работает с 9:00 до вечера. Территория доступна 24/7."
            ),
            (
                "Можно ли арендовать беседку?",
                "Да! Малые беседки (до 6 чел.) — 2000 ₽, большие (до 8 чел.) — 3000 ₽, VIP (до 15 чел.) — 10000 ₽."
            ),
            (
                "Есть ли домики для проживания?",
                "Да, есть домики на 4 человека: стандарт — 6000 ₽, улучшенный — 7000 ₽.\n"
                "В домике: двуспальная кровать + 2 односпальные, санузел, кухня, телевизор, кондиционер."
            ),
        ]
        cursor.executemany('INSERT INTO faq (question, answer) VALUES (?, ?)', default_faq)

    conn.commit()
    conn.close()

# === Админы ===

def get_admins():
    """Получить список админов"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT user_id FROM admins')
    admins = [row['user_id'] for row in cursor.fetchall()]
    conn.close()

    # Гарантируем наличие главного админа
    if MAIN_ADMIN_ID not in admins:
        admins.append(MAIN_ADMIN_ID)
    return admins


def is_admin(user_id):
    """Проверка, является ли пользователь админом"""
    return user_id in get_admins()


def add_admin(user_id, added_by=None):
    """Добавить админа"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('INSERT OR IGNORE INTO admins (user_id, added_by) VALUES (?, ?)', (user_id, added_by))
        conn.commit()
        return True
    except:
        return False
    finally:
        conn.close()


def remove_admin(user_id):
    """Удалить админа"""
    if user_id == MAIN_ADMIN_ID:
        return False

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM admins WHERE user_id = ?', (user_id,))
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0

# === FAQ ===

def get_faq():
    """Получить все FAQ"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, question, answer FROM faq ORDER BY id')
    faq = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return faq


def get_faq_by_id(faq_id):
    """Получить FAQ по ID"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, question, answer FROM faq WHERE id = ?', (faq_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def add_faq(question, answer):
    """Добавить FAQ"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO faq (question, answer) VALUES (?, ?)', (question, answer))
    conn.commit()
    faq_id = cursor.lastrowid
    conn.close()
    return faq_id


def remove_faq(faq_id):
    """Удалить FAQ по ID"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM faq WHERE id = ?', (faq_id,))
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0

# === Реф-токены ===

def generate_ref_token(admin_id):
    """Сгенерировать реферальный токен"""
    import secrets
    token = secrets.token_urlsafe(16)

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO ref_tokens (token, created_by) VALUES (?, ?)', (token, admin_id))
    conn.commit()
    conn.close()
    return token


def use_ref_token(token, user_id):
    """Использовать реферальный токен"""
    conn = get_connection()
    cursor = conn.cursor()

    # Проверяем токен
    cursor.execute('SELECT * FROM ref_tokens WHERE token = ? AND used = 0', (token,))
    row = cursor.fetchone()

    if not row:
        conn.close()
        return False

    # Отмечаем как использованный
    cursor.execute('UPDATE ref_tokens SET used = 1, used_by = ? WHERE token = ?', (user_id, token))
    conn.commit()
    conn.close()

    # Добавляем админа
    add_admin(user_id, row['created_by'])
    return True

# === Поддержка ===

def set_user_in_support(user_id, in_support=True):
    """Установить статус пользователя в поддержке"""
    conn = get_connection()
    cursor = conn.cursor()

    if in_support:
        cursor.execute('INSERT OR REPLACE INTO active_chats (user_id, in_support) VALUES (?, 1)', (user_id,))
    else:
        cursor.execute('DELETE FROM active_chats WHERE user_id = ?', (user_id,))

    conn.commit()
    conn.close()


def is_user_in_support(user_id):
    """Проверка, находится ли пользователь в режиме поддержки"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT in_support FROM active_chats WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()
    return bool(row and row['in_support'])
