import db
from database import Transaction, Wallet


async def get_wallet(user_id: int, guild_id: int) -> Wallet:
    return await Wallet.get_or_create(user_id=user_id, guild_id=guild_id, defaults={"modaks": 0})


async def add_modaks(user_id: int, guild_id: int, amount: int, reason: str) -> int:
    """Atomically adds `amount` to the user's balance, so concurrent rewards (e.g. a catch
    landing at the same time as an achievement payout) never clobber each other."""
    pool = db._get_pool()
    new_balance = await pool.fetchval(
        "INSERT INTO wallets (user_id, guild_id, modaks) VALUES ($1, $2, $3) "
        "ON CONFLICT (user_id, guild_id) DO UPDATE SET modaks = wallets.modaks + $3 "
        "RETURNING modaks",
        user_id,
        guild_id,
        amount,
    )
    await Transaction.create(user_id=user_id, guild_id=guild_id, delta=amount, reason=reason)
    return new_balance
