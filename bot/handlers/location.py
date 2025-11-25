"""Handler for /location command"""

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from bot.db import UserRepository
from bot.db.database import get_db_session
from bot.services.hh_service import hh_service
from bot.utils.logging import get_logger

logger = get_logger(__name__)

router = Router()


def register_location_handlers(router_instance: Router):
    """Register location command handlers"""
    try:
        router_instance.include_router(router)
        logger.info("Location handlers registered successfully")
    except Exception as e:
        logger.error(f"Failed to register location handlers: {e}")


@router.message(Command("location"))
async def location_handler(message: Message):
    """Handler for the /location command to set user's city"""
    user_id = str(message.from_user.id)
    username = message.from_user.username or "N/A"

    # Extract city name from message
    parts = message.text.split(maxsplit=1)
    city_name = parts[1] if len(parts) > 1 else None

    logger.info(f"Location command received from user {user_id} (@{username}) with city: '{city_name}'")

    db_session = await get_db_session()
    if not db_session:
        await message.answer("Sorry, database is unavailable. Please try again later.")
        return

    try:
        user_repo = UserRepository(db_session)

        # If no city provided, show current city or help
        if not city_name:
            city_info = await user_repo.get_user_city(user_id)
            if city_info and city_info[0]:
                await message.answer(
                    f"📍 Your current location: <b>{city_info[0]}</b>\n\n"
                    "To change your location, use:\n"
                    "<code>/location Москва</code>\n"
                    "<code>/location Санкт-Петербург</code>\n"
                    "<code>/location Новосибирск</code>\n\n"
                    "Or use <code>/location clear</code> to remove your location.",
                    parse_mode="HTML",
                )
            else:
                await message.answer(
                    "📍 You haven't set your location yet.\n\n"
                    "Set your city to filter job searches by location:\n"
                    "<code>/location Москва</code>\n"
                    "<code>/location Санкт-Петербург</code>\n"
                    "<code>/location Новосибирск</code>\n\n"
                    "Example: <code>/location Москва</code>",
                    parse_mode="HTML",
                )
            return

        # Handle clear command
        if city_name.lower() in ["clear", "удалить", "сбросить", "none", "null"]:
            success = await user_repo.update_user_city(user_id, None, None)
            if success:
                await message.answer("✅ Location cleared. Job searches will not be filtered by city.")
            else:
                await message.answer("❌ Failed to clear location. Please try again.")
            return

        # Check if HH service is available
        if not hh_service.session:
            await message.answer("Sorry, the job search service is currently unavailable. Please try again later.")
            return

        # Find area ID for the city
        await message.answer(f"🔍 Looking up city '{city_name}'...")
        area_id = await hh_service.find_area_by_name(city_name)

        if not area_id:
            await message.answer(
                f"❌ City '{city_name}' not found.\n\n"
                "Please check the spelling and try again.\n"
                "Common cities:\n"
                "• Москва\n"
                "• Санкт-Петербург\n"
                "• Новосибирск\n"
                "• Екатеринбург\n"
                "• Казань\n"
                "• Нижний Новгород\n"
                "• Челябинск\n"
                "• Самара\n"
                "• Омск\n"
                "• Ростов-на-Дону"
            )
            return

        # Update user's city
        success = await user_repo.update_user_city(user_id, city_name, area_id)
        if success:
            await message.answer(
                f"✅ Location set to: <b>{city_name}</b>\n\n" "All job searches will now be filtered by this city.",
                parse_mode="HTML",
            )
            logger.success(f"User {user_id} set location to {city_name} (area_id: {area_id})")
        else:
            await message.answer("❌ Failed to set location. Please try again.")

    except Exception as e:
        logger.error(f"Failed to handle location command for user {user_id}: {e}")
        await message.answer("Sorry, there was an error processing your request. Please try again later.")
    finally:
        await db_session.close()
