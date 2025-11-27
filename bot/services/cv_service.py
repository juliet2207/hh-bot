from __future__ import annotations

from bot.db import CVRepository, CVType
from bot.db.database import db_session


async def get_cv(user_id: int, vacancy_db_id: int, doc_type: CVType):
    async with db_session() as session:
        if not session:
            return None
        repo = CVRepository(session)
        return await repo.get_cv(user_id, vacancy_db_id, doc_type)


async def upsert_cv(user_id: int, vacancy_db_id: int, text: str, doc_type: CVType):
    async with db_session() as session:
        if not session:
            return False
        repo = CVRepository(session)
        return await repo.upsert_cv(user_id, vacancy_db_id, text, doc_type)
