import discord
from discord import app_commands
from discord.ext import commands

import config


class Help(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(description="Learn how to play RATBOT")
    async def help(self, interaction: discord.Interaction) -> None:
        embed = discord.Embed(
            title="🐀 RATBOT — How to Play",
            description="A wild Mushak spawns in set-up channels. Type `rat` to catch it — first to type it wins!",
            color=0xE67E22,
        )
        embed.add_field(
            name="🐀 Catching",
            value=(
                "Type `rat` when one spawns.\n"
                "`/collection` — your discovered species\n"
                "`/inventory` — your caught Mushaks\n"
                "`/dex` — browse every known species"
            ),
            inline=False,
        )
        embed.add_field(
            name="🍥 Economy",
            value="`/daily` — claim daily Modaks\n`/balance` — check your Modaks\n`/profile` — your stats",
            inline=False,
        )
        embed.add_field(
            name="🪔 Ganesh Chaturthi",
            value=(
                "`/puja` — 1h cooldown\n"
                "`/aarti` — 6h cooldown, bigger reward\n"
                "`/prasad` — 3h cooldown, random reward\n"
                "`/festival` — your festival progress"
            ),
            inline=False,
        )
        embed.add_field(
            name="🏆 Progress",
            value="`/achievements` — your achievements\n`/leaderboard` — server rankings (try the `rat` option for per-species rankings!)",
            inline=False,
        )
        embed.add_field(
            name="🛡️ Admin",
            value=(
                "`/setup` / `/unsetup` — enable/disable spawns in a channel\n"
                "`/forcespawn` — spawn a Mushak immediately\n"
                "`/changetimings` — adjust how often Mushaks spawn"
            ),
            inline=False,
        )
        embed.set_footer(text="Found a bug or have feedback? Try /contactgod")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(description="Reach out to RATBOT's creator")
    async def contactgod(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message(
            f"🙏 Having trouble, found a bug, or just want to chat? Reach out to <@{config.OWNER_ID}>."
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Help(bot))
