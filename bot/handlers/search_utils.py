"""Utility functions for search handlers"""

import asyncio
import time

from bot.db import (
    SearchQueryRepository,
    UserSearchResultRepository,
    VacancyRepository,
)
from bot.db.database import get_db_session
from bot.db.models import UserSearchResult
from bot.services.hh_service import hh_service
from bot.utils.logging import get_logger

logger = get_logger(__name__)

# In-memory cache for search results
# Key: (user_db_id, query_text), Value: (vacancies, total_found, timestamp)
_search_cache: dict[tuple[int, str], tuple[list[dict], int, float]] = {}
CACHE_TTL = 1800  # 30 minutes in seconds


def format_salary(salary: dict | None) -> str:
    """Format salary information from HH API response"""
    if not salary:
        return "Not specified"

    from_str = salary.get("from")
    to_str = salary.get("to")
    currency = salary.get("currency", "")

    if from_str and to_str:
        return f"{from_str}-{to_str} {currency}"
    elif from_str:
        return f"{from_str}+ {currency}"
    elif to_str:
        return f"up to {to_str} {currency}"
    return "Not specified"


def format_vacancy(vacancy: dict, position: int) -> str:
    """Format a single vacancy for display"""
    name = vacancy.get("name", "N/A")

    employer = vacancy.get("employer", {})
    company = employer.get("name", "N/A") if isinstance(employer, dict) else "N/A"

    salary_str = format_salary(vacancy.get("salary"))

    area = vacancy.get("area", {})
    location = area.get("name", "N/A") if isinstance(area, dict) else "N/A"

    url = vacancy.get("alternate_url", "N/A")

    return (
        f"{position}. <b>{name}</b>\n"
        f"   Company: {company}\n"
        f"   Salary: {salary_str}\n"
        f"   Location: {location}\n"
        f"   <a href='{url}'>View on HH.ru</a>\n\n"
    )


def extract_vacancy_data(vacancy: dict) -> dict:
    """Extract vacancy data for database storage"""
    employer = vacancy.get("employer", {})
    area = vacancy.get("area", {})
    snippet = vacancy.get("snippet", {})

    return {
        "hh_vacancy_id": str(vacancy.get("id", "")),
        "title": vacancy.get("name", "N/A"),
        "company": employer.get("name", "N/A") if isinstance(employer, dict) else "N/A",
        "location": area.get("name", "N/A") if isinstance(area, dict) else "N/A",
        "url": vacancy.get("alternate_url", "N/A"),
        "description": (snippet.get("requirement", "N/A") if isinstance(snippet, dict) else "N/A"),
    }


async def store_search_results(
    user_db_id: int,
    query_text: str,
    vacancies: list[dict],
    response_time: int,
    per_page: int = 100,
) -> bool:
    """Store all search results in database. Duplicates are automatically skipped."""
    db_session = await get_db_session()
    if not db_session:
        logger.warning("Could not get database session for storing search results")
        return False

    try:
        search_repo = SearchQueryRepository(db_session)
        vacancy_repo = VacancyRepository(db_session)
        user_search_result_repo = UserSearchResultRepository(db_session)

        # Create search query record
        search_query = await search_repo.create_search_query(
            user_id=user_db_id,
            query_text=query_text,
            search_params={"per_page": per_page},
            results_count=len(vacancies),
            response_time=response_time,
        )

        # Extract all vacancy data
        all_vacancy_data = [extract_vacancy_data(vacancy) for vacancy in vacancies]
        hh_vacancy_ids = [v["hh_vacancy_id"] for v in all_vacancy_data]

        # Check which vacancies already exist (bulk query)
        existing_vacancies = await vacancy_repo.get_vacancies_by_hh_ids(hh_vacancy_ids)
        existing_ids = set(existing_vacancies.keys())

        # Separate new and existing vacancies
        new_vacancies_data = [v for v in all_vacancy_data if v["hh_vacancy_id"] not in existing_ids]

        # Bulk create new vacancies
        if new_vacancies_data:
            new_vacancies_dict = await vacancy_repo.bulk_create_vacancies(new_vacancies_data)
            # Merge with existing
            existing_vacancies.update(new_vacancies_dict)
        else:
            new_vacancies_dict = {}

        # Now we have all vacancies in existing_vacancies dict
        # Create user_search_results in bulk
        user_search_results_data = []
        for i, vacancy_data in enumerate(all_vacancy_data, 1):
            hh_id = vacancy_data["hh_vacancy_id"]
            vacancy_obj = existing_vacancies.get(hh_id)
            if vacancy_obj:
                user_search_results_data.append(
                    {
                        "user_id": user_db_id,
                        "search_query_id": search_query.id,
                        "vacancy_id": vacancy_obj.id,
                        "position": i,
                    }
                )

        # Bulk create user search results
        if user_search_results_data:
            await user_search_result_repo.bulk_create_user_search_results(user_search_results_data)

        new_count = len(new_vacancies_dict)
        existing_count = len(vacancies) - new_count

        logger.info(
            f"Stored search query and {len(vacancies)} results for user {user_db_id} "
            f"(new: {new_count}, existing: {existing_count})"
        )
        return True
    except Exception as e:
        logger.error(f"Failed to store search results for user {user_db_id}: {e}")
        return False
    finally:
        await db_session.close()


async def perform_search(
    query: str,
    per_page: int = 100,
    max_pages: int | None = None,
    search_in_name_only: bool = True,
    area_id: str | None = None,
) -> tuple[dict | None, int]:
    """Perform search and return all results with response time.
    Handles timeouts and retries automatically.

    Args:
        query: Search query text
        per_page: Number of results per page (max 100)
        max_pages: Maximum number of pages to fetch (None = all pages)
        search_in_name_only: If True, search only in vacancy names using 'name:' prefix (default: True)
        area_id: HH.ru area ID to filter by location (optional)
    """
    start_time = time.time()
    all_items = []
    total_found = 0
    page = 0
    max_retries = 3
    retry_delay = 2  # seconds

    while True:
        # Check if we've reached max pages limit
        if max_pages and page >= max_pages:
            break

        retries = 0
        page_results = None

        # Retry logic for handling timeouts and errors
        while retries < max_retries:
            try:
                page_results = await hh_service.search_vacancies(
                    query,
                    area=area_id,
                    page=page,
                    per_page=per_page,
                    search_in_name_only=search_in_name_only,
                )
                if page_results:
                    break
                # If None returned, it means an error occurred (handled in hh_service)
                retries += 1
                if retries < max_retries:
                    logger.warning(f"Failed to fetch page {page} (attempt {retries}/{max_retries}), retrying...")
                    await asyncio.sleep(retry_delay * retries)  # Exponential backoff
            except Exception as e:
                # Handle unexpected exceptions
                logger.warning(f"Exception fetching page {page} (attempt {retries + 1}/{max_retries}): {e}")
                retries += 1
                if retries < max_retries:
                    await asyncio.sleep(retry_delay * retries)  # Exponential backoff
                else:
                    logger.error(f"Failed to fetch page {page} after {max_retries} attempts")
                    break

        if not page_results:
            logger.warning(f"Could not fetch page {page}, stopping pagination")
            break

        items = page_results.get("items", [])
        if not items:
            # No more items, we've reached the end
            break

        all_items.extend(items)

        # Get total found count from first page
        if page == 0:
            total_found = page_results.get("found", 0)
            pages_count = page_results.get("pages", 0)

        # Check if we've fetched all pages
        if page >= pages_count - 1:
            break

        page += 1

        # Small delay between pages to avoid rate limiting
        await asyncio.sleep(0.5)

    response_time = int((time.time() - start_time) * 1000)  # Convert to milliseconds

    # Combine all results into a single response structure
    combined_results = {
        "items": all_items,
        "found": total_found,
        "pages": pages_count if page == 0 else (page + 1),
    }

    logger.info(f"Search completed: found {total_found} total, fetched {len(all_items)} items in {response_time}ms")

    return combined_results, response_time


def format_search_page(query: str, vacancies: list[dict], page: int, per_page: int, total_found: int) -> str:
    """Format a single page of search results"""
    start_idx = page * per_page
    end_idx = start_idx + per_page
    page_vacancies = vacancies[start_idx:end_idx]

    response = f"🔍 Found {total_found} vacancies for '{query}':\n\n"

    for i, vacancy in enumerate(page_vacancies, 1):
        global_position = start_idx + i
        response += format_vacancy(vacancy, global_position)

    total_pages = (len(vacancies) + per_page - 1) // per_page
    response += f"\n📄 Page {page + 1} of {total_pages}"

    return response


def create_pagination_keyboard(query: str, page: int, total_pages: int) -> list[list[dict[str, str]]]:
    """Create inline keyboard for pagination with page numbers and ellipsis"""
    keyboard = []
    buttons = []

    # Always show Previous button if not on first page
    if page > 0:
        buttons.append(
            {
                "text": "◀️",
                "callback_data": f"search_page:{query}:{page - 1}",
            }
        )

    # Calculate which page numbers to show
    current_page_num = page + 1  # 1-based for display

    if total_pages <= 7:
        # Show all pages if 7 or fewer
        for p in range(1, total_pages + 1):
            if p == current_page_num:
                buttons.append(
                    {
                        "text": f"• {p} •",
                        "callback_data": f"search_page:{query}:{p - 1}",
                    }
                )
            else:
                buttons.append(
                    {
                        "text": str(p),
                        "callback_data": f"search_page:{query}:{p - 1}",
                    }
                )
    else:
        # Smart pagination with ellipsis
        # Calculate range around current page
        start_page = max(2, current_page_num - 1)
        end_page = min(total_pages - 1, current_page_num + 1)

        # Always show first page (if not in the range we'll show)
        if current_page_num == 1:
            buttons.append(
                {
                    "text": "• 1 •",
                    "callback_data": f"search_page:{query}:0",
                }
            )
        else:
            buttons.append(
                {
                    "text": "1",
                    "callback_data": f"search_page:{query}:0",
                }
            )
            # Add ellipsis after first page if there's a gap
            if start_page > 2:
                buttons.append(
                    {
                        "text": "...",
                        "callback_data": "noop",  # Non-functional button
                    }
                )

        # Add pages around current (skip 1 and total_pages as they're handled separately)
        for p in range(start_page, end_page + 1):
            if p == 1 or p == total_pages:
                continue  # Skip, already handled
            if p == current_page_num:
                buttons.append(
                    {
                        "text": f"• {p} •",
                        "callback_data": f"search_page:{query}:{p - 1}",
                    }
                )
            else:
                buttons.append(
                    {
                        "text": str(p),
                        "callback_data": f"search_page:{query}:{p - 1}",
                    }
                )

        # Add ellipsis before last page if there's a gap
        if end_page < total_pages - 1:
            buttons.append(
                {
                    "text": "...",
                    "callback_data": "noop",  # Non-functional button
                }
            )

        # Always show last page (if not already shown)
        if total_pages > 1:
            if current_page_num == total_pages:
                buttons.append(
                    {
                        "text": f"• {total_pages} •",
                        "callback_data": f"search_page:{query}:{total_pages - 1}",
                    }
                )
            else:
                buttons.append(
                    {
                        "text": str(total_pages),
                        "callback_data": f"search_page:{query}:{total_pages - 1}",
                    }
                )

    # Always show Next button if not on last page
    if page < total_pages - 1:
        buttons.append(
            {
                "text": "▶️",
                "callback_data": f"search_page:{query}:{page + 1}",
            }
        )

    if buttons:
        keyboard.append(buttons)

    return keyboard


def _cleanup_cache():
    """Remove expired cache entries"""
    current_time = time.time()
    expired_keys = [key for key, (_, _, timestamp) in _search_cache.items() if current_time - timestamp > CACHE_TTL]
    for key in expired_keys:
        del _search_cache[key]
    if expired_keys:
        logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")


def get_cached_vacancies(user_db_id: int, query_text: str) -> tuple[list[dict], int] | None:
    """Get cached vacancies if available. Returns None if not cached or expired."""
    _cleanup_cache()
    key = (user_db_id, query_text)
    if key in _search_cache:
        vacancies, total_found, timestamp = _search_cache[key]
        if time.time() - timestamp <= CACHE_TTL:
            logger.debug(f"Cache hit for user {user_db_id}, query '{query_text}' ({len(vacancies)} vacancies)")
            return vacancies, total_found
        else:
            # Expired, remove from cache
            del _search_cache[key]
            logger.debug(f"Cache expired for user {user_db_id}, query '{query_text}'")
    return None


def cache_vacancies(user_db_id: int, query_text: str, vacancies: list[dict], total_found: int):
    """Cache search results"""
    key = (user_db_id, query_text)
    _search_cache[key] = (vacancies, total_found, time.time())
    logger.debug(f"Cached {len(vacancies)} vacancies for user {user_db_id}, query '{query_text}'")


async def get_vacancies_from_db(user_db_id: int, query_text: str, use_cache: bool = True) -> tuple[list[dict], int]:
    """Get vacancies from database for a user's search query.
    Returns (vacancies_list, total_found).
    Uses cache if available and use_cache=True."""
    # Try cache first
    if use_cache:
        cached = get_cached_vacancies(user_db_id, query_text)
        if cached is not None:
            return cached

    # Cache miss or cache disabled, fetch from DB
    db_session = await get_db_session()
    if not db_session:
        logger.warning("Could not get database session for retrieving vacancies")
        return [], 0

    try:
        from sqlalchemy import select

        search_repo = SearchQueryRepository(db_session)

        # Get the most recent search query for this user with this query text
        search_query = await search_repo.get_latest_search_query(user_id=user_db_id, query_text=query_text)

        if not search_query:
            logger.warning(f"No search query found for user {user_db_id} with query '{query_text}'")
            return [], 0

        # Get all user search results with vacancies in one query using JOIN
        from bot.db.models import Vacancy

        stmt = (
            select(UserSearchResult, Vacancy)
            .join(Vacancy, UserSearchResult.vacancy_id == Vacancy.id)
            .where(UserSearchResult.search_query_id == search_query.id)
            .order_by(UserSearchResult.position)
        )
        result = await db_session.execute(stmt)
        rows = result.all()

        # Convert to dict format similar to HH API response
        vacancies = []
        for _, vacancy in rows:
            vacancy_dict = {
                "id": vacancy.hh_vacancy_id,
                "name": vacancy.title,
                "employer": {"name": vacancy.company or "N/A"},
                "area": {"name": vacancy.location or "N/A"},
                "alternate_url": vacancy.url or "N/A",
                "salary": (
                    {
                        "from": vacancy.salary_from,
                        "to": vacancy.salary_to,
                        "currency": vacancy.salary_currency,
                    }
                    if vacancy.salary_from or vacancy.salary_to
                    else None
                ),
            }
            vacancies.append(vacancy_dict)

        total_found = search_query.results_count

        # Cache the results
        if use_cache:
            cache_vacancies(user_db_id, query_text, vacancies, total_found)

        logger.debug(f"Retrieved {len(vacancies)} vacancies from DB for user {user_db_id}, query '{query_text}'")
        return vacancies, total_found

    except Exception as e:
        logger.error(f"Failed to get vacancies from DB for user {user_db_id}: {e}")
        return [], 0
    finally:
        await db_session.close()


async def format_search_response(query: str, results: dict, max_results: int = 3) -> str:
    """Format search results into a response message (legacy function, kept for compatibility)"""
    vacancies = results.get("items", [])
    found_count = results.get("found", 0)

    response = f"🔍 Found {found_count} vacancies for '{query}':\n\n"

    for i, vacancy in enumerate(vacancies[:max_results], 1):
        response += format_vacancy(vacancy, i)

    response += f"See more results on <a href='https://hh.ru/search/vacancy?text={query}'>HH.ru</a>"
    return response
