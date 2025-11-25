from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import User
from bot.utils.logging import get_logger

# Create logger for this module
repo_logger = get_logger(__name__)


class UserRepository:
    """Repository for user-related database operations"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.logger = repo_logger.bind(repository="UserRepository")

    async def get_or_create_user(self, tg_user_id: str, **kwargs) -> User:
        """Get existing user or create a new one"""
        try:
            # Try to get existing user
            stmt = select(User).where(User.tg_user_id == tg_user_id)
            result = await self.session.execute(stmt)
            user = result.scalar_one_or_none()

            if user:
                # Update user info if provided
                update_data = {k: v for k, v in kwargs.items() if hasattr(user, k) and v is not None}
                if update_data:
                    update_stmt = update(User).where(User.tg_user_id == tg_user_id).values(**update_data)
                    await self.session.execute(update_stmt)
                    await self.session.commit()
                    # Refresh the user object to get updated data
                    await self.session.refresh(user)
                    self.logger.debug(f"Updated user {tg_user_id} with data: {update_data}")
                return user
            else:
                # Create new user
                user_data = {"tg_user_id": tg_user_id, **kwargs}
                user = User(**user_data)
                self.session.add(user)
                await self.session.commit()
                await self.session.refresh(user)
                self.logger.info(f"Created new user with ID {user.id}, tg_user_id {tg_user_id}")
                return user
        except Exception as e:
            self.logger.error(f"Error getting/creating user {tg_user_id}: {e}")
            await self.session.rollback()
            raise

    async def get_user_by_id(self, user_id: int) -> User | None:
        """Get user by internal ID"""
        try:
            stmt = select(User).where(User.id == user_id)
            result = await self.session.execute(stmt)
            user = result.scalar_one_or_none()
            if user:
                self.logger.debug(f"Retrieved user with ID {user_id}")
            else:
                self.logger.debug(f"User with ID {user_id} not found")
            return user
        except Exception as e:
            self.logger.error(f"Error getting user by ID {user_id}: {e}")
            raise

    async def update_user_preferences(self, tg_user_id: str, preferences: dict) -> bool:
        """Update user preferences"""
        try:
            stmt = update(User).where(User.tg_user_id == tg_user_id).values(preferences=preferences)
            result = await self.session.execute(stmt)
            await self.session.commit()

            if result.rowcount > 0:
                self.logger.info(f"Updated preferences for user {tg_user_id}")
                return True
            else:
                self.logger.warning(f"No user found to update preferences for {tg_user_id}")
                return False
        except Exception as e:
            self.logger.error(f"Error updating preferences for user {tg_user_id}: {e}")
            await self.session.rollback()
            raise

    async def update_user_city(self, tg_user_id: str, city: str, hh_area_id: str | None = None) -> bool:
        """Update user's city and HH.ru area ID"""
        try:
            stmt = update(User).where(User.tg_user_id == tg_user_id).values(city=city, hh_area_id=hh_area_id)
            result = await self.session.execute(stmt)
            await self.session.commit()

            if result.rowcount > 0:
                self.logger.info(f"Updated city for user {tg_user_id}: {city} (area_id: {hh_area_id})")
                return True
            else:
                self.logger.warning(f"No user found to update city for {tg_user_id}")
                return False
        except Exception as e:
            self.logger.error(f"Error updating city for user {tg_user_id}: {e}")
            await self.session.rollback()
            raise

    async def get_user_city(self, tg_user_id: str) -> tuple[str, str | None] | None:
        """Get user's city and HH.ru area ID. Returns (city, hh_area_id) or None."""
        try:
            stmt = select(User.city, User.hh_area_id).where(User.tg_user_id == tg_user_id)
            result = await self.session.execute(stmt)
            row = result.first()
            if row and row[0]:
                return (row[0], row[1])
            return None
        except Exception as e:
            self.logger.error(f"Error getting city for user {tg_user_id}: {e}")
            return None
