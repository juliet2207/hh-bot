from functools import lru_cache
from pathlib import Path

from bot.utils.logging import get_logger

logger = get_logger(__name__)

# Prefer project-level prompts directory (one level above /bot), but fall back to bot/prompts
_root_prompts = Path(__file__).resolve().parent.parent.parent / "prompts"
_bot_prompts = Path(__file__).resolve().parent.parent / "prompts"
PROMPTS_DIR_CANDIDATES = [_root_prompts, _bot_prompts]


@lru_cache(maxsize=32)
def load_prompt(name: str) -> str:
    """Load prompt text from prompts/{name}.txt with caching."""
    filename = f"{name}.txt"
    for base_dir in PROMPTS_DIR_CANDIDATES:
        path = base_dir / filename
        try:
            return path.read_text(encoding="utf-8").strip()
        except FileNotFoundError:
            continue
        except Exception as e:
            logger.error(f"Failed to load prompt {name} from {path}: {e}")
            return ""

    missing_paths = ", ".join(
        str((base / filename).resolve()) for base in PROMPTS_DIR_CANDIDATES
    )
    logger.error(f"Prompt file not found in any known location: {missing_paths}")
    return ""
