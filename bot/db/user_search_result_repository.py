from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import UserSearchResult
from bot.utils.logging import get_logger

# Create logger for this module
repo_logger = get_logger(__name__)


class UserSearchResultRepository:
    """Repository for user search result-related database operations"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.logger = repo_logger.bind(repository="UserSearchResultRepository")

    async def create_user_search_result(
        self, user_id: int, search_query_id: int, vacancy_id: int, position: int
    ) -> UserSearchResult:
        """Create a new user search result record"""
        try:
            user_search_result = UserSearchResult(
                user_id=user_id,
                search_query_id=search_query_id,
                vacancy_id=vacancy_id,
                position=position,
            )
            self.session.add(user_search_result)
            await self.session.commit()
            await self.session.refresh(user_search_result)
            self.logger.info(
                f"Created user search result {user_search_result.id} for user {user_id}, query {search_query_id}, vacancy {vacancy_id}"
            )
            return user_search_result
        except Exception as e:
            self.logger.error(f"Error creating user search result for user {user_id}: {e}")
            await self.session.rollback()
            raise

    async def mark_vacancy_as_clicked(self, user_id: int, vacancy_id: int) -> bool:
        """Mark a vacancy as clicked by the user"""
        try:
            stmt = (
                update(UserSearchResult)
                .where(
                    UserSearchResult.user_id == user_id,
                    UserSearchResult.vacancy_id == vacancy_id,
                )
                .values(clicked=True)
            )
            result = await self.session.execute(stmt)
            await self.session.commit()

            if result.rowcount > 0:
                self.logger.info(f"Marked vacancy {vacancy_id} as clicked for user {user_id}")
                return True
            else:
                self.logger.warning(
                    f"No search result found to mark as clicked for user {user_id}, vacancy {vacancy_id}"
                )
                return False
        except Exception as e:
            self.logger.error(f"Error marking vacancy {vacancy_id} as clicked for user {user_id}: {e}")
            await self.session.rollback()
            raise

    async def bulk_create_user_search_results(self, results_data: list[dict]) -> list[UserSearchResult]:
        """Bulk create user search result records"""
        try:
            if not results_data:
                return []

            user_search_results = [UserSearchResult(**data) for data in results_data]
            self.session.add_all(user_search_results)
            await self.session.commit()

            # Refresh all objects to get their IDs
            for usr in user_search_results:
                await self.session.refresh(usr)

            self.logger.info(f"Bulk created {len(user_search_results)} user search results")
            return user_search_results
        except Exception as e:
            self.logger.error(f"Error bulk creating user search results: {e}")
            await self.session.rollback()
            raise
