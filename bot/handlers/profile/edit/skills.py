from aiogram import F, Router, types
from aiogram.fsm.context import FSMContext

from bot.db.database import get_db_session
from bot.db.user_repository import UserRepository
from bot.handlers.profile.states import EditProfile
from bot.utils.i18n import t
from bot.utils.lang import resolve_lang
from bot.utils.profile_helpers import normalize_skills

router = Router()


@router.callback_query(F.data == "edit_skills")
async def cb_edit_skills(call: types.CallbackQuery, state: FSMContext):
    lang = await resolve_lang(str(call.from_user.id), call.from_user.language_code if call.from_user else None)
    await call.message.answer(t("profile.edit_skills_prompt", lang))
    await state.set_state(EditProfile.skills)
    await call.answer()


@router.message(EditProfile.skills)
async def save_skills(message: types.Message, state: FSMContext):
    skills_input = (message.text or "").strip()
    user_id = str(message.from_user.id)
    lang = await resolve_lang(user_id, message.from_user.language_code if message.from_user else None)

    if not skills_input:
        await message.answer(t("profile.edit_skills_empty", lang))
        return

    if skills_input.lower() in {"clear", "удалить", "сбросить", "none", "null"}:
        async with await get_db_session() as session:
            repo = UserRepository(session)
            await repo.update_preferences(user_id, skills=None)
        await message.answer(t("profile.edit_skills_cleared", lang))
        await state.clear()
        return

    skills = normalize_skills(skills_input)
    if not skills:
        await message.answer(t("profile.edit_skills_none", lang))
        return

    async with await get_db_session() as session:
        repo = UserRepository(session)
        await repo.update_preferences(user_id, skills=skills)

    await message.answer(t("profile.edit_skills_updated", lang))
    await state.clear()
