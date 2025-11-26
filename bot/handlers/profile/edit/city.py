from aiogram import F, Router, types
from aiogram.fsm.context import FSMContext

from bot.db.database import get_db_session
from bot.db.user_repository import UserRepository
from bot.handlers.profile.states import EditProfile
from bot.services.hh_service import hh_service
from bot.utils.i18n import t
from bot.utils.lang import resolve_lang

router = Router()


@router.callback_query(F.data == "edit_city")
async def cb_edit_city(call: types.CallbackQuery, state: FSMContext):
    lang = await resolve_lang(str(call.from_user.id), call.from_user.language_code if call.from_user else None)
    await call.message.answer(t("profile.edit_city_prompt", lang))
    await state.set_state(EditProfile.city)
    await call.answer()


@router.message(EditProfile.city)
async def save_city(message: types.Message, state: FSMContext):
    city_input = (message.text or "").strip()
    user_id = str(message.from_user.id)
    lang = await resolve_lang(user_id, message.from_user.language_code if message.from_user else None)

    if not city_input:
        await message.answer(t("profile.edit_city_empty", lang))
        return

    if city_input.lower() in {"clear", "удалить", "сбросить", "none", "null"}:
        async with await get_db_session() as session:
            repo = UserRepository(session)
            await repo.update_user_city(user_id, None, None)
        await message.answer(t("profile.edit_city_cleared", lang))
        await state.clear()
        return

    if not hh_service.session:
        await message.answer(t("profile.search_city_service_unavailable", lang))
        return

    await message.answer(t("profile.edit_city_lookup", lang).format(city=city_input))
    area_id = await hh_service.find_area_by_name(city_input)

    if not area_id:
        await message.answer(t("profile.edit_city_not_found", lang).format(city=city_input))
        return

    async with await get_db_session() as session:
        repo = UserRepository(session)
        await repo.update_user_city(user_id, city_input, area_id)

    await message.answer(t("profile.edit_city_updated", lang).format(city=city_input))
    await state.clear()
