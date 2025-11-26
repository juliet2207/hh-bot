from difflib import get_close_matches

KNOWN_COMMANDS = ["/start", "/help", "/profile", "/preferences", "/search", "/resume"]


def _transliterate_layout(text: str, to_ru: bool = False) -> str:
    """Crude EN<->RU keyboard layout transliteration."""
    en = "qwertyuiop[]asdfghjkl;'zxcvbnm,./" + 'QWERTYUIOP{}ASDFGHJKL:"ZXCVBNM<>?'
    ru = "йцукенгшщзхъфывапролджэячсмитьбю." + "ЙЦУКЕНГШЩЗХЪФЫВАПРОЛДЖЭЯЧСМИТЬБЮ,"
    table = str.maketrans(en if to_ru else ru, ru if to_ru else en)
    return text.translate(table)


def suggest_command(text: str, lang: str) -> str | None:
    """
    Suggest the nearest known command using similarity matching and keyboard layout swap.
    Returns command string or None if nothing is close enough.
    """
    original = text.strip()
    normalized = original.lower()
    candidates = [normalized]

    # Try transliterated keyboard layout (e.g., /рудз -> /help, /hba -> /рга)
    ru_to_en = _transliterate_layout(normalized, to_ru=False)
    en_to_ru = _transliterate_layout(normalized, to_ru=True)
    for cand in (ru_to_en, en_to_ru):
        if cand != normalized:
            candidates.append(cand)

    for candidate in candidates:
        if not candidate.startswith("/"):
            continue
        matches = get_close_matches(candidate, KNOWN_COMMANDS, n=1, cutoff=0.5)
        if matches:
            return matches[0]
    return None
