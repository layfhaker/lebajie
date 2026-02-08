import sqlite3
import os
import calendar as cal_module
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

    # Таблица объектов бронирования
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS objects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            capacity INTEGER NOT NULL,
            price_weekday INTEGER NOT NULL,
            price_weekend INTEGER NOT NULL,
            description TEXT DEFAULT '',
            is_active INTEGER DEFAULT 1,
            sort_order INTEGER DEFAULT 0
        )
    ''')

    # Таблица бронирований
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            object_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            user_id INTEGER NOT NULL,
            user_name TEXT NOT NULL,
            user_phone TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            admin_id INTEGER,
            FOREIGN KEY (object_id) REFERENCES objects(id)
        )
    ''')

    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_bookings_object_date
        ON bookings(object_id, date, status)
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

    # Добавляем объекты бронирования по умолчанию если таблица пустая
    cursor.execute('SELECT COUNT(*) FROM objects')
    if cursor.fetchone()[0] == 0:
        default_objects = [
            # Малые беседки (рыбалка)
            ("Малая беседка №1", "gazebo_fishing", 6, 2000, 2000, "", 1, 1),
            ("Малая беседка №2", "gazebo_fishing", 6, 2000, 2000, "", 1, 2),
            ("Малая беседка №3", "gazebo_fishing", 6, 2000, 2000, "", 1, 3),
            ("Малая беседка №4", "gazebo_fishing", 6, 2000, 2000, "", 1, 4),
            # Средние беседки (рыбалка)
            ("Средняя беседка №6", "gazebo_fishing", 8, 3000, 3000, "", 1, 6),
            ("Средняя беседка №7", "gazebo_fishing", 8, 3000, 3000, "", 1, 7),
            ("Средняя беседка №8", "gazebo_fishing", 8, 3000, 3000, "", 1, 8),
            ("Средняя беседка №9", "gazebo_fishing", 8, 3000, 3000, "", 1, 9),
            ("Средняя беседка №10", "gazebo_fishing", 8, 3000, 3000, "", 1, 10),
            # Беседки (отдых)
            ("Большая беседка №11", "gazebo_recreation", 15, 10000, 10000, "", 1, 11),
            ("Бар №12", "gazebo_recreation", 20, 18000, 18000, "", 1, 12),
            # Домики
            ("Домик №1", "house", 4, 6000, 7000, "", 1, 20),
            ("Домик №2", "house", 4, 6000, 7000, "", 1, 21),
            ("Домик №3", "house", 4, 6000, 7000, "", 1, 22),
        ]
        cursor.executemany(
            'INSERT INTO objects (name, category, capacity, price_weekday, price_weekend, description, is_active, sort_order) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
            default_objects
        )

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

# === Объекты бронирования ===

def get_objects_by_category(category):
    """Получить все активные объекты категории"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        'SELECT * FROM objects WHERE category = ? AND is_active = 1 ORDER BY sort_order',
        (category,)
    )
    items = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return items


def get_all_objects():
    """Получить все активные объекты"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM objects WHERE is_active = 1 ORDER BY sort_order')
    items = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return items


def get_all_objects_admin():
    """Получить все объекты (включая неактивные) для админки"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM objects ORDER BY sort_order')
    items = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return items


def get_object_by_id(object_id):
    """Получить объект по ID"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM objects WHERE id = ?', (object_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def update_object(object_id, **kwargs):
    """Обновить поля объекта"""
    allowed = {'name', 'category', 'capacity', 'price_weekday', 'price_weekend', 'description', 'is_active', 'sort_order'}
    fields = {k: v for k, v in kwargs.items() if k in allowed}
    if not fields:
        return False
    set_clause = ', '.join(f'{k} = ?' for k in fields)
    values = list(fields.values()) + [object_id]
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(f'UPDATE objects SET {set_clause} WHERE id = ?', values)
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0


def deactivate_object(object_id):
    """Деактивировать объект (мягкое удаление)"""
    return update_object(object_id, is_active=0)

# === Бронирования ===

def get_bookings_for_object_month(object_id, year, month):
    """Получить все активные бронирования объекта за месяц"""
    date_from = f"{year:04d}-{month:02d}-01"
    if month == 12:
        date_to = f"{year + 1:04d}-01-01"
    else:
        date_to = f"{year:04d}-{month + 1:02d}-01"
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM bookings WHERE object_id = ? AND date >= ? AND date < ? AND status != 'cancelled' ORDER BY date",
        (object_id, date_from, date_to)
    )
    items = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return items


def get_day_status(object_id, date_str):
    """Статус дня: 'available', 'pending' или 'booked'"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT status FROM bookings WHERE object_id = ? AND date = ? AND status != 'cancelled'",
        (object_id, date_str)
    )
    row = cursor.fetchone()
    conn.close()
    if not row:
        return 'available'
    return 'booked' if row['status'] == 'confirmed' else 'pending'


def create_booking(object_id, date_str, user_id, user_name, user_phone):
    """Создать бронирование. Возвращает ID или None если дата занята."""
    conn = get_connection()
    cursor = conn.cursor()
    # Проверяем доступность в одной транзакции
    cursor.execute(
        "SELECT id FROM bookings WHERE object_id = ? AND date = ? AND status != 'cancelled'",
        (object_id, date_str)
    )
    if cursor.fetchone():
        conn.close()
        return None
    cursor.execute(
        "INSERT INTO bookings (object_id, date, user_id, user_name, user_phone, status) VALUES (?, ?, ?, ?, ?, 'pending')",
        (object_id, date_str, user_id, user_name, user_phone)
    )
    conn.commit()
    booking_id = cursor.lastrowid
    conn.close()
    return booking_id


def confirm_booking(booking_id, admin_id):
    """Админ подтверждает бронирование"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE bookings SET status = 'confirmed', admin_id = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ? AND status = 'pending'",
        (admin_id, booking_id)
    )
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0


def reject_booking(booking_id, admin_id):
    """Админ отклоняет бронирование"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE bookings SET status = 'cancelled', admin_id = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ? AND status = 'pending'",
        (admin_id, booking_id)
    )
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0


def cancel_booking(booking_id, admin_id):
    """Админ отменяет подтверждённое бронирование"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE bookings SET status = 'cancelled', admin_id = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ? AND status = 'confirmed'",
        (admin_id, booking_id)
    )
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0


def get_booking_by_id(booking_id):
    """Получить бронирование с информацией об объекте"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """SELECT b.*, o.name as object_name, o.category as object_category
           FROM bookings b JOIN objects o ON b.object_id = o.id
           WHERE b.id = ?""",
        (booking_id,)
    )
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_pending_bookings():
    """Получить все ожидающие подтверждения бронирования"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """SELECT b.*, o.name as object_name
           FROM bookings b JOIN objects o ON b.object_id = o.id
           WHERE b.status = 'pending' ORDER BY b.created_at"""
    )
    items = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return items


def get_bookings_by_date(date_str):
    """Получить все активные бронирования на дату"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """SELECT b.*, o.name as object_name
           FROM bookings b JOIN objects o ON b.object_id = o.id
           WHERE b.date = ? AND b.status != 'cancelled' ORDER BY o.sort_order""",
        (date_str,)
    )
    items = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return items


def get_calendar_data_for_api(object_id, year, month):
    """Данные календаря для HTTP API: {date: status}"""
    days_in_month = cal_module.monthrange(year, month)[1]
    bookings = get_bookings_for_object_month(object_id, year, month)
    booking_map = {}
    for b in bookings:
        if b['status'] == 'confirmed':
            booking_map[b['date']] = 'booked'
        elif b['date'] not in booking_map:
            booking_map[b['date']] = 'partially'
    result = {}
    for day in range(1, days_in_month + 1):
        date_str = f"{year:04d}-{month:02d}-{day:02d}"
        result[date_str] = booking_map.get(date_str, 'available')
    return result
