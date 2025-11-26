from aiogram import F, Router, types
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext

from bot.handlers.profile.states import CANCEL_COMMANDS, EditPreferences, EditProfile, EditSearchFilters
from bot.utils.i18n import t
from bot.utils.lang import resolve_lang

router = Router()


@router.message(
    StateFilter(EditProfile, EditSearchFilters, EditPreferences),
    F.text.casefold().in_(CANCEL_COMMANDS),
)
async def cancel_edit(message: types.Message, state: FSMContext):
    await state.clear()
    lang = await resolve_lang(str(message.from_user.id), message.from_user.language_code if message.from_user else None)
    await message.answer(t("profile.edit_cancelled", lang))
