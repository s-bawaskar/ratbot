import discord
from discord import app_commands
from discord.ext import commands

import db
import rats

CATEGORIES = {
    "richest": (
        "🍥 Richest",
        "SELECT user_id, modaks AS value FROM wallets WHERE guild_id=$1 ORDER BY modaks DESC LIMIT 10",
        "Modaks",
    ),
    "most_rats": (
        "🐀 Most Mushaks",
        "SELECT user_id, SUM(count) AS value FROM user_rats WHERE guild_id=$1 GROUP BY user_id ORDER BY value DESC LIMIT 10",
        "Mushaks",
    ),
    "best_collection": (
        "🌟 Best Collection",
        "SELECT user_id, COUNT(*) AS value FROM user_rats WHERE guild_id=$1 AND count>0 GROUP BY user_id ORDER BY value DESC LIMIT 10",
        "unique Mushaks",
    ),
    "most_devout": (
        "🪔 Most Devout",
        "SELECT user_id, festival_xp AS value FROM festival_progress WHERE guild_id=$1 ORDER BY festival_xp DESC LIMIT 10",
        "Festival XP",
    ),
    "fastest_catch": (
        "⚡ Fastest Catch",
        "SELECT user_id, MIN(catch_seconds) AS value FROM catches WHERE guild_id=$1 GROUP BY user_id ORDER BY value ASC LIMIT 10",
        "seconds",
    ),
    "slowest_catch": (
        "🐌 Slowest Catch",
        "SELECT user_id, MAX(catch_seconds) AS value FROM catches WHERE guild_id=$1 GROUP BY user_id ORDER BY value DESC LIMIT 10",
        "seconds",
    ),
}


class Leaderboard(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(description="View the server leaderboards")
    @app_commands.describe(rat="Optional: rank by who has the most of a specific Mushak species")
    @app_commands.choices(category=[app_commands.Choice(name=v[0], value=k) for k, v in CATEGORIES.items()])
    @app_commands.autocomplete(rat=rats.autocomplete)
    async def leaderboard(self, interaction: discord.Interaction, category: str = "richest", rat: str | None = None) -> None:
        assert interaction.guild is not None
        await interaction.response.defer()
        pool = db._get_pool()

        if rat:
            rat_data = rats.get_rat(rat)
            if not rat_data:
                await interaction.followup.send("Unknown Mushak.", ephemeral=True)
                return
            emoji = rats.RARITY_EMOJI.get(rat_data["rarity"], "🐀")
            title = f"{emoji} Most {rat_data['name']}s"
            unit = rat_data["name"]
            rows = await pool.fetch(
                "SELECT user_id, count AS value FROM user_rats WHERE guild_id=$1 AND rat_key=$2 AND count>0 ORDER BY count DESC LIMIT 10",
                interaction.guild.id,
                rat,
            )
        else:
            title, query, unit = CATEGORIES[category]
            rows = await pool.fetch(query, interaction.guild.id)

        if not rows:
            await interaction.followup.send("Nobody's on the board yet!", ephemeral=True)
            return

        medals = ["🥇", "🥈", "🥉"]
        lines = []
        for i, row in enumerate(rows):
            medal = medals[i] if i < 3 else f"`#{i + 1}`"
            value = row["value"]
            value_str = f"{value:,.2f}" if isinstance(value, float) else f"{value:,}"
            lines.append(f"{medal} <@{row['user_id']}> — **{value_str}** {unit}")

        embed = discord.Embed(title=title, description="\n".join(lines), color=0x2ECC71)
        await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Leaderboard(bot))
