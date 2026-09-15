from datetime import datetime, timedelta, timezone

import discord
from discord import app_commands
from discord.ext import commands

import permissions
from achievements_engine import check_achievements
from database import Cooldown
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

        if not permissions.is_owner(user_id):
            cd = await Cooldown.get_or_none(user_id=user_id, guild_id=guild_id, command_key="daily")
            now = datetime.now(timezone.utc)
            if cd and cd.expires_at > now:
                remaining = cd.expires_at - now
                hours, rem = divmod(int(remaining.total_seconds()), 3600)
                minutes = rem // 60
                await interaction.followup.send(f"⏳ You already claimed your daily. Come back in {hours}h {minutes}m.", ephemeral=True)
                return

            new_expiry = now + DAILY_COOLDOWN
            if cd:
                cd.expires_at = new_expiry
                await cd.save()
            else:
                await Cooldown.create(user_id=user_id, guild_id=guild_id, command_key="daily", expires_at=new_expiry)

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
