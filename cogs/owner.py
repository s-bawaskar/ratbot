import discord
from discord import app_commands
from discord.ext import commands

import db
import permissions
import rats
from economy import add_modaks


class Owner(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(description="(OWNER) Give Modaks to a user in this server")
    @permissions.owner_only()
    async def ownergive(self, interaction: discord.Interaction, user: discord.User, amount: int) -> None:
        assert interaction.guild is not None
        await interaction.response.defer(ephemeral=True)
        new_balance = await add_modaks(user.id, interaction.guild.id, amount, "owner_grant")
        await interaction.followup.send(f"Gave {amount:,} Modaks to {user.mention}. New balance: {new_balance:,}.", ephemeral=True)

    @app_commands.command(description="(OWNER) Give a specific Mushak to a user in this server")
    @app_commands.describe(rat="Which Mushak to give", count="How many")
    @permissions.owner_only()
    async def ownergiverat(self, interaction: discord.Interaction, user: discord.User, rat: str, count: int = 1) -> None:
        assert interaction.guild is not None
        rat_data = rats.get_rat(rat)
        if not rat_data:
            await interaction.response.send_message("Unknown Mushak.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        pool = db._get_pool()
        await pool.execute(
            "INSERT INTO user_rats (user_id, guild_id, rat_key, count) VALUES ($1, $2, $3, $4) "
            "ON CONFLICT (user_id, guild_id, rat_key) DO UPDATE SET count = user_rats.count + $4",
            user.id,
            interaction.guild.id,
            rat,
            count,
        )
        await interaction.followup.send(f"Gave {count}x {rat_data['name']} to {user.mention}.", ephemeral=True)

    @ownergiverat.autocomplete("rat")
    async def rat_autocomplete(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        return [app_commands.Choice(name=r["name"], value=r["id"]) for r in rats.search(current)]


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Owner(bot))
