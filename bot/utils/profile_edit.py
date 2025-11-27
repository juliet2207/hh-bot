from __future__ import annotations

from bot.services import user_service

CLEAR_COMMANDS = {"clear", "удалить", "сбросить", "none", "null"}


def is_clear_command(raw: str | None) -> bool:
    return (raw or "").strip().lower() in CLEAR_COMMANDS


async def update_user_prefs(tg_id: str, **kwargs):
    """Convenience helper to update user preferences via repository."""
    if not kwargs:
        return
    await user_service.update_preferences(tg_id, **kwargs)


async def load_user(tg_id: str):
    return await user_service.get_user_by_tg_id(tg_id)


def split_name(raw: str) -> tuple[str | None, str | None]:
    """Split raw name into first/last (last optional)."""
    if not raw:
        return None, None
    parts = raw.split(maxsplit=1)
    first = parts[0].strip()
    last = parts[1].strip() if len(parts) > 1 else None
    return first, last
