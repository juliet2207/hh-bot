from aiogram import Router

from bot.handlers.search.commands import router as commands_router
from bot.handlers.search.pagination import router as pagination_router
from bot.handlers.search.vacancy.detail import router as vacancy_detail_router
from bot.handlers.search.vacancy.documents import router as vacancy_docs_router

router = Router()


def register_search_handlers(router_instance: Router):
    router_instance.include_router(commands_router)
    router_instance.include_router(pagination_router)
    router_instance.include_router(vacancy_detail_router)
    router_instance.include_router(vacancy_docs_router)
