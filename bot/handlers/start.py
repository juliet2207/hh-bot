"""Handler for /start command"""

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from bot.db import UserRepository
from bot.db.database import get_db_session
from bot.services.hh_service import hh_service
from bot.services.openai_service import openai_service
from bot.utils.logging import get_logger

logger = get_logger(__name__)

router = Router()


def register_start_handlers(router_instance: Router):
    """Register start command handlers"""
    try:
        router_instance.include_router(router)
        logger.info("Start handlers registered successfully")
    except Exception as e:
        logger.error(f"Failed to register start handlers: {e}")


@router.message(Command("start"))
async def start_handler(message: Message):
    """Handler for the /start command with comprehensive logging and database integration"""
    user_id = str(message.from_user.id)
    username = message.from_user.username or "N/A"
    full_name = f"{message.from_user.first_name} {message.from_user.last_name or ''}".strip()
    language_code = message.from_user.language_code

    logger.info(f"Start command received from user {user_id} (@{username}, {full_name})")

    try:
        # Create or update user in database
        db_session = await get_db_session()
        if db_session:
            try:
                user_repo = UserRepository(db_session)
                user = await user_repo.get_or_create_user(
                    tg_user_id=user_id,
                    username=username,
                    first_name=message.from_user.first_name,
                    last_name=message.from_user.last_name,
                    language_code=language_code,
                )
                logger.debug(f"User {user_id} database record updated/created with ID {user.id}")
            except Exception as e:
                logger.error(f"Failed to update user {user_id} in database: {e}")
            finally:
                await db_session.close()
        else:
            logger.warning(f"Could not get database session for user {user_id}")

        welcome_message = (
            f"🤖 Hello, {full_name}!\n\n"
            f"Welcome to the HH Job Search Bot! I can help you find job opportunities on HH.ru.\n\n"
            f"Available commands:\n"
            f"• /start - Show this message\n"
            f"• /search [query] - Search for job vacancies (e.g., /search python developer)\n"
            f"• /help - Get help information\n\n"
            f"I'm ready to assist you with your job search! Send me a search query to find relevant vacancies."
        )

        await message.answer(welcome_message)
        logger.debug(f"Start message sent to user {user_id}")

        # Log service availability
        hh_available = hh_service.session is not None
        openai_available = openai_service._initialized

        service_status = (
            f"HH service: {'✓' if hh_available else '✗'}, OpenAI service: {'✓' if openai_available else '✗'}"
        )
        logger.info(f"Service availability for user {user_id}: {service_status}")

    except Exception as e:
        logger.error(f"Failed to handle start command for user {user_id}: {e}")
        try:
            await message.answer("Sorry, there was an error processing your request. Please try again later.")
        except Exception:
            logger.error(f"Failed to send error message to user {user_id}")
