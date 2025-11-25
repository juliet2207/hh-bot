"""Handler for /help command"""

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from bot.utils.logging import get_logger

logger = get_logger(__name__)

router = Router()


def register_help_handlers(router_instance: Router):
    """Register help command handlers"""
    try:
        router_instance.include_router(router)
        logger.info("Help handlers registered successfully")
    except Exception as e:
        logger.error(f"Failed to register help handlers: {e}")


@router.message(Command("help"))
async def help_handler(message: Message):
    """Handler for the /help command with comprehensive logging"""
    user_id = str(message.from_user.id)
    username = message.from_user.username or "N/A"

    logger.info(f"Help command received from user {user_id} (@{username})")

    try:
        help_message = (
            "📋 <b>HH Bot Help</b>\n\n"
            "<b>Available commands:</b>\n"
            "• /start - Show welcome message\n"
            "• /help - Show this help message\n"
            "• /search [query] - Search for job vacancies\n"
            "<b>Examples:</b>\n"
            "• <code>/search python developer</code>\n"
            "• <code>/search москва менеджер</code>\n\n"
            "Send me any job-related query and I'll help you find relevant vacancies on HH.ru!"
        )

        await message.answer(help_message, parse_mode="HTML")
        logger.debug(f"Help message sent to user {user_id}")

    except Exception as e:
        logger.error(f"Failed to handle help command for user {user_id}: {e}")
        try:
            await message.answer("Sorry, there was an error processing your request. Please try again later.")
        except Exception:
            logger.error(f"Failed to send error message to user {user_id}")
