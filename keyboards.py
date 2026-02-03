from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_main_keyboard(is_admin_user=False):
    """Главная клавиатура"""
    buttons = [
        [InlineKeyboardButton(text="❓ Частые вопросы (FAQ)", callback_data="faq_menu")],
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

def get_admin_keyboard():
    """Админ-панель"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Изменить FAQ", callback_data="admin_faq")],
        [InlineKeyboardButton(text="🔗 Пригласить админа (реф-ссылка)", callback_data="admin_create_ref")],
        [InlineKeyboardButton(text="👥 Управление админами", callback_data="admin_admins")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_main")],
    ])
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

def get_admin_admins_keyboard(admins, main_admin_id):
    """Админское управление админами"""
    buttons = []
    for admin_id in admins:
        is_main = " (главный)" if admin_id == main_admin_id else ""
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


