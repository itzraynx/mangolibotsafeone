"""
═══════════════════════════════════════════════════════════════════════════════
MODERATION — Mangoli Bot
Message cleanup & moderation utilities.
by Nokiatis Community
═══════════════════════════════════════════════════════════════════════════════

Commands:
  • /purgeuser  — delete a user's messages (whole server or last N hours)
  • /purge      — bulk delete messages in a channel

Discord limits: bulk-delete only works for messages younger than 14 days.
Older messages are deleted one-by-one (best effort).
"""

import asyncio
from datetime import datetime, timedelta, timezone

import discord
from discord import app_commands

BRAND = "Mangoli Bot"
ICON = "https://i.imgur.com/7ZGzqjY.png"
FOOTER = f"⚡ {BRAND} • by Nokiatis Community"
PRIMARY = 0x5865F2
SUCCESS = 0x57F287
ERROR = 0xED4245
WARNING = 0xFEE75C


def _chunk(lst, size=100):
    for i in range(0, len(lst), size):
        yield lst[i:i + size]


async def _delete_messages(channel, messages):
    """Delete a list of messages: bulk for <14d, individual for older."""
    deleted = 0
    now = datetime.now(timezone.utc)
    bulk = []
    for m in messages:
        if m.pinned:
            continue
        age = now - m.created_at
        if age < timedelta(days=14):
            bulk.append(m)
        else:
            try:
                await m.delete()
                deleted += 1
            except Exception:
                pass
            await asyncio.sleep(0.4)  # be gentle with rate limits
    for chunk in _chunk(bulk, 100):
        try:
            await channel.delete_messages(chunk)
            deleted += len(chunk)
        except Exception:
            # fall back to individual
            for m in chunk:
                try:
                    await m.delete()
                    deleted += 1
                except Exception:
                    pass
                await asyncio.sleep(0.3)
    return deleted


async def purge_user_messages(bot, guild, member, cutoff=None, channel=None, limit=2000):
    """Delete a member's messages. Returns total deleted."""
    deleted = 0
    channels = [channel] if channel else guild.text_channels
    for ch in channels:
        if not ch.permissions_for(guild.me).read_message_history:
            continue
        if not ch.permissions_for(guild.me).manage_messages:
            continue
        try:
            kwargs = {"limit": limit}
            if cutoff:
                kwargs["after"] = cutoff
            messages = [m async for m in ch.history(**kwargs)]
            mine = [m for m in messages if m.author.id == member.id]
            if mine:
                deleted += await _delete_messages(ch, mine)
        except Exception as e:
            print(f"[Moderation] purge error in #{ch}: {e}")
    return deleted


def register(bot):
    """Register moderation commands."""

    @bot.tree.command(name="purgeuser", description="🗑️ Delete a user's messages (server-wide or recent)")
    @app_commands.describe(
        member="The user whose messages to delete",
        hours="Only delete messages from the last N hours (empty = all)",
        channel="Only in one channel (empty = whole server)",
    )
    @app_commands.default_permissions(manage_messages=True)
    async def purgeuser(
        interaction: discord.Interaction,
        member: discord.Member,
        hours: int = None,
        channel: discord.TextChannel = None,
    ):
        if hours is not None and hours <= 0:
            await interaction.response.send_message("❌ Hours must be positive.", ephemeral=True)
            return

        scope = f"the last **{hours}h**" if hours else "**all time**"
        area = f"in {channel.mention}" if channel else "**across the whole server**"
        await interaction.response.defer()

        cutoff = None
        if hours:
            cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

        deleted = await purge_user_messages(bot, interaction.guild, member, cutoff=cutoff, channel=channel)

        embed = discord.Embed(
            description=(
                f"# 🗑️ Message Purge\n"
                f"### Deleted `{deleted}` message{'s' if deleted != 1 else ''}\n\n"
                f"**User:** {member.mention}\n"
                f"**Scope:** {scope}\n"
                f"**Area:** {area}"
            ),
            color=SUCCESS if deleted > 0 else WARNING,
        )
        embed.set_footer(text=FOOTER, icon_url=ICON)
        await interaction.followup.send(embed=embed)

    @bot.tree.command(name="purge", description="🧹 Bulk delete messages in this channel")
    @app_commands.describe(
        amount="Number of messages to delete (1-300)",
        user="Only delete this user's messages (optional)",
    )
    @app_commands.default_permissions(manage_messages=True)
    async def purge(
        interaction: discord.Interaction,
        amount: int,
        user: discord.Member = None,
    ):
        if amount < 1 or amount > 300:
            await interaction.response.send_message("❌ Amount must be between 1 and 300.", ephemeral=True)
            return
        await interaction.response.defer()

        def check(m):
            if user:
                return m.author.id == user.id
            return True

        deleted = len(await interaction.channel.purge(limit=amount, check=check))

        embed = discord.Embed(
            description=f"# 🧹 Purged\n### Deleted `{deleted}` message{'s' if deleted != 1 else ''} in {interaction.channel.mention}",
            color=SUCCESS,
        )
        embed.set_footer(text=FOOTER, icon_url=ICON)
        await interaction.followup.send(embed=embed, ephemeral=True)

    print("[Moderation] Moderation module loaded")
