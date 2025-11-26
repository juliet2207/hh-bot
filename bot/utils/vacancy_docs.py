import re

from bot.db import VacancyRepository
from bot.db.database import get_db_session
from bot.utils.logging import get_logger

logger = get_logger(__name__)


def sanitize_cover_letter_text(text: str) -> str:
    """Strip headings/markdown noise from cover letters and collapse to one paragraph."""
    cleaned = re.sub(r"(?m)^\\s*#+\\s*", "", text)  # markdown headers
    cleaned = re.sub(r"(?im)^\\s*optimized resume:?", "", cleaned)  # stray headings
    cleaned = cleaned.replace("**", "").replace("__", "")
    cleaned = " ".join(cleaned.split())
    return cleaned


async def ensure_vacancy_db_id(vacancy: dict) -> int | None:
    """Ensure vacancy dict has db_id by fetching via hh_vacancy_id if missing."""
    vacancy_db_id = vacancy.get("db_id")
    hh_vacancy_id = vacancy.get("id")
    if vacancy_db_id or not hh_vacancy_id:
        return vacancy_db_id

    db_session = await get_db_session()
    if not db_session:
        return None

    try:
        vac_repo = VacancyRepository(db_session)
        vacancy_obj = await vac_repo.get_vacancy_by_hh_id(str(hh_vacancy_id))
        if vacancy_obj:
            vacancy_db_id = vacancy_obj.id
            vacancy["db_id"] = vacancy_db_id
            return vacancy_db_id
    except Exception as e:
        logger.error(f"Failed to fetch vacancy by hh_id {hh_vacancy_id}: {e}")
    finally:
        await db_session.close()

    return None
