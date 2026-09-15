import json
from pathlib import Path

import db
from database import UserAchievement
from economy import add_modaks

with open(Path(__file__).parent / "data" / "achievements.json", encoding="utf-8") as f:
    ACHIEVEMENTS: dict[str, dict] = {a["key"]: a for a in json.load(f)}


async def _unlocked_keys(user_id: int, guild_id: int) -> set[str]:
    rows = await UserAchievement.collect("user_id = $1 AND guild_id = $2", user_id, guild_id)
    return {row.achievement_key for row in rows}


async def check_achievements(
    user_id: int, guild_id: int, *, caught_rarity: str | None = None, catch_seconds: float | None = None
) -> list[dict]:
    """Call after any action that could unlock an achievement. Returns newly unlocked achievement defs."""
    pool = db._get_pool()
    already = await _unlocked_keys(user_id, guild_id)
    newly_unlocked: list[dict] = []

    for ach in ACHIEVEMENTS.values():
        if ach["key"] in already:
            continue

        earned = False
        if ach["type"] == "catches_total":
            total = await pool.fetchval(
                "SELECT COALESCE(SUM(count), 0) FROM user_rats WHERE user_id = $1 AND guild_id = $2", user_id, guild_id
            )
            earned = total >= ach["value"]
        elif ach["type"] == "modaks_total":
            modaks = await pool.fetchval("SELECT modaks FROM wallets WHERE user_id = $1 AND guild_id = $2", user_id, guild_id)
            earned = (modaks or 0) >= ach["value"]
        elif ach["type"] == "unique_rats":
            unique = await pool.fetchval(
                "SELECT COUNT(*) FROM user_rats WHERE user_id = $1 AND guild_id = $2 AND count > 0", user_id, guild_id
            )
            earned = unique >= ach["value"]
        elif ach["type"] == "catch_rarity":
            earned = caught_rarity == ach["rarity"]
        elif ach["type"] == "aartis_total":
            aartis = await pool.fetchval(
                "SELECT aartis_done FROM festival_progress WHERE user_id = $1 AND guild_id = $2", user_id, guild_id
            )
            earned = (aartis or 0) >= ach["value"]
        elif ach["type"] == "catch_speed_under":
            earned = catch_seconds is not None and catch_seconds <= ach["value"]
        elif ach["type"] == "catch_speed_over":
            earned = catch_seconds is not None and catch_seconds >= ach["value"]

        if earned:
            await UserAchievement.create(user_id=user_id, guild_id=guild_id, achievement_key=ach["key"])
            if ach["reward_modaks"]:
                await add_modaks(user_id, guild_id, ach["reward_modaks"], f"achievement:{ach['key']}")
            newly_unlocked.append(ach)

    return newly_unlocked
