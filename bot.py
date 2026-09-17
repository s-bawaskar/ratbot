import asyncio
import logging

import discord
from discord import app_commands
from discord.ext import commands

import config
import db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ratbot")

intents = discord.Intents.default()
intents.message_content = True
intents.messages = True


class RatBotTree(app_commands.CommandTree):
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.guild is None:
            raise app_commands.CheckFailure("RATBOT only works inside a Discord server, not in DMs.")
        return True


bot = commands.Bot(command_prefix="!", intents=intents, help_command=None, tree_cls=RatBotTree)

EXTENSIONS = [
    "cogs.catch",
    "cogs.wallet",
    "cogs.profile",
    "cogs.achievements",
    "cogs.leaderboard",
    "cogs.festival",
    "cogs.help",
    "cogs.owner",
]


@bot.event
async def setup_hook() -> None:
    await db.connect(config.DATABASE_URL)
    for ext in EXTENSIONS:
        await bot.load_extension(ext)


_synced_once = False


@bot.event
async def on_ready() -> None:
    global _synced_once
    logger.info("Logged in as %s (%s)", bot.user, bot.user.id if bot.user else "?")
    if not _synced_once:
        # dev mode: sync per-guild only (instant), and wipe any stray global
        # registration from earlier so commands don't show up duplicated.
        for guild in bot.guilds:
            bot.tree.copy_global_to(guild=guild)
        bot.tree.clear_commands(guild=None)
        await bot.tree.sync()
        for guild in bot.guilds:
            await bot.tree.sync(guild=guild)
        logger.info("Synced commands to %d guild(s), cleared stray global registration", len(bot.guilds))
        _synced_once = True


@bot.event
async def on_guild_join(guild: discord.Guild) -> None:
    bot.tree.copy_global_to(guild=guild)
    await bot.tree.sync(guild=guild)
    logger.info("Joined guild %s (%s), synced commands", guild.name, guild.id)


@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError) -> None:
    if isinstance(error, app_commands.MissingPermissions):
        msg = "You don't have permission to use this command."
    elif isinstance(error, app_commands.CommandOnCooldown):
        msg = f"This command is on cooldown. Try again in {error.retry_after:.0f}s."
    elif isinstance(error, app_commands.CheckFailure):
        msg = str(error) or "You can't use this command here."
    else:
        logger.error("Unhandled app command error", exc_info=error)
        msg = "Something went wrong running that command."
    try:
        if interaction.response.is_done():
            await interaction.followup.send(msg, ephemeral=True)
        else:
            await interaction.response.send_message(msg, ephemeral=True)
    except discord.HTTPException:
        pass


async def main() -> None:
    try:
        await bot.start(config.DISCORD_TOKEN)
    finally:
        await db.close()


if __name__ == "__main__":
    asyncio.run(main())
