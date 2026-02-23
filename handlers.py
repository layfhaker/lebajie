from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from datetime import date, datetime

import keyboards as kb
from database import (
    is_admin, get_admins, add_admin, remove_admin,
    get_faq, get_faq_by_id, add_faq, remove_faq,
    generate_ref_token, use_ref_token,
    set_user_in_support, is_user_in_support,
    get_objects_by_category, get_object_by_id, get_all_objects_admin,
    get_bookings_for_object_month, get_day_status, create_booking,
    confirm_booking, reject_booking, cancel_booking,
    get_booking_by_id, get_pending_bookings,
    update_object,
)
from config import MAIN_ADMIN_ID

router = Router()

# Категории и deep-link сценарии бронирования
BOOKING_CATEGORY_NAMES = {
    "gazebo_fishing": "🎣 Беседки (рыбалка)",
    "gazebo_recreation": "🏖 Беседки (отдых)",
    "house": "🏠 Домики",
}

SITE_START_CATEGORY_MAP = {
    "fishing": "gazebo_fishing",
    "recreation": "gazebo_recreation",
    "house": "house",
    "site_fishing": "gazebo_fishing",
    "site_recreation": "gazebo_recreation",
    "site_house": "house",
    "gazebo_fishing": "gazebo_fishing",
    "gazebo_recreation": "gazebo_recreation",
}

# === Состояния ===
class AdminStates(StatesGroup):
    waiting_faq_question = State()
    waiting_faq_answer = State()
    waiting_reply_to_user = State()

class UserStates(StatesGroup):
    in_support = State()

class BookingStates(StatesGroup):
    entering_name = State()
    entering_phone = State()
    confirming = State()

# === Стартовые команды ===

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    """Обработка /start и реф-ссылок"""
    await state.clear()

    # /start аргумент, если есть
    args = (message.text or "").split(maxsplit=1)
    if len(args) > 1:
        start_arg = args[1].strip()
        start_arg_normalized = start_arg.lower()

        # Сначала обрабатываем deep-link сценарии с сайта
        start_category = SITE_START_CATEGORY_MAP.get(start_arg_normalized)
        if start_category:
            objects = get_objects_by_category(start_category)
            if not objects:
                category_name = BOOKING_CATEGORY_NAMES.get(start_category, "выбранной категории")
                await message.answer(
                    f"📭 В <b>{category_name}</b> пока нет доступных объектов.\n\n"
                    "Выберите другую категорию:",
                    reply_markup=kb.get_booking_categories_keyboard(),
                    parse_mode="HTML"
                )
                return

            await state.update_data(booking_category=start_category)
            await message.answer(
                f"📅 <b>{BOOKING_CATEGORY_NAMES.get(start_category, 'Бронирование')}</b>\n\n"
                "Выберите объект:",
                reply_markup=kb.get_booking_objects_keyboard(objects, start_category),
                parse_mode="HTML"
            )
            return

        # Если это не сценарий сайта, проверяем админ-реф токен
        if use_ref_token(start_arg, message.from_user.id):
            await message.answer(
                "🎉 Поздравляем! Вы стали администратором бота.\n"
                "Используйте /admin для доступа к панели управления."
            )
            return

    await message.answer(
        "👋 Добро пожаловать в бот поддержки!\n\n"
        "🏞 <b>Лебяжье озеро</b> — отдых и рыбалка в Крыму\n\n"
        "Выберите, что вас интересует:",
        reply_markup=kb.get_main_keyboard(is_admin(message.from_user.id)),
        parse_mode="HTML"
    )

@router.message(Command("admin"))
async def cmd_admin(message: Message):
    """Админ-панель"""
    if not is_admin(message.from_user.id):
        await message.answer("⛔ У вас нет доступа к админ-панели.")
        return

    await message.answer(
        "🔧 <b>Админ-панель</b>\n\nВыберите действие:",
        reply_markup=kb.get_admin_keyboard(),
        parse_mode="HTML"
    )

@router.message(Command("help"))
async def cmd_help(message: Message):
    """Помощь"""
    text = (
        "📖 <b>Справка по боту</b>\n\n"
        "/start — Главное меню\n"
        "/help — Эта справка\n"
    )
    if is_admin(message.from_user.id):
        text += "/admin — Панель администратора\n"

    await message.answer(text, parse_mode="HTML")

# === Callback обработчики — Главное меню ===

@router.callback_query(F.data == "back_main")
async def callback_back_main(callback: CallbackQuery, state: FSMContext):
    """Вернуться в главное меню"""
    await state.clear()
    set_user_in_support(callback.from_user.id, False)

    await callback.message.edit_text(
        "👋 <b>Главное меню</b>\n\n"
        "🏞 <b>Лебяжье озеро</b> — отдых и рыбалка в Крыму\n\n"
        "Выберите, что вас интересует:",
        reply_markup=kb.get_main_keyboard(is_admin(callback.from_user.id)),
        parse_mode="HTML"
    )

# === FAQ ===

@router.callback_query(F.data == "faq_menu")
async def callback_faq_menu(callback: CallbackQuery):
    """Меню FAQ"""
    faq_list = get_faq()
    if not faq_list:
        await callback.message.edit_text(
            "📭 Пока нет частых вопросов.",
            reply_markup=kb.get_back_keyboard()
        )
        return

    await callback.message.edit_text(
        "❓ <b>Частые вопросы</b>\n\nВыберите интересующий вопрос:",
        reply_markup=kb.get_faq_keyboard(faq_list),
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("faq_"))
async def callback_faq_answer(callback: CallbackQuery):
    """Ответ на FAQ"""
    if callback.data == "faq_menu":
        return

    faq_id = int(callback.data.replace("faq_", ""))
    item = get_faq_by_id(faq_id)

    if item:
        await callback.message.edit_text(
            f"❓ <b>{item['question']}</b>\n\n{item['answer']}",
            reply_markup=kb.get_faq_answer_keyboard(),
            parse_mode="HTML"
        )
    else:
        await callback.answer("Вопрос не найден", show_alert=True)

# === Поддержка ===

@router.callback_query(F.data == "support_start")
async def callback_support_start(callback: CallbackQuery, state: FSMContext):
    """Начать диалог с поддержкой"""
    await state.set_state(UserStates.in_support)
    set_user_in_support(callback.from_user.id, True)

    await callback.message.edit_text(
        "💬 <b>Связь с поддержкой</b>\n\n"
        "Напишите ваш вопрос, и мы ответим вам в ближайшее время.\n\n"
        "Можете отправлять текст, фото или документы.",
        reply_markup=kb.get_support_keyboard(),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "support_end")
async def callback_support_end(callback: CallbackQuery, state: FSMContext):
    """Завершить диалог с поддержкой"""
    await state.clear()
    set_user_in_support(callback.from_user.id, False)

    await callback.message.edit_text(
        "✅ Диалог с поддержкой завершён.\n\n"
        "Спасибо за обращение! Если у вас появятся ещё вопросы — мы всегда на связи.",
        reply_markup=kb.get_main_keyboard(is_admin(callback.from_user.id))
    )

# === Сообщения от пользователя в режиме поддержки ===

@router.message(UserStates.in_support)
async def handle_support_message(message: Message, state: FSMContext):
    """Пересылка сообщения от пользователя админам"""
    admins = get_admins()

    user = message.from_user
    user_info = "👤 <b>Сообщение от пользователя</b>\n"
    user_info += f"ID: <code>{user.id}</code>\n"
    user_info += f"Имя: {user.full_name}\n"
    if user.username:
        user_info += f"Username: @{user.username}\n"
    user_info += "\n"

    # Отправляем всем админам
    for admin_id in admins:
        try:
            await message.bot.send_message(
                admin_id,
                user_info + "⬇️ <b>Сообщение:</b>",
                parse_mode="HTML"
            )
            # Пересылаем оригинальное сообщение
            await message.forward(admin_id)
            # Кнопка ответа
            await message.bot.send_message(
                admin_id,
                "Нажмите кнопку ниже, чтобы ответить:",
                reply_markup=kb.get_admin_reply_keyboard(user.id)
            )
        except Exception as e:
            print(f"Не удалось отправить сообщение админу {admin_id}: {e}")

    await message.answer(
        "✅ Ваше сообщение отправлено в поддержку.\n"
        "Ожидайте ответа.",
        reply_markup=kb.get_support_keyboard()
    )

# === Админ: Ответ пользователю ===

@router.callback_query(F.data.startswith("reply_to_"))
async def callback_reply_to_user(callback: CallbackQuery, state: FSMContext):
    """Начать отвечать пользователю"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return

    user_id = int(callback.data.replace("reply_to_", ""))
    await state.set_state(AdminStates.waiting_reply_to_user)
    await state.update_data(reply_to_user_id=user_id)

    await callback.message.answer(
        f"✏️ Напишите ответ для пользователя ID: <code>{user_id}</code>\n\n"
        "Отправьте текст, фото или документ.",
        parse_mode="HTML"
    )
    await callback.answer()

@router.message(AdminStates.waiting_reply_to_user)
async def handle_admin_reply(message: Message, state: FSMContext):
    """Отправить ответ пользователю"""
    state_data = await state.get_data()
    user_id = state_data.get("reply_to_user_id")

    if not user_id:
        await state.clear()
        await message.answer("❌ Ошибка: ID пользователя не найден.")
        return

    try:
        # Отправляем сообщение пользователю
        await message.bot.send_message(
            user_id,
            "💬 <b>Ответ от поддержки:</b>",
            parse_mode="HTML"
        )

        # Копируем сообщение админа пользователю
        await message.copy_to(user_id)

        await message.answer(f"✅ Ответ отправлен пользователю ID: {user_id}")
    except Exception as e:
        await message.answer(f"❌ Не удалось отправить сообщение: {e}")

    await state.clear()

# === Админ-панель ===

@router.callback_query(F.data == "admin_panel")
async def callback_admin_panel(callback: CallbackQuery):
    """Админ-панель"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return

    await callback.message.edit_text(
        "🔧 <b>Админ-панель</b>\n\nВыберите действие:",
        reply_markup=kb.get_admin_keyboard(),
        parse_mode="HTML"
    )

# === Админ: Управление FAQ ===

@router.callback_query(F.data == "admin_faq")
async def callback_admin_faq(callback: CallbackQuery, state: FSMContext):
    """Управление FAQ"""
    await state.clear()
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return

    faq_list = get_faq()
    await callback.message.edit_text(
        "📝 <b>Управление FAQ</b>\n\n"
        "Нажмите на вопрос для просмотра, или 🗑 для удаления.",
        reply_markup=kb.get_admin_faq_keyboard(faq_list),
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("admin_faq_view_"))
async def callback_admin_faq_view(callback: CallbackQuery):
    """Просмотр FAQ в админке"""
    faq_id = int(callback.data.replace("admin_faq_view_", ""))
    item = get_faq_by_id(faq_id)

    if item:
        await callback.answer(
            f"Q: {item['question'][:100]}\n\nA: {item['answer'][:100]}",
            show_alert=True
        )

@router.callback_query(F.data.startswith("admin_faq_delete_"))
async def callback_admin_faq_delete(callback: CallbackQuery):
    """Подтверждение удаления FAQ"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return

    faq_id = int(callback.data.replace("admin_faq_delete_", ""))
    item = get_faq_by_id(faq_id)

    if item:
        await callback.message.edit_text(
            "🗑 <b>Удалить вопрос?</b>\n\n"
            f"❓ {item['question']}",
            reply_markup=kb.get_confirm_delete_faq_keyboard(faq_id),
            parse_mode="HTML"
        )

@router.callback_query(F.data.startswith("admin_faq_confirm_delete_"))
async def callback_admin_faq_confirm_delete(callback: CallbackQuery):
    """Удаление FAQ"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return

    faq_id = int(callback.data.replace("admin_faq_confirm_delete_", ""))

    if remove_faq(faq_id):
        await callback.answer("✅ Вопрос удалён", show_alert=True)
        faq_list = get_faq()
        await callback.message.edit_text(
            "📝 <b>Управление FAQ</b>\n\n"
            "Нажмите на вопрос для просмотра, или 🗑 для удаления.",
            reply_markup=kb.get_admin_faq_keyboard(faq_list),
            parse_mode="HTML"
        )
    else:
        await callback.answer("❌ Ошибка удаления", show_alert=True)

@router.callback_query(F.data == "admin_faq_add")
async def callback_admin_faq_add(callback: CallbackQuery, state: FSMContext):
    """Добавить FAQ — шаг 1"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return

    await state.set_state(AdminStates.waiting_faq_question)
    await callback.message.edit_text(
        "➕ <b>Добавление FAQ</b>\n\n"
        "Шаг 1/2: Напишите вопрос",
        reply_markup=kb.get_cancel_keyboard(),
        parse_mode="HTML"
    )

@router.message(AdminStates.waiting_faq_question)
async def handle_faq_question(message: Message, state: FSMContext):
    """Добавить FAQ — шаг 2"""
    await state.update_data(faq_question=message.text)
    await state.set_state(AdminStates.waiting_faq_answer)
    await message.answer(
        "➕ <b>Добавление FAQ</b>\n\n"
        f"Вопрос: {message.text}\n\n"
        "Шаг 2/2: Теперь напишите ответ",
        parse_mode="HTML"
    )

@router.message(AdminStates.waiting_faq_answer)
async def handle_faq_answer(message: Message, state: FSMContext):
    """Добавить FAQ — финал"""
    state_data = await state.get_data()
    question = state_data.get("faq_question")

    add_faq(question, message.text)

    await state.clear()
    await message.answer(
        "✅ <b>FAQ добавлен!</b>\n\n"
        f"❓ {question}\n\n"
        f"💬 {message.text}",
        reply_markup=kb.get_admin_keyboard(),
        parse_mode="HTML"
    )

# === Админ: Управление админами ===

@router.callback_query(F.data == "admin_admins")
async def callback_admin_admins(callback: CallbackQuery):
    """Управление админами"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return

    admins = get_admins()
    await callback.message.edit_text(
        "👥 <b>Управление администраторами</b>\n\n"
        f"Всего админов: {len(admins)}\n"
        "★ — главный админ (нельзя удалить)",
        reply_markup=kb.get_admin_admins_keyboard(admins, MAIN_ADMIN_ID),
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("admin_remove_"))
async def callback_admin_remove(callback: CallbackQuery):
    """Удалить админа"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return

    admin_id = int(callback.data.replace("admin_remove_", ""))

    if admin_id == MAIN_ADMIN_ID:
        await callback.answer("⛔ Нельзя удалить главного админа", show_alert=True)
        return

    if remove_admin(admin_id):
        await callback.answer("✅ Админ удалён", show_alert=True)
        admins = get_admins()
        await callback.message.edit_text(
            "👥 <b>Управление администраторами</b>\n\n"
            f"Всего админов: {len(admins)}",
            reply_markup=kb.get_admin_admins_keyboard(admins, MAIN_ADMIN_ID),
            parse_mode="HTML"
        )
    else:
        await callback.answer("❌ Ошибка удаления", show_alert=True)

@router.callback_query(F.data == "noop")
async def callback_noop(callback: CallbackQuery):
    """Заглушка"""
    await callback.answer()

# === Админ: Создание реф-ссылки ===

@router.callback_query(F.data == "admin_create_ref")
async def callback_admin_create_ref(callback: CallbackQuery):
    """Создать реферальную ссылку"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return

    token = generate_ref_token(callback.from_user.id)
    bot_info = await callback.bot.get_me()

    ref_link = f"https://t.me/{bot_info.username}?start={token}"

    await callback.message.edit_text(
        "🔗 <b>Реферальная ссылка создана!</b>\n\n"
        f"<code>{ref_link}</code>\n\n"
        "Отправьте эту ссылку человеку, которого хотите сделать админом.\n"
        "⚠️ Ссылка одноразовая.",
        reply_markup=kb.get_admin_keyboard(),
        parse_mode="HTML"
    )

# === Бронирование (пользователь) ===

@router.callback_query(F.data == "booking")
async def callback_booking_start(callback: CallbackQuery, state: FSMContext):
    """Бронирование: выбор категории"""
    await state.clear()
    await callback.message.edit_text(
        "📅 <b>Бронирование</b>\n\nВыберите категорию:",
        reply_markup=kb.get_booking_categories_keyboard(),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "book_back_categories")
async def callback_book_back_categories(callback: CallbackQuery, state: FSMContext):
    """Назад к категориям"""
    await state.clear()
    await callback.message.edit_text(
        "📅 <b>Бронирование</b>\n\nВыберите категорию:",
        reply_markup=kb.get_booking_categories_keyboard(),
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("book_cat_"))
async def callback_booking_category(callback: CallbackQuery, state: FSMContext):
    """Бронирование: список объектов в категории"""
    category = callback.data.replace("book_cat_", "")
    objects = get_objects_by_category(category)

    if not objects:
        await callback.answer("Нет доступных объектов в этой категории", show_alert=True)
        return

    await state.update_data(booking_category=category)
    await callback.message.edit_text(
        f"📅 <b>{BOOKING_CATEGORY_NAMES.get(category, 'Бронирование')}</b>\n\nВыберите объект:",
        reply_markup=kb.get_booking_objects_keyboard(objects, category),
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("book_obj_"))
async def callback_booking_object(callback: CallbackQuery, state: FSMContext):
    """Бронирование: показ календаря для объекта"""
    object_id = int(callback.data.replace("book_obj_", ""))
    obj = get_object_by_id(object_id)
    if not obj:
        await callback.answer("Объект не найден", show_alert=True)
        return

    today = date.today()
    year, month = today.year, today.month
    bookings = get_bookings_for_object_month(object_id, year, month)

    await state.update_data(booking_object_id=object_id, booking_category=obj['category'])

    price_text = f"{obj['price_weekday']}₽/день"
    if obj['price_weekday'] != obj['price_weekend']:
        price_text = f"{obj['price_weekday']}₽ будни / {obj['price_weekend']}₽ выходные"

    await callback.message.edit_text(
        f"📅 <b>{obj['name']}</b>\n"
        f"👥 До {obj['capacity']} человек | {price_text}\n\n"
        "Выберите дату:",
        reply_markup=kb.get_booking_calendar_keyboard(object_id, year, month, bookings),
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("book_cal_"))
async def callback_booking_calendar_nav(callback: CallbackQuery, state: FSMContext):
    """Бронирование: навигация по месяцам"""
    parts = callback.data.split("_")  # book_cal_{id}_{year}_{month}
    object_id = int(parts[2])
    year = int(parts[3])
    month = int(parts[4])

    obj = get_object_by_id(object_id)
    if not obj:
        await callback.answer("Объект не найден", show_alert=True)
        return

    bookings = get_bookings_for_object_month(object_id, year, month)

    price_text = f"{obj['price_weekday']}₽/день"
    if obj['price_weekday'] != obj['price_weekend']:
        price_text = f"{obj['price_weekday']}₽ будни / {obj['price_weekend']}₽ выходные"

    await callback.message.edit_text(
        f"📅 <b>{obj['name']}</b>\n"
        f"👥 До {obj['capacity']} человек | {price_text}\n\n"
        "Выберите дату:",
        reply_markup=kb.get_booking_calendar_keyboard(object_id, year, month, bookings),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "book_back_objects")
async def callback_book_back_objects(callback: CallbackQuery, state: FSMContext):
    """Назад к списку объектов"""
    state_data = await state.get_data()
    category = state_data.get("booking_category", "gazebo_fishing")
    objects = get_objects_by_category(category)

    await callback.message.edit_text(
        f"📅 <b>{BOOKING_CATEGORY_NAMES.get(category, 'Бронирование')}</b>\n\nВыберите объект:",
        reply_markup=kb.get_booking_objects_keyboard(objects, category),
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("book_day_"))
async def callback_booking_select_date(callback: CallbackQuery, state: FSMContext):
    """Бронирование: дата выбрана, запрос имени"""
    parts = callback.data.split("_")  # book_day_{id}_{YYYY-MM-DD}
    object_id = int(parts[2])
    date_str = parts[3]  # "YYYY-MM-DD"

    # Проверяем доступность
    status = get_day_status(object_id, date_str)
    if status != 'available':
        await callback.answer("Эта дата уже занята!", show_alert=True)
        return

    obj = get_object_by_id(object_id)
    await state.update_data(
        booking_object_id=object_id,
        booking_date=date_str,
        booking_object_name=obj['name'] if obj else "?"
    )
    await state.set_state(BookingStates.entering_name)

    await callback.message.edit_text(
        f"📅 <b>Бронирование: {obj['name']}</b>\n"
        f"📆 Дата: {date_str}\n\n"
        "Введите ваше имя:",
        reply_markup=kb.get_booking_cancel_keyboard(),
        parse_mode="HTML"
    )

@router.message(BookingStates.entering_name)
async def handle_booking_name(message: Message, state: FSMContext):
    """Бронирование: имя введено, запрос телефона"""
    name = message.text.strip()
    if len(name) < 2 or len(name) > 100:
        await message.answer("Пожалуйста, введите корректное имя (от 2 до 100 символов):")
        return

    await state.update_data(booking_user_name=name)
    await state.set_state(BookingStates.entering_phone)

    await message.answer(
        f"👤 Имя: {name}\n\n"
        "Введите номер телефона:",
        reply_markup=kb.get_booking_cancel_keyboard()
    )

@router.message(BookingStates.entering_phone)
async def handle_booking_phone(message: Message, state: FSMContext):
    """Бронирование: телефон введён, показ подтверждения"""
    phone = message.text.strip()
    digits = ''.join(c for c in phone if c.isdigit())
    if len(digits) < 7:
        await message.answer("Пожалуйста, введите корректный номер телефона:")
        return

    await state.update_data(booking_user_phone=phone)
    state_data = await state.get_data()

    obj = get_object_by_id(state_data['booking_object_id'])
    date_obj = datetime.strptime(state_data['booking_date'], '%Y-%m-%d').date()

    # Считаем цену
    is_weekend = date_obj.weekday() >= 5
    price = obj['price_weekend'] if is_weekend else obj['price_weekday']

    await state.set_state(BookingStates.confirming)

    await message.answer(
        "📋 <b>Подтверждение бронирования</b>\n\n"
        f"🏠 Объект: {state_data['booking_object_name']}\n"
        f"📆 Дата: {state_data['booking_date']}\n"
        f"💰 Стоимость: {price}₽\n"
        f"👤 Имя: {state_data['booking_user_name']}\n"
        f"📱 Телефон: {phone}\n\n"
        "Всё верно?",
        reply_markup=kb.get_booking_confirm_keyboard(),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "book_confirm", BookingStates.confirming)
async def callback_booking_confirm(callback: CallbackQuery, state: FSMContext):
    """Бронирование: подтверждение, создание заявки"""
    state_data = await state.get_data()

    booking_id = create_booking(
        object_id=state_data['booking_object_id'],
        date_str=state_data['booking_date'],
        user_id=callback.from_user.id,
        user_name=state_data['booking_user_name'],
        user_phone=state_data['booking_user_phone'],
    )

    if booking_id is None:
        await callback.message.edit_text(
            "❌ К сожалению, эта дата уже занята.\n"
            "Попробуйте выбрать другую дату.",
            reply_markup=kb.get_booking_categories_keyboard()
        )
        await state.clear()
        return

    await state.clear()

    await callback.message.edit_text(
        "✅ <b>Заявка отправлена!</b>\n\n"
        f"Номер брони: #{booking_id}\n"
        f"🏠 {state_data['booking_object_name']}\n"
        f"📆 {state_data['booking_date']}\n\n"
        "Ожидайте подтверждения от администратора.\n"
        "Мы уведомим вас о решении.",
        reply_markup=kb.get_main_keyboard(is_admin(callback.from_user.id)),
        parse_mode="HTML"
    )

    # Уведомляем админов
    admins = get_admins()
    admin_text = (
        "🔔 <b>Новая заявка на бронирование!</b>\n\n"
        f"#{booking_id}\n"
        f"🏠 {state_data['booking_object_name']}\n"
        f"📆 {state_data['booking_date']}\n"
        f"👤 {state_data['booking_user_name']}\n"
        f"📱 {state_data['booking_user_phone']}\n"
        f"Telegram ID: <code>{callback.from_user.id}</code>"
    )
    for admin_id in admins:
        try:
            await callback.bot.send_message(
                admin_id,
                admin_text,
                reply_markup=kb.get_admin_booking_detail_keyboard(booking_id, 'pending'),
                parse_mode="HTML"
            )
        except Exception as e:
            print(f"Не удалось уведомить админа {admin_id}: {e}")

@router.callback_query(F.data == "book_cancel")
async def callback_booking_cancel(callback: CallbackQuery, state: FSMContext):
    """Отмена бронирования"""
    await state.clear()
    await callback.message.edit_text(
        "❌ Бронирование отменено.\n\n"
        "Вы можете начать заново из главного меню.",
        reply_markup=kb.get_main_keyboard(is_admin(callback.from_user.id))
    )

# === Админ: Управление бронированиями ===

@router.callback_query(F.data == "admin_bookings")
async def callback_admin_bookings(callback: CallbackQuery):
    """Меню управления бронированиями"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    await callback.message.edit_text(
        "📅 <b>Управление бронированиями</b>",
        reply_markup=kb.get_admin_bookings_keyboard(),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "admin_book_pending")
async def callback_admin_book_pending(callback: CallbackQuery):
    """Список ожидающих бронирований"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    bookings = get_pending_bookings()
    if not bookings:
        await callback.message.edit_text(
            "📅 Нет ожидающих заявок.",
            reply_markup=kb.get_admin_bookings_keyboard()
        )
        return
    await callback.message.edit_text(
        f"⏳ <b>Ожидающие подтверждения ({len(bookings)})</b>",
        reply_markup=kb.get_admin_pending_bookings_keyboard(bookings),
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("admin_book_detail_"))
async def callback_admin_book_detail(callback: CallbackQuery):
    """Детали бронирования"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    booking_id = int(callback.data.replace("admin_book_detail_", ""))
    booking = get_booking_by_id(booking_id)
    if not booking:
        await callback.answer("Бронирование не найдено", show_alert=True)
        return

    status_text = {"pending": "⏳ Ожидает", "confirmed": "✅ Подтверждено", "cancelled": "❌ Отменено"}
    await callback.message.edit_text(
        f"📋 <b>Бронирование #{booking['id']}</b>\n\n"
        f"🏠 {booking['object_name']}\n"
        f"📆 {booking['date']}\n"
        f"👤 {booking['user_name']}\n"
        f"📱 {booking['user_phone']}\n"
        f"Telegram: <code>{booking['user_id']}</code>\n"
        f"Статус: {status_text.get(booking['status'], booking['status'])}\n"
        f"Создано: {booking['created_at']}",
        reply_markup=kb.get_admin_booking_detail_keyboard(booking_id, booking['status']),
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("admin_book_confirm_"))
async def callback_admin_book_confirm(callback: CallbackQuery):
    """Подтвердить бронирование"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    booking_id = int(callback.data.replace("admin_book_confirm_", ""))
    booking = get_booking_by_id(booking_id)
    if confirm_booking(booking_id, callback.from_user.id):
        await callback.answer("✅ Бронирование подтверждено", show_alert=True)
        # Обновляем детали
        booking = get_booking_by_id(booking_id)
        if booking:
            status_text = {"pending": "⏳ Ожидает", "confirmed": "✅ Подтверждено", "cancelled": "❌ Отменено"}
            await callback.message.edit_text(
                f"📋 <b>Бронирование #{booking['id']}</b>\n\n"
                f"🏠 {booking['object_name']}\n"
                f"📆 {booking['date']}\n"
                f"👤 {booking['user_name']}\n"
                f"📱 {booking['user_phone']}\n"
                f"Telegram: <code>{booking['user_id']}</code>\n"
                f"Статус: {status_text.get(booking['status'], booking['status'])}\n"
                f"Создано: {booking['created_at']}",
                reply_markup=kb.get_admin_booking_detail_keyboard(booking_id, booking['status']),
                parse_mode="HTML"
            )
            # Уведомляем пользователя
            try:
                await callback.bot.send_message(
                    booking['user_id'],
                    f"✅ <b>Ваше бронирование подтверждено!</b>\n\n"
                    f"#{booking['id']}\n"
                    f"🏠 {booking['object_name']}\n"
                    f"📆 {booking['date']}\n\n"
                    "Ждём вас!",
                    parse_mode="HTML"
                )
            except Exception:
                pass
    else:
        await callback.answer("❌ Не удалось подтвердить", show_alert=True)

@router.callback_query(F.data.startswith("admin_book_reject_"))
async def callback_admin_book_reject(callback: CallbackQuery):
    """Отклонить бронирование"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    booking_id = int(callback.data.replace("admin_book_reject_", ""))
    booking = get_booking_by_id(booking_id)
    if reject_booking(booking_id, callback.from_user.id):
        await callback.answer("❌ Бронирование отклонено", show_alert=True)
        # Возврат к списку ожидающих
        bookings = get_pending_bookings()
        if not bookings:
            await callback.message.edit_text(
                "📅 Нет ожидающих заявок.",
                reply_markup=kb.get_admin_bookings_keyboard()
            )
        else:
            await callback.message.edit_text(
                f"⏳ <b>Ожидающие подтверждения ({len(bookings)})</b>",
                reply_markup=kb.get_admin_pending_bookings_keyboard(bookings),
                parse_mode="HTML"
            )
        # Уведомляем пользователя
        if booking:
            try:
                await callback.bot.send_message(
                    booking['user_id'],
                    f"❌ <b>Ваше бронирование отклонено</b>\n\n"
                    f"#{booking['id']}\n"
                    f"🏠 {booking['object_name']}\n"
                    f"📆 {booking['date']}\n\n"
                    "Свяжитесь с поддержкой для уточнения.",
                    parse_mode="HTML"
                )
            except Exception:
                pass
    else:
        await callback.answer("❌ Ошибка", show_alert=True)

@router.callback_query(F.data.startswith("admin_book_cancel_"))
async def callback_admin_book_cancel(callback: CallbackQuery):
    """Отменить подтверждённое бронирование"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    booking_id = int(callback.data.replace("admin_book_cancel_", ""))
    booking = get_booking_by_id(booking_id)
    if cancel_booking(booking_id, callback.from_user.id):
        await callback.answer("🚫 Бронирование отменено", show_alert=True)
        # Обновляем детали
        booking = get_booking_by_id(booking_id)
        if booking:
            status_text = {"pending": "⏳ Ожидает", "confirmed": "✅ Подтверждено", "cancelled": "❌ Отменено"}
            await callback.message.edit_text(
                f"📋 <b>Бронирование #{booking['id']}</b>\n\n"
                f"🏠 {booking['object_name']}\n"
                f"📆 {booking['date']}\n"
                f"👤 {booking['user_name']}\n"
                f"📱 {booking['user_phone']}\n"
                f"Telegram: <code>{booking['user_id']}</code>\n"
                f"Статус: {status_text.get(booking['status'], booking['status'])}\n"
                f"Создано: {booking['created_at']}",
                reply_markup=kb.get_admin_booking_detail_keyboard(booking_id, booking['status']),
                parse_mode="HTML"
            )
        # Уведомляем пользователя
        if booking:
            try:
                await callback.bot.send_message(
                    booking['user_id'],
                    f"🚫 <b>Ваше бронирование отменено администратором</b>\n\n"
                    f"#{booking['id']}\n"
                    f"🏠 {booking['object_name']}\n"
                    f"📆 {booking['date']}\n\n"
                    "Свяжитесь с поддержкой для уточнения.",
                    parse_mode="HTML"
                )
            except Exception:
                pass
    else:
        await callback.answer("❌ Ошибка", show_alert=True)

# === Админ: Управление объектами ===

@router.callback_query(F.data == "admin_objects")
async def callback_admin_objects(callback: CallbackQuery):
    """Список объектов для управления"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    objects = get_all_objects_admin()
    await callback.message.edit_text(
        "🔧 <b>Управление объектами</b>\n\n"
        "🟢 активен | 🔴 отключён\n"
        "Нажмите для переключения:",
        reply_markup=kb.get_admin_objects_keyboard(objects),
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("admin_obj_toggle_"))
async def callback_admin_obj_toggle(callback: CallbackQuery):
    """Включить/отключить объект"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    object_id = int(callback.data.replace("admin_obj_toggle_", ""))
    obj = get_object_by_id(object_id)
    if obj:
        new_status = 0 if obj['is_active'] else 1
        update_object(object_id, is_active=new_status)
        status_text = "включён" if new_status else "отключён"
        await callback.answer(f"Объект {status_text}", show_alert=True)
    # Обновляем список
    objects = get_all_objects_admin()
    await callback.message.edit_text(
        "🔧 <b>Управление объектами</b>\n\n"
        "🟢 активен | 🔴 отключён\n"
        "Нажмите для переключения:",
        reply_markup=kb.get_admin_objects_keyboard(objects),
        parse_mode="HTML"
    )
