from aiogram import Router

from bot.handlers.profile import edit, preferences, search_settings, view

router = Router()


def register_profile_handlers(router_instance: Router):
    router_instance.include_router(view.router)
    router_instance.include_router(edit.router)
    router_instance.include_router(search_settings.router)
    router_instance.include_router(preferences.router)
