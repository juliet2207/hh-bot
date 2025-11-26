from aiogram.types import InlineKeyboardButton


def back_button(text: str, callback_data: str) -> list[InlineKeyboardButton]:
    """Single back button row."""
    return [InlineKeyboardButton(text=text, callback_data=callback_data)]


def row(*buttons: InlineKeyboardButton) -> list[InlineKeyboardButton]:
    """Helper to create a row of buttons."""
    return list(buttons)
