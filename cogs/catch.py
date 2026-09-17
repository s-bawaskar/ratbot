import logging
import random
from datetime import datetime, timedelta, timezone

import discord
from discord import app_commands
from discord.ext import commands, tasks

import config
import db
import permissions
import rats
from achievements_engine import check_achievements
from database import Channel, Guild
from economy import add_modaks

CATCH_TEMPLATES = [
    "{mention} snatched up **{name}**!",
    "{mention} caught **{name}**!",
    "{mention} got their paws on **{name}**!",
    "{mention} nabbed **{name}**!",
    "{mention} scooped up **{name}**!",
]


def _random_delay(min_s: int, max_s: int) -> datetime:
    return datetime.now(timezone.utc) + timedelta(seconds=random.randint(min_s, max_s))


def _fmt_catch_time(seconds: float) -> str:
    minutes = int(seconds // 60)
    secs = seconds % 60
    if minutes > 0:
        return f"{minutes} minute{'s' if minutes != 1 else ''} {secs:.1f} seconds"
    return f"{secs:.1f} seconds"


class Catch(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.spawning: set[int] = set()
        # channels with a currently-active spawn, mirrored from the DB so on_message doesn't
        # need a query per chat message just to check this
        self.active_spawn_channels: set[int] = set()
        self.spawn_loop.start()

    async def cog_load(self) -> None:
        rows = await db._get_pool().fetch("SELECT channel_id FROM channels WHERE current_spawn_msg_id IS NOT NULL")
        self.active_spawn_channels = {row["channel_id"] for row in rows}

    def cog_unload(self) -> None:
        self.spawn_loop.cancel()

    @app_commands.command(description="(ADMIN) Set up Mushak spawning in this channel")
    @permissions.admin_or_owner()
    async def setup(self, interaction: discord.Interaction) -> None:
        assert interaction.guild is not None and interaction.channel_id is not None
        await interaction.response.defer()
        await Guild.get_or_create(guild_id=interaction.guild.id, defaults={"name": interaction.guild.name})
        existing = await Channel.get_or_none(channel_id=interaction.channel_id)
        if existing:
            await interaction.followup.send("This channel is already set up for spawns.", ephemeral=True)
            return
        await Channel.create(
            channel_id=interaction.channel_id,
            guild_id=interaction.guild.id,
            enabled=True,
            spawn_min_s=600,
            spawn_max_s=3600,
            next_spawn_at=_random_delay(60, 300),
        )
        await interaction.followup.send(f"Mushaks will now spawn here! Type `{config.CATCH_TRIGGER_WORD}` to catch one.")

    @app_commands.command(description="(ADMIN) Stop Mushak spawning in this channel")
    @permissions.admin_or_owner()
    async def unsetup(self, interaction: discord.Interaction) -> None:
        assert interaction.channel_id is not None
        await interaction.response.defer()
        channel = await Channel.get_or_none(channel_id=interaction.channel_id)
        if not channel:
            await interaction.followup.send("This channel isn't set up.", ephemeral=True)
            return
        await channel.delete()
        self.active_spawn_channels.discard(interaction.channel_id)
        await interaction.followup.send("Spawning stopped in this channel.")

    @app_commands.command(description="(ADMIN) Force a Mushak to spawn immediately in this channel")
    @app_commands.describe(
        rarity="Optional: force a specific rarity tier (ignored if `rat` is also given)",
        rat="Optional: force a specific Mushak species",
    )
    @app_commands.choices(rarity=[app_commands.Choice(name=r.title(), value=r) for r in rats.RARITY_ORDER])
    @permissions.admin_or_owner()
    async def forcespawn(self, interaction: discord.Interaction, rarity: str | None = None, rat: str | None = None) -> None:
        assert interaction.channel_id is not None
        await interaction.response.defer(ephemeral=True)
        channel = await Channel.get_or_none(channel_id=interaction.channel_id)
        if not channel:
            await interaction.followup.send("This channel isn't set up. Run `/setup` first.", ephemeral=True)
            return
        if channel.current_spawn_msg_id:
            await interaction.followup.send("A Mushak is already spawned here.", ephemeral=True)
            return

        forced_rat = None
        if rat:
            forced_rat = rats.get_rat(rat)
            if forced_rat is None:
                await interaction.followup.send("Unknown Mushak.", ephemeral=True)
                return
        elif rarity:
            forced_rat = rats.weighted_spawn(rarity=rarity)

        await interaction.followup.send("Forcing a spawn...", ephemeral=True)
        await self._spawn(interaction.channel_id, channel.spawn_min_s, channel.spawn_max_s, forced_rat=forced_rat)

    @forcespawn.autocomplete("rat")
    async def forcespawn_rat_autocomplete(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        return await rats.autocomplete(interaction, current)

    @app_commands.command(description="(ADMIN) Change how often Mushaks spawn in this channel, in seconds")
    @app_commands.describe(min_seconds="Minimum seconds between spawns", max_seconds="Maximum seconds between spawns")
    @permissions.admin_or_owner()
    async def changetimings(
        self,
        interaction: discord.Interaction,
        min_seconds: app_commands.Range[int, 10, 86400],
        max_seconds: app_commands.Range[int, 10, 86400],
    ) -> None:
        assert interaction.channel_id is not None
        await interaction.response.defer()
        if min_seconds > max_seconds:
            await interaction.followup.send("Minimum can't be greater than maximum.", ephemeral=True)
            return
        channel = await Channel.get_or_none(channel_id=interaction.channel_id)
        if not channel:
            await interaction.followup.send("This channel isn't set up. Run `/setup` first.", ephemeral=True)
            return
        channel.spawn_min_s = min_seconds
        channel.spawn_max_s = max_seconds
        if not channel.current_spawn_msg_id:
            # reschedule the next spawn under the new timing immediately, instead of waiting
            # for whatever delay was already queued up under the old min/max
            channel.next_spawn_at = _random_delay(min_seconds, max_seconds)
        await channel.save()
        await interaction.followup.send(f"Mushaks will now spawn every {min_seconds}-{max_seconds} seconds here.")

    @tasks.loop(seconds=15)
    async def spawn_loop(self) -> None:
        pool = db._get_pool()
        rows = await pool.fetch(
            "SELECT channel_id, spawn_min_s, spawn_max_s FROM channels "
            "WHERE enabled AND current_spawn_msg_id IS NULL AND next_spawn_at <= now()"
        )
        log = logging.getLogger("ratbot")
        for row in rows:
            channel_id = row["channel_id"]
            if channel_id in self.spawning:
                continue
            self.spawning.add(channel_id)
            try:
                await self._spawn(channel_id, row["spawn_min_s"], row["spawn_max_s"])
            except Exception:
                # never let one bad channel (deleted, forbidden, etc.) kill the whole loop
                log.exception("spawn failed for channel %s", channel_id)
            finally:
                self.spawning.discard(channel_id)

    @spawn_loop.before_loop
    async def before_spawn_loop(self) -> None:
        await self.bot.wait_until_ready()

    async def _spawn(self, channel_id: int, min_s: int, max_s: int, forced_rat: dict | None = None) -> None:
        log = logging.getLogger("ratbot")
        try:
            channel = self.bot.get_channel(channel_id) or await self.bot.fetch_channel(channel_id)
        except (discord.NotFound, discord.Forbidden):
            log.warning("channel %s no longer accessible, removing its spawn config", channel_id)
            await db._get_pool().execute("DELETE FROM channels WHERE channel_id = $1", channel_id)
            self.active_spawn_channels.discard(channel_id)
            return
        rat = forced_rat or rats.weighted_spawn()
        log.info("spawning: channel=%s rat_id=%r rat_name=%r", channel_id, rat.get("id"), rat.get("name"))
        emoji = rats.RARITY_EMOJI.get(rat["rarity"], "🐀")
        content = f"{emoji} A wild **{rat['name']}** has appeared!\n{rat['rarity'].title()} — Type `{config.CATCH_TRIGGER_WORD}` to catch it!"
        image_path = rats.get_image_path(rat["id"])
        file = discord.File(image_path, filename=f"{rat['id']}{image_path.suffix}") if image_path else None
        try:
            msg = await channel.send(content, file=file) if file else await channel.send(content)  # type: ignore[union-attr]
        except discord.HTTPException:
            return
        pool = db._get_pool()
        spawned_at = datetime.now(timezone.utc)
        await pool.execute(
            "UPDATE channels SET current_spawn_msg_id = $1, current_rat_key = $2, current_spawn_at = $3, next_spawn_at = $4 WHERE channel_id = $5",
            msg.id,
            rat["id"],
            spawned_at,
            _random_delay(min_s, max_s),
            channel_id,
        )
        self.active_spawn_channels.add(channel_id)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot or message.guild is None:
            return

        log = logging.getLogger("ratbot")
        content = message.content.strip().lower()

        if content != config.CATCH_TRIGGER_WORD:
            if not content or message.channel.id not in self.active_spawn_channels:
                return
            try:
                if content == "cat":
                    await message.reply("😹 You thought it was me huh?", mention_author=False)
                else:
                    await message.add_reaction("😂")
            except discord.HTTPException:
                pass
            except Exception:
                log.exception("wrong-guess reaction failed")
            return

        try:
            pool = db._get_pool()
            row = await pool.fetchrow(
                "WITH claimed AS ("
                "  SELECT channel_id, current_rat_key, current_spawn_msg_id, current_spawn_at FROM channels "
                "  WHERE channel_id = $1 AND current_spawn_msg_id IS NOT NULL "
                "  FOR UPDATE"
                ") "
                "UPDATE channels SET current_spawn_msg_id = NULL, current_rat_key = NULL, current_spawn_at = NULL "
                "FROM claimed WHERE channels.channel_id = claimed.channel_id "
                "RETURNING claimed.current_rat_key, claimed.current_spawn_msg_id, claimed.current_spawn_at",
                message.channel.id,
            )
            self.active_spawn_channels.discard(message.channel.id)
            if row is None:
                # either no spawn is active, or someone else already claimed it a moment earlier
                try:
                    await message.add_reaction("😂")
                except discord.HTTPException:
                    pass
                return

            rat_key = row["current_rat_key"]
            spawn_msg_id = row["current_spawn_msg_id"]
            rat = rats.get_rat(rat_key)
            if rat is None:
                log.warning("catch: rat_key %r not found in rats.RATS", rat_key)
                if spawn_msg_id:
                    try:
                        await message.channel.get_partial_message(spawn_msg_id).delete()
                    except discord.HTTPException:
                        pass
                    await message.channel.send("🐀 That Mushak vanished into thin air. Weird.")
                return

            spawn_at = row["current_spawn_at"]
            catch_seconds = max(0.0, (datetime.now(timezone.utc) - spawn_at).total_seconds()) if spawn_at else 0.0

            # remove the original spawn message so the catch announcement replaces it
            if spawn_msg_id:
                try:
                    await message.channel.get_partial_message(spawn_msg_id).delete()
                except discord.HTTPException:
                    pass

            user_id, guild_id = message.author.id, message.guild.id
            new_count = await pool.fetchval(
                "INSERT INTO user_rats (user_id, guild_id, rat_key, count) VALUES ($1, $2, $3, 1) "
                "ON CONFLICT (user_id, guild_id, rat_key) DO UPDATE SET count = user_rats.count + 1 "
                "RETURNING count",
                user_id,
                guild_id,
                rat_key,
            )
            await pool.execute(
                "INSERT INTO catches (user_id, guild_id, rat_key, catch_seconds) VALUES ($1, $2, $3, $4)",
                user_id,
                guild_id,
                rat_key,
                catch_seconds,
            )
            reward = max(1, int(rat["sell_value"] * config.CATCH_REWARD_RATIO))
            await add_modaks(user_id, guild_id, reward, f"catch:{rat_key}")

            emoji = rats.RARITY_EMOJI.get(rat["rarity"], "🐀")
            template = random.choice(CATCH_TEMPLATES).format(mention=message.author.mention, name=rat["name"])
            plural = "s" if new_count != 1 else ""
            content = (
                f"{emoji} {template}\n"
                f"You now have **{new_count}** {rat['name']}{plural}.\n"
                f"Caught in {_fmt_catch_time(catch_seconds)}. (+{reward} 🍥 Modaks)"
            )
            await message.channel.send(content)

            unlocked = await check_achievements(user_id, guild_id, caught_rarity=rat["rarity"], catch_seconds=catch_seconds)
            for ach in unlocked:
                await message.channel.send(f"🏆 {message.author.mention} unlocked achievement **{ach['name']}**!")
        except Exception:
            log.exception("catch handler failed")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Catch(bot))
