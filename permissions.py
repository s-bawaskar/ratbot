import discord
from discord import app_commands

import config


def is_owner(user_id: int) -> bool:
    return user_id == config.OWNER_ID


def owner_only():
    """Command check: only the bot owner, in any server."""

    async def predicate(interaction: discord.Interaction) -> bool:
        if is_owner(interaction.user.id):
            return True
        raise app_commands.MissingPermissions(["owner"])

    return app_commands.check(predicate)


def admin_or_owner():
    """Command check: the bot owner (anywhere), or anyone with Manage Server in the current guild."""

    async def predicate(interaction: discord.Interaction) -> bool:
        if is_owner(interaction.user.id):
            return True
        if isinstance(interaction.user, discord.Member) and interaction.user.guild_permissions.manage_guild:
            return True
        raise app_commands.MissingPermissions(["manage_guild"])

    return app_commands.check(predicate)
