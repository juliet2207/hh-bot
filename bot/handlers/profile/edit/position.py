from aiogram import F, Router, types
from aiogram.fsm.context import FSMContext

from bot.db.database import get_db_session
from bot.db.user_repository import UserRepository
from bot.handlers.profile.states import EditProfile
from bot.utils.i18n import t
from bot.utils.lang import resolve_lang

router = Router()


@router.callback_query(F.data == "edit_position")
async def cb_edit_position(call: types.CallbackQuery, state: FSMContext):
    lang = await resolve_lang(str(call.from_user.id), call.from_user.language_code if call.from_user else None)
    await call.message.answer(t("profile.edit_position_prompt", lang))
    await state.set_state(EditProfile.position)
    await call.answer()


@router.message(EditProfile.position)
async def save_position(message: types.Message, state: FSMContext):
    position = (message.text or "").strip()
    user_id = str(message.from_user.id)
    lang = await resolve_lang(user_id, message.from_user.language_code if message.from_user else None)

    if not position:
        await message.answer(t("profile.edit_position_empty", lang))
        return

    if position.lower() in {"clear", "удалить", "сбросить", "none", "null"}:
        async with await get_db_session() as session:
            repo = UserRepository(session)
            await repo.update_preferences(user_id, desired_position=None)
        await message.answer(t("profile.edit_position_cleared", lang))
        await state.clear()
        return

    async with await get_db_session() as session:
        repo = UserRepository(session)
        await repo.update_preferences(user_id, desired_position=position)

    await message.answer(t("profile.edit_position_updated", lang))
    await state.clear()
