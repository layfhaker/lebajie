from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import calendar as cal_module
from datetime import date

def get_main_keyboard(is_admin_user=False):
    """Главная клавиатура"""
    buttons = [
        [InlineKeyboardButton(text="❓ Частые вопросы (FAQ)", callback_data="faq_menu")],
        [InlineKeyboardButton(text="📅 Бронирование", callback_data="booking")],
        [InlineKeyboardButton(text="💬 Связаться с поддержкой", callback_data="support_start")],
    ]
    if is_admin_user:
        buttons.append([InlineKeyboardButton(text="🔧 Админ меню", callback_data="admin_panel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_faq_keyboard(faq_list):
    """Клавиатура FAQ"""
    buttons = []
    for item in faq_list:
        # Обрезаем вопрос если слишком длинный
        question = item["question"][:50] + "..." if len(item["question"]) > 50 else item["question"]
        buttons.append([InlineKeyboardButton(text=f"📌 {question}", callback_data=f"faq_{item['id']}")])

    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back_main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_faq_answer_keyboard():
    """Клавиатура после ответа FAQ"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ К списку вопросов", callback_data="faq_menu")],
        [InlineKeyboardButton(text="💬 Связаться с поддержкой", callback_data="support_start")],
        [InlineKeyboardButton(text="🏠 В главное меню", callback_data="back_main")],
    ])
    return keyboard

def get_support_keyboard():
    """Клавиатура поддержки"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Завершить диалог", callback_data="support_end")],
    ])
    return keyboard

def get_back_keyboard():
    """Кнопка назад"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_main")],
    ])
    return keyboard

# === Админские клавиатуры ===

def get_admin_keyboard(is_tech_admin=False, notifications_enabled=True):
    """Админ-панель"""
    buttons = [
        [InlineKeyboardButton(text="📅 Бронирования", callback_data="admin_bookings")],
        [InlineKeyboardButton(text="📝 Изменить FAQ", callback_data="admin_faq")],
        [InlineKeyboardButton(text="🔗 Пригласить админа (реф-ссылка)", callback_data="admin_create_ref")],
        [InlineKeyboardButton(text="👥 Управление админами", callback_data="admin_admins")],
    ]

    if is_tech_admin:
        toggle_text = "🔕 Выключить уведомления" if notifications_enabled else "🔔 Включить уведомления"
        buttons.append([InlineKeyboardButton(text=toggle_text, callback_data="admin_toggle_notifications")])

    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back_main")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard

def get_admin_faq_keyboard(faq_list):
    """Админское управление FAQ"""
    buttons = []
    for item in faq_list:
        question = item["question"][:30] + "..." if len(item["question"]) > 30 else item["question"]
        buttons.append([
            InlineKeyboardButton(text=f"📌 {question}", callback_data=f"admin_faq_view_{item['id']}"),
            InlineKeyboardButton(text="🗑", callback_data=f"admin_faq_delete_{item['id']}")
        ])

    buttons.append([InlineKeyboardButton(text="➕ Добавить вопрос", callback_data="admin_faq_add")])
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_panel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_admin_faq_item_keyboard(faq_id):
    """Меню редактирования одного FAQ-элемента"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Изменить вопрос", callback_data=f"admin_faq_edit_q_{faq_id}")],
        [InlineKeyboardButton(text="📝 Изменить ответ", callback_data=f"admin_faq_edit_a_{faq_id}")],
        [InlineKeyboardButton(text="🗑 Удалить вопрос", callback_data=f"admin_faq_delete_{faq_id}")],
        [InlineKeyboardButton(text="⬅️ К списку FAQ", callback_data="admin_faq")],
    ])


def get_admin_admins_keyboard(admins, main_admin_id):
    """Админское управление админами"""
    buttons = []
    for admin_id in admins:
        is_main = " (админ-технарь)" if admin_id == main_admin_id else ""
        buttons.append([
            InlineKeyboardButton(text=f"👤 {admin_id}{is_main}", callback_data=f"admin_info_{admin_id}"),
            InlineKeyboardButton(text="🗑" if admin_id != main_admin_id else "⭐", callback_data=f"admin_remove_{admin_id}" if admin_id != main_admin_id else "noop")
        ])

    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_panel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_confirm_delete_faq_keyboard(faq_id):
    """Подтверждение удаления FAQ"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"admin_faq_confirm_delete_{faq_id}"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="admin_faq")
        ],
    ])
    return keyboard

def get_cancel_keyboard():
    """Кнопка отмены"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_faq")],
    ])
    return keyboard

def get_admin_reply_keyboard(user_id):
    """Клавиатура для ответа пользователю"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 Ответить", callback_data=f"reply_to_{user_id}")],
    ])
    return keyboard

# === Клавиатуры бронирования (пользователь) ===

def get_booking_categories_keyboard():
    """Выбор категории бронирования"""
    buttons = [
        [InlineKeyboardButton(text="🎣 Беседки (рыбалка)", callback_data="book_cat_gazebo_fishing")],
        [InlineKeyboardButton(text="🏖 Беседки (отдых)", callback_data="book_cat_gazebo_recreation")],
        [InlineKeyboardButton(text="🏠 Домики", callback_data="book_cat_house")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_main")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_booking_objects_keyboard(objects, category):
    """Список объектов в категории"""
    buttons = []
    for obj in objects:
        price_text = f"{obj['price_weekday']}₽"
        if obj['price_weekday'] != obj['price_weekend']:
            price_text = f"{obj['price_weekday']}/{obj['price_weekend']}₽"
        text = f"{obj['name']} (до {obj['capacity']} чел., {price_text})"
        buttons.append([InlineKeyboardButton(text=text, callback_data=f"book_obj_{obj['id']}")])
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="book_back_categories")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_booking_calendar_keyboard(object_id, year, month, bookings):
    """Календарь для выбора даты бронирования"""
    # Карта статусов: date_str -> status
    status_map = {}
    for b in bookings:
        if b['status'] in ('confirmed', 'blocked'):
            status_map[b['date']] = 'booked'
        elif b['status'] == 'pending' and b['date'] not in status_map:
            status_map[b['date']] = 'pending'

    today = date.today()
    month_names = {
        1: "Январь", 2: "Февраль", 3: "Март", 4: "Апрель",
        5: "Май", 6: "Июнь", 7: "Июль", 8: "Август",
        9: "Сентябрь", 10: "Октябрь", 11: "Ноябрь", 12: "Декабрь"
    }

    buttons = []

    # Навигация по месяцам
    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    next_month = month + 1 if month < 12 else 1
    next_year = year if month < 12 else year + 1

    can_go_prev = date(prev_year, prev_month, 1) >= date(today.year, today.month, 1)
    prev_btn = InlineKeyboardButton(
        text="◀️" if can_go_prev else " ",
        callback_data=f"book_cal_{object_id}_{prev_year}_{prev_month}" if can_go_prev else "noop"
    )
    next_btn = InlineKeyboardButton(
        text="▶️",
        callback_data=f"book_cal_{object_id}_{next_year}_{next_month}"
    )
    header_btn = InlineKeyboardButton(
        text=f"{month_names[month]} {year}",
        callback_data="noop"
    )
    buttons.append([prev_btn, header_btn, next_btn])

    # Дни недели
    week_headers = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    buttons.append([
        InlineKeyboardButton(text=d, callback_data="noop") for d in week_headers
    ])

    # Сетка дней
    cal = cal_module.monthcalendar(year, month)
    for week in cal:
        row = []
        for day_num in week:
            if day_num == 0:
                row.append(InlineKeyboardButton(text=" ", callback_data="noop"))
                continue

            date_str = f"{year:04d}-{month:02d}-{day_num:02d}"
            day_date = date(year, month, day_num)
            status = status_map.get(date_str, 'available')

            # Прошедшие дни
            if day_date < today:
                row.append(InlineKeyboardButton(text=f"{day_num}", callback_data="noop"))
                continue

            # Статус
            if status == 'booked':
                row.append(InlineKeyboardButton(text=f"❌{day_num}", callback_data="noop"))
            elif status == 'pending':
                row.append(InlineKeyboardButton(text=f"⏳{day_num}", callback_data="noop"))
            else:
                row.append(InlineKeyboardButton(text=f"✅{day_num}", callback_data=f"book_day_{object_id}_{date_str}"))

        buttons.append(row)

    # Легенда
    buttons.append([
        InlineKeyboardButton(text="✅свободно", callback_data="noop"),
        InlineKeyboardButton(text="⏳ожидание", callback_data="noop"),
        InlineKeyboardButton(text="❌занято", callback_data="noop"),
    ])
    buttons.append([
        InlineKeyboardButton(text="⬅️ Назад", callback_data="book_back_objects")
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_booking_confirm_keyboard():
    """Подтверждение бронирования"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Подтвердить", callback_data="book_confirm"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="book_cancel"),
        ],
    ])


def get_booking_cancel_keyboard():
    """Кнопка отмены бронирования"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="book_cancel")],
    ])

# === Клавиатуры бронирования (админ) ===

def get_admin_bookings_keyboard():
    """Меню управления бронированиями"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏳ Ожидающие подтверждения", callback_data="admin_book_pending")],
        [InlineKeyboardButton(text="🔧 Управление объектами", callback_data="admin_objects")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_panel")],
    ])


def get_admin_pending_bookings_keyboard(bookings):
    """Список ожидающих бронирований"""
    buttons = []
    for b in bookings:
        text = f"#{b['id']} | {b['object_name']} | {b['date']}"
        if len(text) > 60:
            text = text[:57] + "..."
        buttons.append([InlineKeyboardButton(text=text, callback_data=f"admin_book_detail_{b['id']}")])
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_bookings")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_admin_booking_detail_keyboard(booking_id, status):
    """Действия с бронированием"""
    buttons = []
    if status == 'pending':
        buttons.append([
            InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"admin_book_confirm_{booking_id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"admin_book_reject_{booking_id}"),
        ])
    elif status == 'confirmed':
        buttons.append([
            InlineKeyboardButton(text="🚫 Отменить бронь", callback_data=f"admin_book_cancel_{booking_id}"),
        ])
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_book_pending")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_admin_objects_keyboard(objects):
    """Управление объектами"""
    buttons = []
    for obj in objects:
        status_icon = "🟢" if obj['is_active'] else "🔴"
        text = f"{status_icon} {obj['name']}"
        buttons.append([
            InlineKeyboardButton(text=text, callback_data=f"admin_obj_open_{obj['id']}")
        ])
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_bookings")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_admin_object_calendar_keyboard(object_id, year, month, bookings, is_active):
    """Календарь объекта для ручной блокировки дат в админке"""
    status_map = {}
    for b in bookings:
        if b['status'] == 'confirmed':
            status_map[b['date']] = 'confirmed'
        elif b['status'] == 'pending' and status_map.get(b['date']) != 'confirmed':
            status_map[b['date']] = 'pending'
        elif b['status'] == 'blocked' and b['date'] not in status_map:
            status_map[b['date']] = 'blocked'

    today = date.today()
    month_names = {
        1: "Январь", 2: "Февраль", 3: "Март", 4: "Апрель",
        5: "Май", 6: "Июнь", 7: "Июль", 8: "Август",
        9: "Сентябрь", 10: "Октябрь", 11: "Ноябрь", 12: "Декабрь"
    }
    buttons = []

    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    next_month = month + 1 if month < 12 else 1
    next_year = year if month < 12 else year + 1

    can_go_prev = date(prev_year, prev_month, 1) >= date(today.year, today.month, 1)
    prev_btn = InlineKeyboardButton(
        text="◀️" if can_go_prev else " ",
        callback_data=f"admin_obj_cal_{object_id}_{prev_year}_{prev_month}" if can_go_prev else "noop"
    )
    next_btn = InlineKeyboardButton(
        text="▶️",
        callback_data=f"admin_obj_cal_{object_id}_{next_year}_{next_month}"
    )
    header_btn = InlineKeyboardButton(
        text=f"{month_names[month]} {year}",
        callback_data="noop"
    )
    buttons.append([prev_btn, header_btn, next_btn])

    week_headers = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    buttons.append([InlineKeyboardButton(text=d, callback_data="noop") for d in week_headers])

    cal = cal_module.monthcalendar(year, month)
    for week in cal:
        row = []
        for day_num in week:
            if day_num == 0:
                row.append(InlineKeyboardButton(text=" ", callback_data="noop"))
                continue

            date_str = f"{year:04d}-{month:02d}-{day_num:02d}"
            day_date = date(year, month, day_num)
            status = status_map.get(date_str, 'available')

            if day_date < today:
                row.append(InlineKeyboardButton(text=f"{day_num}", callback_data="noop"))
                continue

            if status == 'confirmed':
                row.append(InlineKeyboardButton(text=f"❌{day_num}", callback_data="noop"))
            elif status == 'pending':
                row.append(InlineKeyboardButton(text=f"⏳{day_num}", callback_data="noop"))
            elif status == 'blocked':
                row.append(InlineKeyboardButton(text=f"🚫{day_num}", callback_data=f"admin_obj_day_{object_id}_{date_str}"))
            else:
                row.append(InlineKeyboardButton(text=f"✅{day_num}", callback_data=f"admin_obj_day_{object_id}_{date_str}"))
        buttons.append(row)

    buttons.append([
        InlineKeyboardButton(text="✅свободно", callback_data="noop"),
        InlineKeyboardButton(text="🚫вручную", callback_data="noop"),
        InlineKeyboardButton(text="⏳ожидание", callback_data="noop"),
        InlineKeyboardButton(text="❌бронь", callback_data="noop"),
    ])

    active_btn_text = "🔴 Отключить объект" if is_active else "🟢 Включить объект"
    buttons.append([
        InlineKeyboardButton(text=active_btn_text, callback_data=f"admin_obj_active_{object_id}_{year}_{month}")
    ])
    buttons.append([InlineKeyboardButton(text="⬅️ К объектам", callback_data="admin_objects")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)
