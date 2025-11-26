from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import Vacancy
from bot.utils.logging import get_logger

# Create logger for this module
repo_logger = get_logger(__name__)


class VacancyRepository:
    """Repository for vacancy-related database operations"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.logger = repo_logger.bind(repository="VacancyRepository")

    async def get_or_create_vacancy(
        self, hh_vacancy_id: str, **kwargs
    ) -> tuple[Vacancy, bool]:
        """Get existing vacancy or create a new one. Returns (vacancy, is_new)"""
        try:
            # Try to get existing vacancy
            stmt = select(Vacancy).where(Vacancy.hh_vacancy_id == hh_vacancy_id)
            result = await self.session.execute(stmt)
            vacancy = result.scalar_one_or_none()

            if vacancy:
                # Update vacancy info if provided
                update_data = {
                    k: v
                    for k, v in kwargs.items()
                    if hasattr(vacancy, k) and v is not None
                }
                if update_data:
                    update_stmt = (
                        update(Vacancy)
                        .where(Vacancy.hh_vacancy_id == hh_vacancy_id)
                        .values(**update_data)
                    )
                    await self.session.execute(update_stmt)
                    await self.session.commit()
                    self.logger.debug(
                        f"Updated vacancy {hh_vacancy_id} with data: {update_data}"
                    )
                return vacancy, False
            else:
                # Create new vacancy
                vacancy_data = {"hh_vacancy_id": hh_vacancy_id, **kwargs}
                vacancy = Vacancy(**vacancy_data)
                self.session.add(vacancy)
                await self.session.commit()
                await self.session.refresh(vacancy)
                self.logger.info(
                    f"Created new vacancy with ID {vacancy.id}, HH ID {hh_vacancy_id}"
                )
                return vacancy, True
        except Exception as e:
            self.logger.error(f"Error getting/creating vacancy {hh_vacancy_id}: {e}")
            await self.session.rollback()
            raise

    async def get_vacancy_by_id(self, vacancy_id: int) -> Vacancy | None:
        """Get vacancy by internal ID"""
        try:
            stmt = select(Vacancy).where(Vacancy.id == vacancy_id)
            result = await self.session.execute(stmt)
            vacancy = result.scalar_one_or_none()
            if vacancy:
                self.logger.debug(f"Retrieved vacancy with ID {vacancy_id}")
            else:
                self.logger.debug(f"Vacancy with ID {vacancy_id} not found")
            return vacancy
        except Exception as e:
            self.logger.error(f"Error getting vacancy by ID {vacancy_id}: {e}")
            raise

    async def get_vacancy_by_hh_id(self, hh_vacancy_id: str) -> Vacancy | None:
        """Get vacancy by HH.ru ID"""
        try:
            stmt = select(Vacancy).where(Vacancy.hh_vacancy_id == hh_vacancy_id)
            result = await self.session.execute(stmt)
            vacancy = result.scalar_one_or_none()
            if vacancy:
                self.logger.debug(f"Retrieved vacancy with HH ID {hh_vacancy_id}")
            else:
                self.logger.debug(f"Vacancy with HH ID {hh_vacancy_id} not found")
            return vacancy
        except Exception as e:
            self.logger.error(f"Error getting vacancy by HH ID {hh_vacancy_id}: {e}")
            raise

    async def get_vacancies_by_hh_ids(
        self, hh_vacancy_ids: list[str]
    ) -> dict[str, Vacancy]:
        """Get multiple vacancies by HH.ru IDs. Returns dict mapping hh_vacancy_id to Vacancy."""
        try:
            if not hh_vacancy_ids:
                return {}
            stmt = select(Vacancy).where(Vacancy.hh_vacancy_id.in_(hh_vacancy_ids))
            result = await self.session.execute(stmt)
            vacancies = result.scalars().all()
            vacancy_dict = {v.hh_vacancy_id: v for v in vacancies}
            self.logger.debug(
                f"Retrieved {len(vacancy_dict)} existing vacancies from {len(hh_vacancy_ids)} requested"
            )
            return vacancy_dict
        except Exception as e:
            self.logger.error(f"Error getting vacancies by HH IDs: {e}")
            raise

    async def bulk_create_vacancies(
        self, vacancies_data: list[dict]
    ) -> dict[str, Vacancy]:
        """Bulk create vacancies. Returns dict mapping hh_vacancy_id to Vacancy.
        Uses PostgreSQL ON CONFLICT to handle duplicates."""
        try:
            if not vacancies_data:
                return {}

            # Use PostgreSQL INSERT ... ON CONFLICT DO NOTHING for efficient bulk insert
            stmt = insert(Vacancy).values(vacancies_data)
            stmt = stmt.on_conflict_do_nothing(index_elements=["hh_vacancy_id"])

            await self.session.execute(stmt)
            await self.session.flush()  # Flush to get IDs, but don't commit yet

            # Fetch all inserted/existing vacancies (including ones that already existed)
            hh_ids = [v["hh_vacancy_id"] for v in vacancies_data]
            vacancy_dict = await self.get_vacancies_by_hh_ids(hh_ids)

            await self.session.commit()

            self.logger.info(
                f"Bulk created/retrieved {len(vacancy_dict)} vacancies from {len(vacancies_data)} provided"
            )
            return vacancy_dict
        except Exception as e:
            self.logger.error(f"Error bulk creating vacancies: {e}")
            await self.session.rollback()
            raise
