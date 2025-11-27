from __future__ import annotations

from bot.db.database import db_session
from bot.db.user_repository import UserRepository


async def get_or_create_user(*, tg_user_id: str, **kwargs):
    async with db_session() as session:
        if not session:
            return None
        repo = UserRepository(session)
        return await repo.get_or_create_user(tg_user_id, **kwargs)


async def get_user_by_tg_id(tg_user_id: str):
    async with db_session() as session:
        if not session:
            return None
        repo = UserRepository(session)
        return await repo.get_user_by_tg_id(tg_user_id)


async def update_preferences(tg_user_id: str, **kwargs) -> bool:
    if not kwargs:
        return True
    async with db_session() as session:
        if not session:
            return False
        repo = UserRepository(session)
        return await repo.update_preferences(tg_user_id, **kwargs)


async def get_users_with_schedule():
    async with db_session() as session:
        if not session:
            return []
        repo = UserRepository(session)
        return await repo.get_users_with_schedule()


async def update_language_code(tg_user_id: str, language_code: str) -> bool:
    async with db_session() as session:
        if not session:
            return False
        repo = UserRepository(session)
        return await repo.update_language_code(tg_user_id, language_code)


async def update_user_city(
    tg_user_id: str, city: str | None, hh_area_id: str | None = None
) -> bool:
    async with db_session() as session:
        if not session:
            return False
        repo = UserRepository(session)
        return await repo.update_user_city(tg_user_id, city, hh_area_id)


async def update_search_filters(tg_user_id: str, **kwargs) -> bool:
    async with db_session() as session:
        if not session:
            return False
        repo = UserRepository(session)
        return await repo.update_search_filters(tg_user_id, **kwargs)


async def get_user_city(tg_user_id: str):
    async with db_session() as session:
        if not session:
            return None
        repo = UserRepository(session)
        return await repo.get_user_city(tg_user_id)


async def get_or_create_user_with_lang(
    tg_user_id: str,
    username: str | None,
    first_name: str | None,
    last_name: str | None,
    language_code: str | None,
):
    from bot.utils.i18n import detect_lang

    user = await get_or_create_user(
        tg_user_id=tg_user_id,
        username=username,
        first_name=first_name,
        last_name=last_name,
        language_code=language_code,
    )
    lang = detect_lang(language_code)
    if user and user.language_code:
        lang = detect_lang(user.language_code)
    return user, lang
