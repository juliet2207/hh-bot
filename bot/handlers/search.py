"""Handler for /search command"""

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message

from bot.db import SearchQueryRepository, UserRepository
from bot.db.database import get_db_session
from bot.handlers.search_utils import (
    cache_vacancies,
    create_pagination_keyboard,
    format_search_page,
    get_vacancies_from_db,
    perform_search,
    store_search_results,
)
from bot.services.hh_service import hh_service
from bot.utils.logging import get_logger

logger = get_logger(__name__)

router = Router()

# Constants
VACANCIES_PER_PAGE = 8


def register_search_handlers(router_instance: Router):
    """Register search command handlers"""
    try:
        router_instance.include_router(router)
        logger.info("Search handlers registered successfully")
    except Exception as e:
        logger.error(f"Failed to register search handlers: {e}")


@router.message(Command("search"))
async def search_handler(message: Message):
    """Handler for the /search command with comprehensive logging and database integration"""
    user_id = str(message.from_user.id)
    username = message.from_user.username or "N/A"

    # Extract search query from message
    query = message.text.split(maxsplit=1)[1] if len(message.text.split()) > 1 else ""

    logger.info(f"Search command received from user {user_id} (@{username}) with query: '{query}'")

    if not query:
        logger.warning(f"Empty search query from user {user_id}")
        try:
            await message.answer("Please provide a search query. Example: /search python developer")
        except Exception as e:
            logger.error(f"Failed to send empty query message to user {user_id}: {e}")
        return

    try:
        # Check if HH service is available
        if not hh_service.session:
            logger.error(f"HH service not available for user {user_id}")
            await message.answer("Sorry, the job search service is currently unavailable. Please try again later.")
            return

        # Get user from database to get user ID
        db_session = await get_db_session()
        user_db_id = None
        if db_session:
            try:
                user_repo = UserRepository(db_session)
                user = await user_repo.get_or_create_user(
                    tg_user_id=user_id,
                    username=message.from_user.username,
                    first_name=message.from_user.first_name,
                    last_name=message.from_user.last_name,
                    language_code=message.from_user.language_code,
                )
                user_db_id = user.id
            except Exception as e:
                logger.error(f"Failed to get user {user_id} from database: {e}")
            finally:
                await db_session.close()

        # Get user's city if set
        user_city_info = None
        if user_db_id:
            db_session = await get_db_session()
            if db_session:
                try:
                    user_repo = UserRepository(db_session)
                    user_city_info = await user_repo.get_user_city(user_id)
                except Exception as e:
                    logger.error(f"Failed to get user city for {user_id}: {e}")
                finally:
                    await db_session.close()

        # Show loading message
        loading_msg = await message.answer("🔍 Searching for vacancies... Please wait.")

        # Perform search - get all vacancies
        area_id = user_city_info[1] if user_city_info and user_city_info[1] else None
        logger.debug(
            f"Performing search for query '{query}' for user {user_id} "
            f"(city: {user_city_info[0] if user_city_info else 'any'}, area_id: {area_id})"
        )
        results, response_time = await perform_search(query, per_page=100, area_id=area_id)

        if not results or not results.get("items"):
            await loading_msg.delete()
            logger.info(f"No vacancies found for query '{query}' for user {user_id}")

            # Store search query even if no results found
            if user_db_id:
                db_session = await get_db_session()
                if db_session:
                    try:
                        search_repo = SearchQueryRepository(db_session)
                        await search_repo.create_search_query(
                            user_id=user_db_id,
                            query_text=query,
                            results_count=0,
                            response_time=response_time,
                        )
                        logger.debug(f"Stored search query with no results for user {user_db_id}")
                    except Exception as e:
                        logger.error(f"Failed to store search query for user {user_db_id}: {e}")
                    finally:
                        await db_session.close()

            await message.answer(
                f"Sorry, I couldn't find any vacancies for '{query}'. Please try a different search term."
            )
            return

        # Get all vacancies
        vacancies = results["items"]
        total_found = results.get("found", len(vacancies))

        # Store all search results in database
        if user_db_id:
            await store_search_results(user_db_id, query, vacancies, response_time, per_page=100)
            # Cache the results for fast pagination
            cache_vacancies(user_db_id, query, vacancies, total_found)

        # Format first page
        page = 0
        total_pages = (len(vacancies) + VACANCIES_PER_PAGE - 1) // VACANCIES_PER_PAGE
        response_text = format_search_page(query, vacancies, page, VACANCIES_PER_PAGE, total_found)

        # Create pagination keyboard
        keyboard = create_pagination_keyboard(query, page, total_pages)
        reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard) if keyboard else None

        await loading_msg.delete()
        await message.answer(
            response_text,
            parse_mode="HTML",
            disable_web_page_preview=True,
            reply_markup=reply_markup,
        )
        logger.success(
            f"Search results sent to user {user_id} for query '{query}' ({len(vacancies)} vacancies, {total_pages} pages)"
        )

    except Exception as e:
        logger.error(f"Failed to handle search command for user {user_id}, query '{query}': {e}")
        try:
            await message.answer("Sorry, there was an error processing your search request. Please try again later.")
        except Exception:
            logger.error(f"Failed to send error message to user {user_id}")


@router.callback_query(F.data.startswith("search_page:"))
async def pagination_handler(callback: CallbackQuery):
    """Handler for pagination callbacks"""
    # Handle non-functional buttons (like ellipsis)
    if callback.data == "noop":
        await callback.answer()
        return

    user_id = str(callback.from_user.id)
    username = callback.from_user.username or "N/A"

    try:
        # Parse callback data: search_page:query:page
        parts = callback.data.split(":", 2)
        if len(parts) != 3:
            await callback.answer("Invalid pagination request", show_alert=True)
            return

        query = parts[1]
        page = int(parts[2])

        logger.info(f"Pagination request from user {user_id} (@{username}): query '{query}', page {page}")

        # Get user from database
        db_session = await get_db_session()
        user_db_id = None
        if db_session:
            try:
                user_repo = UserRepository(db_session)
                user = await user_repo.get_or_create_user(
                    tg_user_id=user_id,
                    username=callback.from_user.username,
                    first_name=callback.from_user.first_name,
                    last_name=callback.from_user.last_name,
                    language_code=callback.from_user.language_code,
                )
                user_db_id = user.id
            except Exception as e:
                logger.error(f"Failed to get user {user_id} from database: {e}")
            finally:
                await db_session.close()

        if not user_db_id:
            await callback.answer("Error: user not found", show_alert=True)
            return

        # Get vacancies from database
        vacancies, total_found = await get_vacancies_from_db(user_db_id, query)

        if not vacancies:
            await callback.answer("No vacancies found for this search", show_alert=True)
            return

        # Calculate pagination
        total_pages = (len(vacancies) + VACANCIES_PER_PAGE - 1) // VACANCIES_PER_PAGE

        # Validate page number
        if page < 0 or page >= total_pages:
            await callback.answer("Invalid page number", show_alert=True)
            return

        # Check if user clicked on the current page (extract from message text)
        import re

        current_page_match = re.search(r"Page (\d+) of", callback.message.text or "")
        if current_page_match:
            current_page_num = int(current_page_match.group(1)) - 1  # Convert to 0-based
            if current_page_num == page:
                # User clicked on the current page, just answer callback
                await callback.answer()
                return

        # Format page
        response_text = format_search_page(query, vacancies, page, VACANCIES_PER_PAGE, total_found)

        # Create pagination keyboard
        keyboard = create_pagination_keyboard(query, page, total_pages)
        reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard) if keyboard else None

        # Update message
        try:
            await callback.message.edit_text(
                response_text,
                parse_mode="HTML",
                disable_web_page_preview=True,
                reply_markup=reply_markup,
            )
        except Exception as edit_error:
            # If message is not modified (same content), just answer callback
            if "not modified" in str(edit_error).lower():
                await callback.answer()
                return
            raise

        await callback.answer()
        logger.success(f"Page {page + 1} displayed for user {user_id} for query '{query}'")

    except ValueError as e:
        logger.error(f"Invalid page number in callback: {e}")
        await callback.answer("Invalid page number", show_alert=True)
    except Exception as e:
        logger.error(f"Failed to handle pagination for user {user_id}, query '{query}': {e}")
        await callback.answer(
            "Sorry, there was an error loading this page. Please try again.",
            show_alert=True,
        )
