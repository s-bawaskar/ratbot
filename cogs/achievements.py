import discord
from discord import app_commands
from discord.ext import commands

from achievements_engine import ACHIEVEMENTS
from database import UserAchievement


class Achievements(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(description="View your achievements")
    async def achievements(self, interaction: discord.Interaction) -> None:
        assert interaction.guild is not None
        await interaction.response.defer()
        rows = await UserAchievement.collect("user_id = $1 AND guild_id = $2", interaction.user.id, interaction.guild.id)
        unlocked = {r.achievement_key for r in rows}

        lines = []
        for ach in ACHIEVEMENTS.values():
            mark = "✅" if ach["key"] in unlocked else "🔒"
            lines.append(f"{mark} **{ach['name']}** — {ach['description']}")

        embed = discord.Embed(
            title=f"🏆 {interaction.user.display_name}'s Achievements",
            description=f"{len(unlocked)} / {len(ACHIEVEMENTS)} unlocked\n\n" + "\n".join(lines),
            color=0xF1C40F,
        )
        await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Achievements(bot))
