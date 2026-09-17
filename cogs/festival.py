import random
from datetime import timedelta

import discord
from discord import app_commands
from discord.ext import commands

import cooldowns
from achievements_engine import check_achievements
from database import FestivalProgress
from economy import add_modaks


async def _get_progress(user_id: int, guild_id: int) -> FestivalProgress:
    return await FestivalProgress.get_or_create(
        user_id=user_id,
        guild_id=guild_id,
        defaults={"pujas_done": 0, "aartis_done": 0, "prasad_collected": 0, "festival_xp": 0},
    )


async def _announce_achievements(interaction: discord.Interaction, user_id: int, guild_id: int) -> None:
    unlocked = await check_achievements(user_id, guild_id)
    for ach in unlocked:
        await interaction.followup.send(f"🏆 {interaction.user.mention} unlocked achievement **{ach['name']}**!")


class Festival(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(description="Perform Puja for Modaks and Festival XP")
    async def puja(self, interaction: discord.Interaction) -> None:
        assert interaction.guild is not None
        await interaction.response.defer()
        user_id, guild_id = interaction.user.id, interaction.guild.id
        remaining = await cooldowns.check(user_id, guild_id, "puja", timedelta(hours=1))
        if remaining:
            await interaction.followup.send(f"🙏 You already performed Puja. Come back in {cooldowns.format_remaining(remaining)}.", ephemeral=True)
            return

        progress = await _get_progress(user_id, guild_id)
        progress.pujas_done = progress.pujas_done + 1
        progress.festival_xp = progress.festival_xp + 50
        await progress.save()
        await add_modaks(user_id, guild_id, 250, "puja")
        await interaction.followup.send("🙏 You performed Puja.\n\n🍥 +250 Modaks\n✨ +50 Festival XP")
        await _announce_achievements(interaction, user_id, guild_id)

    @app_commands.command(description="Perform Aarti for bigger Modak and XP rewards")
    async def aarti(self, interaction: discord.Interaction) -> None:
        assert interaction.guild is not None
        await interaction.response.defer()
        user_id, guild_id = interaction.user.id, interaction.guild.id
        remaining = await cooldowns.check(user_id, guild_id, "aarti", timedelta(hours=6))
        if remaining:
            await interaction.followup.send(f"🪔 You already performed Aarti. Come back in {cooldowns.format_remaining(remaining)}.", ephemeral=True)
            return

        progress = await _get_progress(user_id, guild_id)
        progress.aartis_done = progress.aartis_done + 1
        progress.festival_xp = progress.festival_xp + 100
        await progress.save()
        await add_modaks(user_id, guild_id, 500, "aarti")
        await interaction.followup.send("🪔 Evening Aarti completed!\n\n🍥 +500 Modaks\n✨ +100 Festival XP")
        await _announce_achievements(interaction, user_id, guild_id)

    @app_commands.command(description="Receive Prasad — a random festival reward")
    async def prasad(self, interaction: discord.Interaction) -> None:
        assert interaction.guild is not None
        await interaction.response.defer()
        user_id, guild_id = interaction.user.id, interaction.guild.id
        remaining = await cooldowns.check(user_id, guild_id, "prasad", timedelta(hours=3))
        if remaining:
            await interaction.followup.send(f"🥥 You already received Prasad. Come back in {cooldowns.format_remaining(remaining)}.", ephemeral=True)
            return

        progress = await _get_progress(user_id, guild_id)
        progress.prasad_collected = progress.prasad_collected + 1
        progress.festival_xp = progress.festival_xp + 25
        await progress.save()

        reward = random.choice(["modaks_small", "modaks_big", "xp"])
        if reward == "modaks_small":
            amount = random.randint(50, 150)
            await add_modaks(user_id, guild_id, amount, "prasad")
            desc = f"🍥 +{amount} Modaks"
        elif reward == "modaks_big":
            amount = random.randint(300, 600)
            await add_modaks(user_id, guild_id, amount, "prasad")
            desc = f"🍥 +{amount} Modaks (a generous helping!)"
        else:
            bonus_xp = random.randint(50, 100)
            progress.festival_xp = progress.festival_xp + bonus_xp
            await progress.save()
            desc = f"✨ +{bonus_xp} bonus Festival XP"

        await interaction.followup.send(f"🥥 You received Prasad!\n\n{desc}\n✨ +25 Festival XP")
        await _announce_achievements(interaction, user_id, guild_id)

    @app_commands.command(description="View your Ganesh Chaturthi festival progress")
    async def festival(self, interaction: discord.Interaction) -> None:
        assert interaction.guild is not None
        await interaction.response.defer()
        progress = await _get_progress(interaction.user.id, interaction.guild.id)
        embed = discord.Embed(title="🪔 Ganesh Chaturthi Progress", color=0xE67E22)
        embed.add_field(name="🙏 Pujas", value=str(progress.pujas_done))
        embed.add_field(name="🪔 Aartis", value=str(progress.aartis_done))
        embed.add_field(name="🥥 Prasad", value=str(progress.prasad_collected))
        embed.add_field(name="✨ Festival XP", value=str(progress.festival_xp))
        await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Festival(bot))
