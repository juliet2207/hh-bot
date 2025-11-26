from aiogram import F, Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from bot.db.database import get_db_session
from bot.db.user_repository import UserRepository
from bot.handlers.profile.keyboards import preferences_keyboard
from bot.utils.i18n import detect_lang, t
from bot.utils.logging import get_logger

logger = get_logger(__name__)
router = Router()


async def send_preferences_view(message_obj: types.Message | types.CallbackQuery, tg_id: str, edit: bool = False):
    async with await get_db_session() as session:
        repo = UserRepository(session)
        user = await repo.get_user_by_tg_id(tg_id)

    lang = detect_lang(
        user.language_code
        if user
        else (
            message_obj.from_user.language_code
            if isinstance(message_obj, types.Message) and message_obj.from_user
            else None
        )
    )
    if not user:
        target = message_obj.message if isinstance(message_obj, types.CallbackQuery) else message_obj
        await target.answer(t("profile.no_profile", lang))
        if isinstance(message_obj, types.CallbackQuery):
            await message_obj.answer()
        return

    lang_name = t(f"profile.languages.{lang}", lang)
    text = t("profile.preferences_view", lang).format(language=lang_name)
    markup = preferences_keyboard(False, lang)

    target = message_obj.message if isinstance(message_obj, types.CallbackQuery) else message_obj
    if isinstance(message_obj, types.CallbackQuery) and edit:
        await target.edit_text(text, parse_mode="HTML", reply_markup=markup)
        await message_obj.answer()
    else:
        await target.answer(text, parse_mode="HTML", reply_markup=markup)
        if isinstance(message_obj, types.CallbackQuery):
            await message_obj.answer()


@router.message(Command("preferences"))
async def cmd_preferences(message: types.Message):
    await send_preferences_view(message, str(message.from_user.id))


@router.callback_query(F.data == "prefs_menu")
async def cb_prefs_menu(call: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await send_preferences_view(call, str(call.from_user.id), edit=True)


@router.callback_query(F.data == "prefs_back_profile")
async def cb_prefs_back_profile(call: types.CallbackQuery, state: FSMContext):
    await state.clear()
    from bot.handlers.profile.view import send_profile_view

    await send_profile_view(str(call.from_user.id), call.message)
    await call.answer()


@router.callback_query(F.data == "prefs_lang_menu")
async def cb_prefs_lang_menu(call: types.CallbackQuery, state: FSMContext):
    lang = detect_lang(call.from_user.language_code if call.from_user else None)
    buttons = [
        [types.InlineKeyboardButton(text=t("profile.languages.en", lang), callback_data="prefs_set_lang:en")],
        [types.InlineKeyboardButton(text=t("profile.languages.ru", lang), callback_data="prefs_set_lang:ru")],
        [types.InlineKeyboardButton(text=t("profile.buttons.back_profile", lang), callback_data="prefs_menu")],
    ]
    await call.message.answer(
        t("profile.preferences_lang_prompt", lang), reply_markup=types.InlineKeyboardMarkup(inline_keyboard=buttons)
    )
    await state.clear()
    await call.answer()


@router.callback_query(F.data.startswith("prefs_set_lang:"))
async def cb_prefs_set_lang(call: types.CallbackQuery, state: FSMContext):
    _, _, code = call.data.partition(":")
    if code not in {"en", "ru"}:
        lang = detect_lang(call.from_user.language_code if call.from_user else None)
        await call.message.answer(t("profile.preferences_lang_invalid", lang))
        await call.answer()
        return

    target_lang = detect_lang(code)
    async with await get_db_session() as session:
        repo = UserRepository(session)
        await repo.update_language_code(str(call.from_user.id), target_lang)

    lang_name = t(f"profile.languages.{target_lang}", target_lang)
    await call.message.answer(t("profile.preferences_lang_saved", target_lang).format(language=lang_name))
    await call.answer()
    await send_preferences_view(call, str(call.from_user.id), edit=True)
