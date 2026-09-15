import json
import random
from pathlib import Path

RARITY_ORDER = ["common", "uncommon", "rare", "epic", "legendary", "mythic", "devotional", "divine", "secret"]

RARITY_EMOJI = {
    "common": "⚪",
    "uncommon": "🟢",
    "rare": "🔵",
    "epic": "🟣",
    "legendary": "🟠",
    "mythic": "🔴",
    "devotional": "🪔",
    "divine": "🌟",
    "secret": "❓",
}

RARITY_COLOR = {
    "common": 0xB0B0B0,
    "uncommon": 0x2ECC71,
    "rare": 0x3498DB,
    "epic": 0x9B59B6,
    "legendary": 0xE67E22,
    "mythic": 0xE74C3C,
    "devotional": 0xFF8C00,
    "divine": 0xF1C40F,
    "secret": 0x2C2F33,
}

with open(Path(__file__).parent / "data" / "rats.json", encoding="utf-8") as f:
    _raw = json.load(f)

RATS: dict[str, dict] = {rat["id"]: rat for rat in _raw}


def get_rat(rat_key: str) -> dict | None:
    return RATS.get(rat_key)


_ASSETS_DIR = Path(__file__).parent / "assets" / "rats"


def get_image_path(rat_key: str) -> Path | None:
    """Finds the rat's image on disk regardless of extension (.png/.jpg/etc), or None if missing."""
    matches = list(_ASSETS_DIR.glob(f"{rat_key}.*"))
    return matches[0] if matches else None


def weighted_spawn(rarity: str | None = None) -> dict:
    """Pick a random rat for a normal spawn, weighted by spawn_weight. Excludes event-only rats
    unless that's the only way to satisfy a requested rarity."""
    pool = [r for r in RATS.values() if not r.get("event_tag")]
    if rarity:
        filtered = [r for r in pool if r["rarity"] == rarity]
        pool = filtered or [r for r in RATS.values() if r["rarity"] == rarity] or pool
    if not pool:
        pool = list(RATS.values())
    weights = [r["spawn_weight"] for r in pool]
    return random.choices(pool, weights=weights, k=1)[0]


def search(current: str, limit: int = 25) -> list[dict]:
    """Rat species whose name contains `current` (case-insensitive), for autocomplete."""
    current_lower = current.lower()
    return [r for r in RATS.values() if current_lower in r["name"].lower()][:limit]


def rarity_rank(rarity: str) -> int:
    return RARITY_ORDER.index(rarity) if rarity in RARITY_ORDER else -1
