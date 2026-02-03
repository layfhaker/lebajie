from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

import keyboards as kb
from database import (
    is_admin, get_admins, add_admin, remove_admin,
    get_faq, get_faq_by_id, add_faq, remove_faq,
    generate_ref_token, use_ref_token,
    set_user_in_support, is_user_in_support
)
from config import MAIN_ADMIN_ID

router = Router()

# === Состояния ===
class AdminStates(StatesGroup):
    waiting_faq_question = State()
    waiting_faq_answer = State()
    waiting_reply_to_user = State()

class UserStates(StatesGroup):
    in_support = State()

# === Стартовые команды ===

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    """Обработка /start и реф-ссылок"""
    await state.clear()

    # Проверяем реф-ссылку
    args = message.text.split()
    if len(args) > 1:
        token = args[1]
        if use_ref_token(token, message.from_user.id):
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
