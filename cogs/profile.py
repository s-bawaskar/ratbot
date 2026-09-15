import discord
from discord import app_commands
from discord.ext import commands

import db
import rats
from economy import get_wallet


class Profile(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(description="View your RATBOT profile")
    async def profile(self, interaction: discord.Interaction, user: discord.User | None = None) -> None:
        assert interaction.guild is not None
        await interaction.response.defer()
        target = user or interaction.user
        wallet = await get_wallet(target.id, interaction.guild.id)
        pool = db._get_pool()
        rows = await pool.fetch(
            "SELECT rat_key, count FROM user_rats WHERE user_id=$1 AND guild_id=$2 AND count>0",
            target.id,
            interaction.guild.id,
        )
        total_owned = sum(r["count"] for r in rows)
        unique = len(rows)
        rarest = None
        for r in rows:
            rat = rats.get_rat(r["rat_key"])
            if rat and (rarest is None or rats.rarity_rank(rat["rarity"]) > rats.rarity_rank(rarest["rarity"])):
                rarest = rat

        embed = discord.Embed(title=f"🐀 {target.display_name}", color=0xE67E22)
        embed.add_field(name="🍥 Modaks", value=f"{wallet.modaks:,}")
        embed.add_field(name="🐀 Collection", value=f"{unique} / {len(rats.RATS)} unique ({total_owned} total)")
        if rarest:
            embed.add_field(name="⭐ Rarest", value=f"{rats.RARITY_EMOJI.get(rarest['rarity'], '')} {rarest['name']}")
        await interaction.followup.send(embed=embed)

    @app_commands.command(description="View your Mushak inventory")
    async def inventory(self, interaction: discord.Interaction) -> None:
        assert interaction.guild is not None
        await interaction.response.defer()
        pool = db._get_pool()
        rows = await pool.fetch(
            "SELECT rat_key, count FROM user_rats WHERE user_id=$1 AND guild_id=$2 AND count>0 ORDER BY count DESC",
            interaction.user.id,
            interaction.guild.id,
        )
        if not rows:
            await interaction.followup.send("You don't have any Mushaks yet — go catch one!", ephemeral=True)
            return
        lines = []
        for r in rows[:25]:
            rat = rats.get_rat(r["rat_key"])
            if not rat:
                continue
            emoji = rats.RARITY_EMOJI.get(rat["rarity"], "🐀")
            lines.append(f"{emoji} **{rat['name']}** ×{r['count']}")
        embed = discord.Embed(
            title=f"🎒 {interaction.user.display_name}'s Inventory", description="\n".join(lines), color=0x3498DB
        )
        await interaction.followup.send(embed=embed)

    @app_commands.command(description="View your Mushak collection progress")
    async def collection(self, interaction: discord.Interaction) -> None:
        assert interaction.guild is not None
        await interaction.response.defer()
        pool = db._get_pool()
        rows = await pool.fetch(
            "SELECT rat_key FROM user_rats WHERE user_id=$1 AND guild_id=$2 AND count>0",
            interaction.user.id,
            interaction.guild.id,
        )
        owned = {r["rat_key"] for r in rows}

        lines = []
        for rarity in rats.RARITY_ORDER:
            species = [r for r in rats.RATS.values() if r["rarity"] == rarity]
            if not species:
                continue
            have = sum(1 for r in species if r["id"] in owned)
            emoji = rats.RARITY_EMOJI.get(rarity, "")
            lines.append(f"{emoji} {rarity.title():<10} {have}/{len(species)}")

        embed = discord.Embed(
            title=f"📖 {interaction.user.display_name}'s Collection",
            description=f"Discovered: **{len(owned)} / {len(rats.RATS)}**\n\n" + "\n".join(f"`{line}`" for line in lines),
            color=0x9B59B6,
        )
        await interaction.followup.send(embed=embed)

    @app_commands.command(description="Browse every known Mushak species, grouped by category")
    async def dex(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        by_category: dict[str, list[dict]] = {}
        for rat in rats.RATS.values():
            by_category.setdefault(rat.get("category", "other"), []).append(rat)

        embed = discord.Embed(
            title="📖 Mushak Species Dex",
            description=f"{len(rats.RATS)} known species across {len(by_category)} categories",
            color=0x9B59B6,
        )
        for category, species in sorted(by_category.items()):
            species.sort(key=lambda r: rats.rarity_rank(r["rarity"]))
            lines = [f"{rats.RARITY_EMOJI.get(r['rarity'], '')} **{r['name']}** ({r['rarity'].title()})" for r in species]
            embed.add_field(name=f"{category.title()} ({len(species)})", value="\n".join(lines), inline=False)
        await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Profile(bot))
