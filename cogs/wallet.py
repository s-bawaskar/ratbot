from datetime import timedelta

import discord
from discord import app_commands
from discord.ext import commands

import cooldowns
from achievements_engine import check_achievements
from economy import add_modaks, get_wallet

DAILY_AMOUNT = 500
DAILY_COOLDOWN = timedelta(hours=24)


class Wallet(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(description="Claim your daily Modaks")
    async def daily(self, interaction: discord.Interaction) -> None:
        assert interaction.guild is not None
        await interaction.response.defer()
        user_id, guild_id = interaction.user.id, interaction.guild.id

        remaining = await cooldowns.check(user_id, guild_id, "daily", DAILY_COOLDOWN)
        if remaining:
            await interaction.followup.send(
                f"⏳ You already claimed your daily. Come back in {cooldowns.format_remaining(remaining)}.", ephemeral=True
            )
            return

        await add_modaks(user_id, guild_id, DAILY_AMOUNT, "daily")
        await interaction.followup.send(f"🍥 You received **{DAILY_AMOUNT} Modaks**!\n🙏 Your devotion has been rewarded.")

        unlocked = await check_achievements(user_id, guild_id)
        for ach in unlocked:
            await interaction.followup.send(f"🏆 {interaction.user.mention} unlocked achievement **{ach['name']}**!")

    @app_commands.command(description="Check your Modak balance")
    async def balance(self, interaction: discord.Interaction) -> None:
        assert interaction.guild is not None
        await interaction.response.defer()
        wallet = await get_wallet(interaction.user.id, interaction.guild.id)
        await interaction.followup.send(f"🍥 You have **{wallet.modaks:,} Modaks**.")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Wallet(bot))
