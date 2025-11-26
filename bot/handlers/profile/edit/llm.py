from aiogram import F, Router, types
from aiogram.fsm.context import FSMContext

from bot.db.database import get_db_session
from bot.db.user_repository import UserRepository
from bot.handlers.profile.states import EditProfile
from bot.utils.i18n import t
from bot.utils.lang import resolve_lang
from bot.utils.logging import get_logger

logger = get_logger(__name__)
router = Router()


@router.callback_query(F.data == "edit_llm")
async def cb_edit_llm(call: types.CallbackQuery, state: FSMContext):
    lang = await resolve_lang(str(call.from_user.id), call.from_user.language_code if call.from_user else None)
    await call.message.answer(t("profile.edit_llm_prompt", lang), parse_mode="HTML")
    await state.set_state(EditProfile.llm)
    await call.answer()


@router.message(EditProfile.llm)
async def save_llm(message: types.Message, state: FSMContext):
    llm_raw = (message.text or "").strip()
    user_id = str(message.from_user.id)
    lang = await resolve_lang(user_id, message.from_user.language_code if message.from_user else None)

    if not llm_raw:
        await message.answer(t("profile.edit_llm_empty", lang))
        return

    if llm_raw.lower() in {"clear", "удалить", "сбросить", "none", "null"}:
        async with await get_db_session() as session:
            repo = UserRepository(session)
            await repo.update_preferences(user_id, llm_settings=None)
        await message.answer(t("profile.edit_llm_cleared", lang))
        await state.clear()
        return

    try:
        model, url, key = (s.strip() for s in llm_raw.split(";"))
    except ValueError:
        await message.answer(t("profile.edit_llm_bad_format", lang), parse_mode="HTML")
        return

    async with await get_db_session() as session:
        repo = UserRepository(session)
        await repo.update_preferences(user_id, llm_settings={"model": model, "base_url": url, "api_key": key})

    try:
        await message.delete()
    except Exception as e:
        logger.warning(f"Failed to delete message with LLM settings for user {user_id}: {e}")

    await message.answer(t("profile.edit_llm_updated", lang))
    await state.clear()
