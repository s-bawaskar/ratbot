from datetime import datetime, timedelta, timezone

import db
import permissions


async def check(user_id: int, guild_id: int, key: str, duration: timedelta) -> timedelta | None:
    """Atomically claims a cooldown if it isn't active, returning None on success or the
    remaining time if it's still active. The bot owner bypasses cooldowns entirely.

    The claim itself is a single conditional upsert so two overlapping requests (e.g. a
    double-tapped command) can't both slip through before either one's write lands.
    """
    if permissions.is_owner(user_id):
        return None
    pool = db._get_pool()
    now = datetime.now(timezone.utc)
    new_expiry = now + duration
    claimed = await pool.fetchval(
        "INSERT INTO cooldowns (user_id, guild_id, command_key, expires_at) VALUES ($1, $2, $3, $4) "
        "ON CONFLICT (user_id, guild_id, command_key) DO UPDATE SET expires_at = $4 "
        "WHERE cooldowns.expires_at <= now() "
        "RETURNING expires_at",
        user_id,
        guild_id,
        key,
        new_expiry,
    )
    if claimed is not None:
        return None
    existing = await pool.fetchval(
        "SELECT expires_at FROM cooldowns WHERE user_id = $1 AND guild_id = $2 AND command_key = $3",
        user_id,
        guild_id,
        key,
    )
    return (existing - now) if existing else None


def format_remaining(remaining: timedelta) -> str:
    total = int(remaining.total_seconds())
    hours, rem = divmod(total, 3600)
    minutes = rem // 60
    return f"{hours}h {minutes}m" if hours else f"{minutes}m"
