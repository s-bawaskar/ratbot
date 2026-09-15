from database import Transaction, Wallet


async def get_wallet(user_id: int, guild_id: int) -> Wallet:
    return await Wallet.get_or_create(user_id=user_id, guild_id=guild_id, defaults={"modaks": 0})


async def add_modaks(user_id: int, guild_id: int, amount: int, reason: str) -> int:
    wallet = await get_wallet(user_id, guild_id)
    wallet.modaks = wallet.modaks + amount
    await wallet.save()
    await Transaction.create(user_id=user_id, guild_id=guild_id, delta=amount, reason=reason)
    return wallet.modaks
