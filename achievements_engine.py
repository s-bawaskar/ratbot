import asyncio
import json
from pathlib import Path

import db
from database import UserAchievement
from economy import add_modaks

with open(Path(__file__).parent / "data" / "achievements.json", encoding="utf-8") as f:
    ACHIEVEMENTS: dict[str, dict] = {a["key"]: a for a in json.load(f)}

# achievement types backed by a single stat value fetched from the DB, keyed by the query
# that produces it — as opposed to catch_rarity/catch_speed_* which are checked in-memory
# against the arguments passed to check_achievements.
_STAT_QUERIES: dict[str, str] = {
    "catches_total": "SELECT COALESCE(SUM(count), 0) FROM user_rats WHERE user_id = $1 AND guild_id = $2",
    "modaks_total": "SELECT COALESCE(modaks, 0) FROM wallets WHERE user_id = $1 AND guild_id = $2",
    "unique_rats": "SELECT COUNT(*) FROM user_rats WHERE user_id = $1 AND guild_id = $2 AND count > 0",
    "aartis_total": "SELECT COALESCE(aartis_done, 0) FROM festival_progress WHERE user_id = $1 AND guild_id = $2",
}


async def _unlocked_keys(user_id: int, guild_id: int) -> set[str]:
    rows = await UserAchievement.collect("user_id = $1 AND guild_id = $2", user_id, guild_id)
    return {row.achievement_key for row in rows}


async def check_achievements(
    user_id: int, guild_id: int, *, caught_rarity: str | None = None, catch_seconds: float | None = None
) -> list[dict]:
    """Call after any action that could unlock an achievement. Returns newly unlocked achievement defs."""
    pool = db._get_pool()
    already = await _unlocked_keys(user_id, guild_id)
    candidates = [ach for ach in ACHIEVEMENTS.values() if ach["key"] not in already]

    # fetch every distinct stat this batch of candidates needs concurrently, instead of one
    # sequential round trip per candidate
    needed_types = {ach["type"] for ach in candidates if ach["type"] in _STAT_QUERIES}
    stats: dict[str, int] = {}
    if needed_types:
        results = await asyncio.gather(*(pool.fetchval(_STAT_QUERIES[t], user_id, guild_id) for t in needed_types))
        stats = dict(zip(needed_types, results))

    newly_unlocked: list[dict] = []
    for ach in candidates:
        ach_type = ach["type"]
        if ach_type in _STAT_QUERIES:
            earned = (stats.get(ach_type) or 0) >= ach["value"]
        elif ach_type == "catch_rarity":
            earned = caught_rarity == ach["rarity"]
        elif ach_type == "catch_speed_under":
            earned = catch_seconds is not None and catch_seconds <= ach["value"]
        elif ach_type == "catch_speed_over":
            earned = catch_seconds is not None and catch_seconds >= ach["value"]
        else:
            earned = False

        if earned:
            await UserAchievement.create(user_id=user_id, guild_id=guild_id, achievement_key=ach["key"])
            if ach["reward_modaks"]:
                await add_modaks(user_id, guild_id, ach["reward_modaks"], f"achievement:{ach['key']}")
            newly_unlocked.append(ach)

    return newly_unlocked
