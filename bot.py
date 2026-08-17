"""
╔════════════════════════════════════════════════════════════════════════════════════╗
║     ███╗   ██╗ ██████╗ ██╗  ██╗██╗ █████╗ ████████╗██╗███████╗                     ║
║     ████╗  ██║██╔═══██╗██║ ██╔╝██║██╔══██╗╚══██╔══╝██║██╔════╝                     ║
║     ██╔██╗ ██║██║   ██║█████╔╝ ██║███████║   ██║   ██║███████╗                     ║
║     ██║╚██╗██║██║   ██║██╔═██╗ ██║██╔══██║   ██║   ██║╚════██║                     ║
║     ██║ ╚████║╚██████╔╝██║  ██╗██║██║  ██║   ██║   ██║███████║                     ║
║     ╚═╝  ╚═══╝ ╚═════╝ ╚═╝  ╚═╝╚═╝╚═╝  ╚═╝   ╚═╝   ╚═╝╚══════╝                     ║
║                                                                                     ║
║            ██████╗ ██████╗ ████████╗                                               ║
║            ██╔══██╗██╔═══██╗╚══██╔══╝                                               ║
║            ██████╔╝██║   ██║   ██║                                                  ║
║            ██╔══██╗██║   ██║   ██║                                                  ║
║            ██████╔╝╚██████╔╝   ██║                                                  ║
║            ╚═════╝  ╚═════╝    ╚═╝                                                  ║
║                                                                                     ║
║   ⚡ NOKIATIS COMMUNITY - NOVAGEN CLOUD SERVICES ⚡                                      ║
║   🤖 Multi-Feature Discord Bot 🤖                                       ║
║                                                                                     ║
╚════════════════════════════════════════════════════════════════════════════════════╝

General-Purpose Discord Bot with AI Chat & Utility Features
Features:
- Asynchronous processing with thread executor
- Beautiful Discord Embeds with status colors
- Slash Commands (app_commands)
- Robust error handling
- Rate limiting protection
- Queue system for batch processing
"""

import discord
from discord import app_commands
from discord.ext import commands
import asyncio
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
from typing import Optional
import logging
import random
import time
import sys
import shutil
# Control bridge for the web dashboard (logs, voice control, settings)
import control_bridge

# Level system (XP, ranks, invites, leaderboards)
import level_system

# Economy system (coins, gambling, shop, boosters)
import economy_system

# MiMoAI for AI-powered responses
from mimo_ai import MiMoAI

# Configure logging FIRST (before imports that might fail)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger('MangoliBot')

# Forward log records to the dashboard control bridge (for the Logs page).
class _BridgeLogHandler(logging.Handler):
    def emit(self, record):
        try:
            control_bridge.add_log(record.levelname, self.format(record))
        except Exception:
            pass

_bridge_handler = _BridgeLogHandler()
_bridge_handler.setFormatter(logging.Formatter('%(message)s'))
_bridge_handler.setLevel(logging.INFO)
logger.addHandler(_bridge_handler)

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION - EDIT THESE VARIABLES DIRECTLY
# ═══════════════════════════════════════════════════════════════════════════════

# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║                           ⚠️ IMPORTANT CONFIG ⚠️                              ║
# ║           Edit these values directly - DO NOT use .env file                  ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

# Discord Bot Token - Your bot token from Discord Developer Portal
TOKEN = "MTQxNjUxNDgxMDI0MTA4OTYzOQ.GUN1Mb.0U015pGcLjL5OPH0MkscSts02Tjw95wfTM4618"

# Xiaomi MiMo API Configuration
MIMO_API_KEY = "sk-s23ziwpuvbacymffhb4fehsfy66dtoc7z4oxxwp7kscipy9y"

# Channel ID where AI will respond to messages
AI_CHANNEL_ID = 1464054036603863072

# Thread pool for running synchronous tasks
MAX_WORKERS = 50  # 50 parallel workers for ultra-fast checking
executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)

# ═══════════════════════════════════════════════════════════════════════════════
# EMBED FACTORY - Premium Production-Ready Embed System
# ═══════════════════════════════════════════════════════════════════════════════

class EmbedFactory:
    """
    Centralized embed creation for consistent premium styling.
    All embeds created through this factory have standardized:
    - Color palette (Modern Dark aesthetic)
    - Footer with branding
    - Timestamp
    - Professional formatting
    """
    
    # Modern Dark Color Palette
    PRIMARY = 0x5865F2    # Blurple - Info/Default
    SUCCESS = 0x57F287    # Green - Valid/Success
    ERROR = 0xED4245      # Red - Error/Invalid
    WARNING = 0xFEE75C    # Yellow - Warning/2FA
    PREMIUM = 0x9B59B6    # Purple - Premium
    CHECKING = 0x3498DB   # Blue - Loading/Checking
    GOLD = 0xFBBF24       # Gold - Rewards/Level-ups/Achievements
    MINECRAFT = 0x5D8731  # MC Green - Minecraft
    GAMEPASS = 0x107C10   # Xbox Green - GamePass
    
    # Branding
    BOT_NAME = "MangoliBot"
    FOOTER_TEXT = "⚡ MangoliBot • by Nokiatis Community"
    BOT_ICON = "https://i.imgur.com/7ZGzqjY.png"
    
    @staticmethod
    def _base_embed(title: str, description: str, color: int) -> discord.Embed:
        """Create base embed with standard premium formatting."""
        embed = discord.Embed(
            title=title,
            description=description,
            color=color,
            timestamp=datetime.now(timezone.utc)
        )
        embed.set_footer(text=EmbedFactory.FOOTER_TEXT, icon_url=EmbedFactory.BOT_ICON)
        return embed
    
    @staticmethod
    def gold(title: str, description: str = "") -> discord.Embed:
        """🏆 Gold embed for rewards, level-ups & achievements."""
        return EmbedFactory._base_embed(f"🏆 {title}", description, EmbedFactory.GOLD)
    
    @staticmethod
    def info(title: str, description: str = "") -> discord.Embed:
        """📘 Blue info embed for general information."""
        return EmbedFactory._base_embed(f"ℹ️ {title}", description, EmbedFactory.PRIMARY)
    
    @staticmethod
    def success(title: str, description: str = "") -> discord.Embed:
        """✅ Green success embed for valid/successful operations."""
        return EmbedFactory._base_embed(f"✅ {title}", description, EmbedFactory.SUCCESS)
    
    @staticmethod
    def error(title: str, description: str = "") -> discord.Embed:
        """❌ Red error embed for errors/invalid results."""
        return EmbedFactory._base_embed(f"❌ {title}", description, EmbedFactory.ERROR)
    
    @staticmethod
    def warning(title: str, description: str = "") -> discord.Embed:
        """⚠️ Yellow warning embed for warnings/2FA."""
        return EmbedFactory._base_embed(f"⚠️ {title}", description, EmbedFactory.WARNING)
    
    @staticmethod
    def premium(title: str, description: str = "") -> discord.Embed:
        """💎 Purple premium embed for premium content."""
        return EmbedFactory._base_embed(f"💎 {title}", description, EmbedFactory.PREMIUM)
    
    @staticmethod
    def loading(title: str, description: str = "") -> discord.Embed:
        """⏳ Blue loading embed for processing states."""
        return EmbedFactory._base_embed(f"⏳ {title}", description, EmbedFactory.CHECKING)
    
    @staticmethod
    def minecraft(title: str, description: str = "") -> discord.Embed:
        """⛏️ Green Minecraft themed embed."""
        return EmbedFactory._base_embed(f"⛏️ {title}", description, EmbedFactory.MINECRAFT)
    
    @staticmethod
    def gamepass(title: str, description: str = "") -> discord.Embed:
        """🎮 Xbox themed embed for GamePass."""
        return EmbedFactory._base_embed(f"🎮 {title}", description, EmbedFactory.GAMEPASS)
    
    @staticmethod
    def custom(title: str, description: str = "", color: int = PRIMARY, emoji: str = "") -> discord.Embed:
        """Custom embed with specified color and optional emoji."""
        display_title = f"{emoji} {title}" if emoji else title
        return EmbedFactory._base_embed(display_title, description, color)


# Legacy compatibility - keep old class for existing code
class EmbedColors:
    SUCCESS = EmbedFactory.SUCCESS
    ERROR = EmbedFactory.ERROR
    WARNING = EmbedFactory.WARNING
    INFO = EmbedFactory.PRIMARY
    PREMIUM = EmbedFactory.PREMIUM
    GOLD = EmbedFactory.GOLD
    BANNED = 0x8B0000

# ═══════════════════════════════════════════════════════════════════════════════
# CHANNEL CONFIGURATION - Edit these channel IDs for your server
# ═══════════════════════════════════════════════════════════════════════════════

# LOGS CHANNEL - all important logs go here (no spam)
LOGS_CHANNEL = 1463665248606359562

# Emojis for visual appeal
class Emojis:
    LOADING = "⏳"
    SUCCESS = "✅"
    ERROR = "❌"
    WARNING = "⚠️"
    MINECRAFT = "⛏️"
    CAPE = "🧥"
    STAR = "⭐"
    BAN = "🔨"
    UNBAN = "🟢"
    LEVEL = "📊"
    RANK = "👑"
    INFO = "ℹ️"
    GAMEPASS = "🎮"
    ULTIMATE = "💎"
    MAIL = "📧"
    HYPIXEL = "🔶"
    COIN = "💰"
    TROPHY = "🏆"
    FIRE = "🔥"
    INVITE = "📨"
    DAILY = "🎁"

# ═══════════════════════════════════════════════════════════════════════════════
# BOT SETUP
# ═══════════════════════════════════════════════════════════════════════════════

class MangoliBot(commands.Bot):
    """Custom bot class with enhanced functionality."""
    
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        
        super().__init__(
            command_prefix="!",
            intents=intents,
            help_command=None
        )
        self.start_time = datetime.now(timezone.utc)
        self.log_queue = []  # Queue to batch logs
        self.last_log_time = 0  # Track last log to prevent spam
        
    async def setup_hook(self):
        """Setup hook called when bot is ready to sync commands."""
        try:
            synced = await self.tree.sync()
            logger.info(f"Synced {len(synced)} command(s)")
        except Exception as e:
            logger.error(f"Failed to sync commands: {e}")
    
    async def on_ready(self):
        """Event triggered when bot is fully ready."""
        logger.info(f"{'═' * 60}")
        logger.info("Bot is online and ready!")
        logger.info(f"Logged in as: {self.user.name}#{self.user.discriminator}")
        logger.info(f"Bot ID: {self.user.id}")
        logger.info(f"Servers: {len(self.guilds)}")
        logger.info(f"{'═' * 60}")
        logger.info("📊 DASHBOARD: http://localhost:5000")
        logger.info(f"{'═' * 60}")
        
        # Set Rich Presence from dashboard settings
        try:
            _cfg = control_bridge.get_settings()
            st = _cfg.get("presence_status", "online")
            atype = _cfg.get("presence_activity_type", "streaming")
            text = _cfg.get("presence_text", "Nokiatis Community 🎮")
            url = _cfg.get("presence_stream_url", "https://twitch.tv/nokiatis")
            _status_map = {
                "online": discord.Status.online,
                "idle": discord.Status.idle,
                "dnd": discord.Status.dnd,
                "invisible": discord.Status.invisible,
            }
            if atype == "streaming":
                _activity = discord.Streaming(name=text or "Twitch", url=url or "https://twitch.tv/")
            else:
                _atype_map = {
                    "playing": discord.ActivityType.playing,
                    "watching": discord.ActivityType.watching,
                    "listening": discord.ActivityType.listening,
                    "competing": discord.ActivityType.competing,
                }
                _activity = discord.Activity(type=_atype_map.get(atype, discord.ActivityType.playing), name=text or "")
            await self.change_presence(status=_status_map.get(st, discord.Status.online), activity=_activity)
        except Exception as e:
            logger.warning(f"Could not apply presence: {e}")
        
        # Send startup log to logs channel
        await send_log("🟢 **BOT ONLINE**", f"Bot started successfully!\n• Name: `{self.user.name}`\n• Servers: `{len(self.guilds)}`\n• Commands synced\n• Dashboard: `http://localhost:5000`", "success")
        
        # Register with the dashboard control bridge
        try:
            control_bridge.set_bot(
                self,
                voice_state={
                    "clients": voice_clients,
                    "tasks": voice_tasks,
                    "enabled": voice_enabled,
                    "paused": voice_paused,
                },
                sounds=GAME_SOUNDS,
                sound_loop=play_random_game_sounds,
                api_key=MIMO_API_KEY,
            )
            logger.info("Dashboard control bridge registered")
        except Exception as e:
            logger.warning(f"Dashboard bridge not available: {e}")

        # ── Level system: start voice XP loop + cache invites ─────────
        try:
            if not hasattr(self, "_voice_xp_task") or self._voice_xp_task is None:
                self._voice_xp_task = self.loop.create_task(voice_xp_loop())
                logger.info("Voice XP loop started")
            for guild in self.guilds:
                try:
                    invites = await guild.invites()
                    level_system.cache_invites(guild.id, invites)
                except Exception:
                    pass  # needs manage_guild permission
        except Exception as e:
            logger.warning(f"Level system init error: {e}")

    async def on_message(self, message: discord.Message):
        """Handle incoming messages and respond in AI channel."""
        # Ignore messages from bots
        if message.author.bot:
            return

        # ── Level system: grant chat XP (with cooldown + min length) ──
        if message.guild is not None and not message.content.startswith(('!', '/')):
            try:
                cfg = level_system.get_settings(message.guild.id)
                min_len = cfg.get("message_min_length", 3)
                if len(message.content.strip()) >= min_len and \
                   level_system.message_xp_allowed(message.guild.id, message.author.id):
                    amount = random.randint(
                        cfg.get("message_xp_min", 15),
                        cfg.get("message_xp_max", 25),
                    )
                    await grant_xp(message.guild, message.author, amount, "message")
            except Exception as e:
                logger.error(f"Message XP error: {e}")

        # Check if message is in the AI channel (configurable from dashboard)
        try:
            _cfg = control_bridge.get_settings()
            _ai_enabled = _cfg.get("ai_enabled", True)
            _ai_channel = int(_cfg.get("ai_channel_id") or AI_CHANNEL_ID)
            _personality = _cfg.get("ai_personality") or "default"
            _custom_persona = _cfg.get("ai_custom_persona") or ""
        except Exception:
            _ai_enabled = True
            _ai_channel = AI_CHANNEL_ID
            _personality = "default"
            _custom_persona = ""

        if not _ai_enabled:
            return

        if message.channel.id == _ai_channel:
            # Skip if it's a command (starts with ! or /)
            if message.content.startswith(('!', '/')):
                return

            try:
                # Show typing indicator
                async with message.channel.typing():
                    # Generate AI response with user memory
                    async with MiMoAI(MIMO_API_KEY) as ai:
                        ai.set_personality(_personality)
                        if _custom_persona:
                            ai.set_custom_persona(_custom_persona)
                        response = await ai.generate_response(message.content, user_id=str(message.author.id))

                        if response:
                            # Send response as plain text
                            await message.reply(response)
                        else:
                            await message.reply("❌ Sorry, I couldn't generate a response. Please try again.")

            except Exception as e:
                logger.error(f"Error generating AI response: {e}")
                await message.reply("❌ An error occurred while processing your request.")

# Initialize bot
bot = MangoliBot()


@bot.event
async def on_app_command_completion(interaction: discord.Interaction, command: discord.app_commands.Command):
    """Track command usage for the dashboard."""
    try:
        control_bridge.increment_command(command.name)
    except Exception:
        pass


# ═══════════════════════════════════════════════════════════════════════════════
# LEVEL SYSTEM — helpers, events & commands
# ═══════════════════════════════════════════════════════════════════════════════

LEVELUP_CHANNEL = 1538702988821139547


def levelup_channel_for(guild_id):
    try:
        return level_system.get_settings(guild_id).get("level_up_channel", LEVELUP_CHANNEL)
    except Exception:
        return LEVELUP_CHANNEL


def _progress_bar(cur, need, width=18):
    filled = int(width * (cur / need)) if need else width
    return "".join("█" if i < filled else "░" for i in range(width))


def build_rank_embed(member, stats, rank=None, balance=None):
    """A premium rank card embed."""
    level = stats["level"]
    bar = _progress_bar(stats["xp_into_level"], stats["xp_needed"])
    emoji = level_system.level_emoji(level)
    embed = discord.Embed(
        title=f"{emoji} {member.display_name}",
        description=f"**Level {level}**  ·  `{stats['xp']:,}` XP total",
        color=EmbedFactory.PREMIUM,
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(
        name="📈 Progress to next level",
        value=f"`{bar}`\n`{stats['xp_into_level']:,}` / `{stats['xp_needed']:,}` XP ({stats['progress']}%)",
        inline=False,
    )
    if rank:
        embed.add_field(name="👑 Rank", value=f"`#{rank}`", inline=True)
    if balance is not None:
        embed.add_field(name="💰 Coins", value=f"`{balance:,}`", inline=True)
    embed.add_field(name="💬 Messages", value=f"`{stats['messages']}`", inline=True)
    embed.add_field(name="🎙️ Voice (min)", value=f"`{stats['voice_minutes']}`", inline=True)
    embed.add_field(name="📨 Invites", value=f"`{stats['invites']}`", inline=True)
    embed.add_field(name="🔥 Streak", value=f"`{stats.get('streak', 0)} days`", inline=True)
    embed.add_field(name="📅 Weekly XP", value=f"`{stats.get('weekly_xp', 0):,}`", inline=True)
    ach = stats.get("achievements", [])
    if ach:
        badges = " ".join(a["emoji"] for a in ach)
        embed.add_field(name=f"🏅 Achievements ({len(ach)})", value=badges, inline=False)
    embed.set_footer(text=EmbedFactory.FOOTER_TEXT, icon_url=EmbedFactory.BOT_ICON)
    return embed


async def apply_role_rewards(guild, member, level):
    """Best-effort auto role assignment at reward milestones."""
    try:
        rewards = level_system.get_settings(guild.id).get("role_rewards", {})
        target = rewards.get(str(level))
        if not target:
            return
        role = discord.utils.get(guild.roles, name=target)
        if role and role not in member.roles and role < guild.me.top_role:
            await member.add_roles(role, reason=f"Reached level {level}")
            logger.info(f"Assigned role '{role.name}' to {member} (level {level})")
    except Exception as e:
        logger.warning(f"Role reward error: {e}")


async def announce_level_up(guild, member, stats):
    """Send a celebratory level-up card to the configured channel."""
    try:
        channel = guild.get_channel(levelup_channel_for(guild.id))
        if not channel:
            return
        lv = stats["level"]
        emoji = level_system.level_emoji(lv)
        bar = _progress_bar(stats["xp_into_level"], stats["xp_needed"])
        rank = level_system.get_rank(guild.id, member.id)

        embed = discord.Embed(
            title=f"{emoji} LEVEL UP!",
            description=f"**{member.mention}** reached **Level {lv}**!",
            color=EmbedFactory.GOLD,
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="✨ Total XP", value=f"`{stats['xp']:,}`", inline=True)
        embed.add_field(name="👑 Rank", value=f"`#{rank or '—'}`", inline=True)
        embed.add_field(
            name="📈 Next level",
            value=f"`{bar}`\n`{stats['xp_into_level']:,}` / `{stats['xp_needed']:,}` XP",
            inline=False,
        )
        if stats.get("streak", 0) >= 2:
            embed.add_field(name="🔥 Streak", value=f"`{stats['streak']} days`", inline=True)
        embed.set_footer(text=EmbedFactory.FOOTER_TEXT, icon_url=EmbedFactory.BOT_ICON)
        await channel.send(embed=embed)
    except Exception as e:
        logger.error(f"Level-up announce failed: {e}")


async def grant_xp(guild, member, amount, source="misc"):
    """Add XP (with boost multiplier) and handle level-ups, achievements, coins."""
    # Apply any active XP boost from the economy shop
    try:
        mult, _ = economy_system.get_boost(guild.id, member.id)
        amount = int(amount * mult)
    except Exception:
        mult = 1.0

    result = level_system.add_xp(guild.id, member.id, amount, source)
    old_level, new_level, leveled_up, xp, new_achievements = result

    if leveled_up:
        stats = level_system.get_user_stats(guild.id, member.id)
        await announce_level_up(guild, member, stats)
        await apply_role_rewards(guild, member, new_level)

    # Achievement unlocks
    for aid in new_achievements:
        await announce_achievement(guild, member, aid)

    # Passive coins (piggyback on chat/voice XP)
    try:
        await grant_passive_coins(guild, member, source)
    except Exception:
        pass

    return old_level, new_level, leveled_up


async def announce_achievement(guild, member, aid):
    """Post an achievement unlock to the level-up channel."""
    ach = level_system.ACHIEVEMENTS.get(aid)
    if not ach:
        return
    try:
        channel = guild.get_channel(levelup_channel_for(guild.id))
        if not channel:
            return
        stats = level_system.get_user_stats(guild.id, member.id)
        total = len(stats.get("achievements", [])) if stats else 0
        embed = discord.Embed(
            title=f"{ach['emoji']} Achievement Unlocked!",
            description=f"**{member.mention}** earned **{ach['name']}**!\n> {ach['desc']}",
            color=EmbedFactory.GOLD,
        )
        embed.set_footer(
            text=f"{EmbedFactory.FOOTER_TEXT} • {total} achievement{'s' if total != 1 else ''} unlocked",
            icon_url=EmbedFactory.BOT_ICON,
        )
        await channel.send(embed=embed)
    except Exception as e:
        logger.error(f"Achievement announce failed: {e}")


async def grant_passive_coins(guild, member, source):
    """Small chance to earn coins passively through activity."""
    cfg = economy_system.get_settings(guild.id)
    if source == "message":
        if random.random() < cfg.get("chat_coin_chance", 0.25):
            amount = random.randint(cfg.get("chat_coin_min", 5), cfg.get("chat_coin_max", 15))
            economy_system.add_coins(guild.id, member.id, amount)
    elif source == "voice":
        amount = cfg.get("voice_coins_per_minute", 2)
        economy_system.add_coins(guild.id, member.id, amount)


async def voice_xp_loop():
    """Grant XP every minute to members active in voice channels."""
    await asyncio.sleep(60)
    while True:
        try:
            for guild in bot.guilds:
                cfg = level_system.get_settings(guild.id)
                base = cfg.get("voice_xp_per_minute", 5)
                bonus = cfg.get("voice_bonus_with_others", 3)
                for vc in guild.voice_channels:
                    # Skip members who are self-muted AND self-deafened (AFK/idle)
                    humans = [
                        m for m in vc.members
                        if not m.bot and not (m.voice.self_mute and m.voice.self_deaf)
                    ]
                    for member in humans:
                        with_others = len(humans) > 1
                        amount = base + (bonus if with_others else 0)
                        await grant_xp(guild, member, amount, "voice")
        except Exception as e:
            logger.error(f"Voice XP loop error: {e}")
        await asyncio.sleep(60)


@bot.event
async def on_invite_create(invite: discord.Invite):
    """Cache newly created invites for the tracker."""
    if invite.guild is None:
        return
    try:
        level_system.cache_invites(invite.guild.id, [invite])
    except Exception:
        pass


@bot.event
async def on_member_join(member: discord.Member):
    """Welcome the new member, attribute the invite used, grant inviter XP."""
    guild = member.guild
    inviter = None
    try:
        invites = await guild.invites()
        used = level_system.find_used_invite(guild.id, invites)
        if used and used.inviter and used.inviter.id != member.id:
            inviter = used.inviter
            amount = level_system.get_settings(guild.id).get("invite_xp", 50)
            await grant_xp(guild, inviter, amount, "invite")
            logger.info(f"Invite XP: {inviter} invited {member}")
    except Exception as e:
        logger.warning(f"Invite tracking error: {e}")

    # Welcome message in the level-up/announce channel
    try:
        channel = guild.get_channel(levelup_channel_for(guild.id))
        if channel:
            embed = discord.Embed(
                title="👋 Welcome!",
                description=(
                    f"Hey **{member.mention}**, welcome to **{guild.name}**! 🎉\n\n"
                    f"You're member **#{guild.member_count}**.\n"
                    f"Start chatting, join voice, or invite friends to earn XP and coins! 💬🎙️"
                ),
                color=EmbedFactory.SUCCESS,
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            if inviter:
                embed.add_field(name="🎁 Invited by", value=f"{inviter.mention}", inline=False)
            embed.set_footer(text=EmbedFactory.FOOTER_TEXT, icon_url=EmbedFactory.BOT_ICON)
            await channel.send(embed=embed)
    except Exception as e:
        logger.error(f"Welcome message failed: {e}")


@bot.tree.command(name="rank", description="🏆 View your (or someone's) level & rank card")
@app_commands.describe(member="User to check (defaults to you)")
async def rank_command(interaction: discord.Interaction, member: Optional[discord.Member] = None):
    member = member or interaction.user
    stats = level_system.get_user_stats(interaction.guild_id, member.id)
    if stats is None:
        await interaction.response.send_message(
            "❌ This user has no XP yet — start chatting, join voice, or invite people!", ephemeral=True
        )
        return
    rank = level_system.get_rank(interaction.guild_id, member.id)
    balance = economy_system.get_balance(interaction.guild_id, member.id)
    embed = build_rank_embed(member, stats, rank=rank, balance=balance)
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="leaderboard", description="🏅 Top members by level/XP")
async def leaderboard_command(interaction: discord.Interaction):
    board = level_system.get_leaderboard(interaction.guild_id)
    if not board:
        await interaction.response.send_message("📭 No one has earned XP yet!", ephemeral=True)
        return
    lines = []
    medals = ["🥇", "🥈", "🥉"]
    for i, (uid, s) in enumerate(board[:10]):
        try:
            member = interaction.guild.get_member(int(uid))
            name = member.display_name if member else f"User {uid}"
        except Exception:
            name = f"User {uid}"
        medal = medals[i] if i < 3 else f"`#{i+1}`"
        lines.append(f"{medal} **{name}** — Level `{s['level']}` · `{s['xp']:,}` XP")
    embed = discord.Embed(
        title="🏅 Server Leaderboard",
        description="\n".join(lines),
        color=EmbedFactory.GOLD,
    )
    embed.set_footer(text=EmbedFactory.FOOTER_TEXT, icon_url=EmbedFactory.BOT_ICON)
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="invites", description="📨 See how many people someone invited")
@app_commands.describe(member="User to check (defaults to you)")
async def invites_command(interaction: discord.Interaction, member: Optional[discord.Member] = None):
    member = member or interaction.user
    stats = level_system.get_user_stats(interaction.guild_id, member.id)
    count = stats["invites"] if stats else 0
    embed = discord.Embed(
        title="📨 Invite Count",
        description=f"**{member.display_name}** has invited **{count}** member(s).",
        color=EmbedFactory.CHECKING,
    )
    embed.set_footer(text=EmbedFactory.FOOTER_TEXT, icon_url=EmbedFactory.BOT_ICON)
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="daily", description="🎁 Claim your daily XP + coins bonus")
async def daily_command(interaction: discord.Interaction):
    ok, amount, msg, new_achievements = level_system.daily_claim(interaction.guild_id, interaction.user.id)
    if ok:
        # also grant daily coins
        coin_amount = economy_system.get_settings(interaction.guild_id).get("daily_coins", 150)
        economy_system.add_coins(interaction.guild_id, interaction.user.id, coin_amount)
        stats = level_system.get_user_stats(interaction.guild_id, interaction.user.id)
        embed = discord.Embed(
            title="🎁 Daily Bonus Claimed!",
            description=f"You earned **{amount} XP** and **{coin_amount} coins**!",
            color=EmbedFactory.SUCCESS,
        )
        embed.add_field(name="📈 New total", value=f"`{stats['xp']:,}` XP · Level `{stats['level']}`", inline=False)
        embed.add_field(name="💰 Balance", value=f"`{economy_system.get_balance(interaction.guild_id, interaction.user.id):,}` coins", inline=False)
        if stats.get("streak"):
            embed.add_field(name="🔥 Streak", value=f"`{stats['streak']} days`", inline=True)
        embed.set_footer(text=EmbedFactory.FOOTER_TEXT, icon_url=EmbedFactory.BOT_ICON)
        # announce any streak achievements unlocked by this daily
        for aid in new_achievements:
            await announce_achievement(interaction.guild, interaction.user, aid)
        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message(
            "⏰ You already claimed your daily bonus — come back tomorrow!", ephemeral=True
        )


# ═══════════════════════════════════════════════════════════════════════════════
# ECONOMY COMMANDS
# ═══════════════════════════════════════════════════════════════════════════════

@bot.tree.command(name="balance", description="💰 Check your (or someone's) coin balance")
@app_commands.describe(member="User to check (defaults to you)")
async def balance_command(interaction: discord.Interaction, member: Optional[discord.Member] = None):
    member = member or interaction.user
    bal = economy_system.get_balance(interaction.guild_id, member.id)
    effects = economy_system.active_effects(interaction.guild_id, member.id)
    embed = discord.Embed(
        title="💰 Balance",
        description=f"**{member.display_name}** has **`{bal:,}` coins**.",
        color=EmbedFactory.GOLD,
    )
    if effects:
        embed.add_field(name="⚡ Active effects", value="\n".join(effects), inline=False)
    embed.set_footer(text=EmbedFactory.FOOTER_TEXT, icon_url=EmbedFactory.BOT_ICON)
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="give", description="🎁 Give coins to another member")
@app_commands.describe(member="Recipient", amount="Amount of coins to send")
async def give_command(interaction: discord.Interaction, member: discord.Member, amount: int):
    if amount <= 0:
        await interaction.response.send_message("❌ Amount must be positive.", ephemeral=True)
        return
    ok, msg = economy_system.transfer(interaction.guild_id, interaction.user.id, member.id, amount)
    if ok:
        embed = discord.Embed(
            title="🎁 Coins Sent",
            description=f"**{interaction.user.display_name}** sent **`{amount:,}` coins** to **{member.display_name}**!",
            color=EmbedFactory.SUCCESS,
        )
        embed.set_footer(text=EmbedFactory.FOOTER_TEXT, icon_url=EmbedFactory.BOT_ICON)
        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message(f"❌ {msg}", ephemeral=True)


@bot.tree.command(name="coinflip", description="🪙 Bet coins on heads or tails")
@app_commands.describe(side="heads or tails", bet="Amount to bet")
@app_commands.choices(side=[
    app_commands.Choice(name="Heads", value="heads"),
    app_commands.Choice(name="Tails", value="tails"),
])
@app_commands.checks.cooldown(1, 3.0, key=lambda i: (i.guild_id, i.user.id))
async def coinflip_command(interaction: discord.Interaction, side: str, bet: int):
    ok, won, result, msg = economy_system.coinflip(interaction.guild_id, interaction.user.id, side, bet)
    if not ok:
        await interaction.response.send_message(f"❌ {msg}", ephemeral=True)
        return
    embed = discord.Embed(
        title="🪙 Coin Flip",
        description=msg,
        color=EmbedFactory.SUCCESS if won else EmbedFactory.ERROR,
    )
    embed.add_field(name="💰 Balance", value=f"`{economy_system.get_balance(interaction.guild_id, interaction.user.id):,}` coins")
    embed.set_footer(text=EmbedFactory.FOOTER_TEXT, icon_url=EmbedFactory.BOT_ICON)
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="slots", description="🎰 Spin the slot machine")
@app_commands.describe(bet="Amount to bet")
@app_commands.checks.cooldown(1, 3.0, key=lambda i: (i.guild_id, i.user.id))
async def slots_command(interaction: discord.Interaction, bet: int):
    ok, payout, reels, msg = economy_system.slots(interaction.guild_id, interaction.user.id, bet)
    if not ok:
        await interaction.response.send_message(f"❌ {msg}", ephemeral=True)
        return
    embed = discord.Embed(
        title="🎰 Slot Machine",
        description=msg,
        color=EmbedFactory.SUCCESS if payout > 0 else EmbedFactory.ERROR,
    )
    embed.add_field(name="💰 Balance", value=f"`{economy_system.get_balance(interaction.guild_id, interaction.user.id):,}` coins")
    embed.set_footer(text=EmbedFactory.FOOTER_TEXT, icon_url=EmbedFactory.BOT_ICON)
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="shop", description="🛒 View the coin shop")
async def shop_command(interaction: discord.Interaction):
    lines = []
    for item_id, item in economy_system.SHOP_ITEMS.items():
        lines.append(f"{item['emoji']} **{item['name']}** — `{item['cost']:,}` coins\n> {item['description']}")
    embed = discord.Embed(
        title="🛒 Coin Shop",
        description="\n\n".join(lines),
        color=EmbedFactory.PREMIUM,
    )
    embed.set_footer(
        text=f"{EmbedFactory.FOOTER_TEXT} • /buy <item> to purchase",
        icon_url=EmbedFactory.BOT_ICON,
    )
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="buy", description="🛍️ Buy an item from the shop")
@app_commands.describe(item="Item to buy")
@app_commands.choices(item=[
    app_commands.Choice(name="XP Boost (1 hour)", value="xp_boost_1h"),
    app_commands.Choice(name="XP Boost (3 hours)", value="xp_boost_3h"),
    app_commands.Choice(name="XP Boost (24 hours)", value="xp_boost_1d"),
    app_commands.Choice(name="Lucky Charm", value="lucky_charm"),
])
async def buy_command(interaction: discord.Interaction, item: str):
    ok, msg = economy_system.apply_purchase(interaction.guild_id, interaction.user.id, item)
    if ok:
        embed = discord.Embed(title="🛍️ Purchase Complete", description=msg, color=EmbedFactory.SUCCESS)
        embed.add_field(name="💰 Balance", value=f"`{economy_system.get_balance(interaction.guild_id, interaction.user.id):,}` coins")
        embed.set_footer(text=EmbedFactory.FOOTER_TEXT, icon_url=EmbedFactory.BOT_ICON)
        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message(f"❌ {msg}", ephemeral=True)


@bot.tree.command(name="rich", description="💎 Richest members by coin balance")
async def rich_command(interaction: discord.Interaction):
    board = economy_system.get_balance_leaderboard(interaction.guild_id)
    if not board:
        await interaction.response.send_message("📭 No balances yet!", ephemeral=True)
        return
    medals = ["🥇", "🥈", "🥉"]
    lines = []
    for i, (uid, bal) in enumerate(board[:10]):
        try:
            member = interaction.guild.get_member(int(uid))
            name = member.display_name if member else f"User {uid}"
        except Exception:
            name = f"User {uid}"
        medal = medals[i] if i < 3 else f"`#{i+1}`"
        lines.append(f"{medal} **{name}** — `{bal:,}` coins")
    embed = discord.Embed(title="💎 Richest Members", description="\n".join(lines), color=EmbedFactory.GOLD)
    embed.set_footer(text=EmbedFactory.FOOTER_TEXT, icon_url=EmbedFactory.BOT_ICON)
    await interaction.response.send_message(embed=embed)


# ═══════════════════════════════════════════════════════════════════════════════
# ACHIEVEMENTS & SEASONS
# ═══════════════════════════════════════════════════════════════════════════════

@bot.tree.command(name="achievements", description="🏅 View achievements (yours or someone's)")
@app_commands.describe(member="User to check (defaults to you)")
async def achievements_command(interaction: discord.Interaction, member: Optional[discord.Member] = None):
    member = member or interaction.user
    stats = level_system.get_user_stats(interaction.guild_id, member.id)
    if stats is None:
        await interaction.response.send_message("❌ No data for this user yet.", ephemeral=True)
        return
    unlocked = stats.get("achievements", [])
    all_ach = level_system.ACHIEVEMENTS
    lines = []
    for aid, ach in all_ach.items():
        is_unlocked = any(a["name"] == ach["name"] for a in unlocked)
        mark = "✅" if is_unlocked else "🔒"
        lines.append(f"{mark} {ach['emoji']} **{ach['name']}** — {ach['desc']}")
    embed = discord.Embed(
        title=f"🏅 {member.display_name}'s Achievements",
        description=f"`{len(unlocked)}/{len(all_ach)}` unlocked\n\n" + "\n".join(lines),
        color=EmbedFactory.GOLD,
    )
    embed.set_footer(text=EmbedFactory.FOOTER_TEXT, icon_url=EmbedFactory.BOT_ICON)
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="weekly", description="📅 This week's XP leaderboard")
async def weekly_command(interaction: discord.Interaction):
    board = level_system.get_weekly_leaderboard(interaction.guild_id)
    if not board:
        await interaction.response.send_message("📭 No XP earned this week yet!", ephemeral=True)
        return
    medals = ["🥇", "🥈", "🥉"]
    lines = []
    for i, (uid, weekly_xp) in enumerate(board[:10]):
        try:
            member = interaction.guild.get_member(int(uid))
            name = member.display_name if member else f"User {uid}"
        except Exception:
            name = f"User {uid}"
        medal = medals[i] if i < 3 else f"`#{i+1}`"
        lines.append(f"{medal} **{name}** — `{weekly_xp:,}` XP this week")
    embed = discord.Embed(title="📅 Weekly Leaderboard", description="\n".join(lines), color=EmbedFactory.CHECKING)
    embed.set_footer(
        text=f"{EmbedFactory.FOOTER_TEXT} • Resets every week",
        icon_url=EmbedFactory.BOT_ICON,
    )
    await interaction.response.send_message(embed=embed)


# ═══════════════════════════════════════════════════════════════════════════════
# MINI-GAMES
# ═══════════════════════════════════════════════════════════════════════════════

@bot.tree.command(name="rps", description="✊ Rock paper scissors vs the bot")
@app_commands.choices(choice=[
    app_commands.Choice(name="Rock ✊", value="rock"),
    app_commands.Choice(name="Paper ✋", value="paper"),
    app_commands.Choice(name="Scissors ✌️", value="scissors"),
])
async def rps_command(interaction: discord.Interaction, choice: str):
    bot_choice = random.choice(["rock", "paper", "scissors"])
    emojis = {"rock": "✊", "paper": "✋", "scissors": "✌️"}
    if choice == bot_choice:
        result = "It's a tie! 🤝"
    elif (choice == "rock" and bot_choice == "scissors") or \
         (choice == "paper" and bot_choice == "rock") or \
         (choice == "scissors" and bot_choice == "paper"):
        result = "You win! 🎉"
    else:
        result = "I win! 😎"
    embed = discord.Embed(
        title="✊ Rock Paper Scissors",
        description=f"You chose {emojis[choice]} · I chose {emojis[bot_choice]}\n\n**{result}**",
        color=EmbedFactory.PREMIUM,
    )
    embed.set_footer(text=EmbedFactory.FOOTER_TEXT, icon_url=EmbedFactory.BOT_ICON)
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="guess", description="🔢 Guess the number (1-100)")
@app_commands.describe(number="Your guess")
async def guess_command(interaction: discord.Interaction, number: int):
    if number < 1 or number > 100:
        await interaction.response.send_message("❌ Pick a number between 1 and 100.", ephemeral=True)
        return
    answer = random.randint(1, 100)
    diff = abs(number - answer)
    if number == answer:
        msg = "🎯 EXACT MATCH! You're a mind reader!"
        color = EmbedFactory.SUCCESS
    elif diff <= 5:
        msg = f"🔥 So close! The number was **{answer}**."
        color = EmbedFactory.GOLD
    elif diff <= 20:
        msg = f"😊 Not bad! The number was **{answer}**."
        color = EmbedFactory.CHECKING
    else:
        msg = f"😅 Way off! The number was **{answer}**."
        color = EmbedFactory.ERROR
    embed = discord.Embed(title="🔢 Guess the Number", description=msg, color=color)
    embed.set_footer(text=EmbedFactory.FOOTER_TEXT, icon_url=EmbedFactory.BOT_ICON)
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="8ball", description="🎱 Ask the magic 8-ball a question")
@app_commands.describe(question="Your yes/no question")
async def eightball_command(interaction: discord.Interaction, question: str):
    answers = [
        "🎱 It is certain.", "🎱 Without a doubt.", "🎱 Yes, definitely.",
        "🎱 Ask again later.", "🎱 Cannot predict now.", "🎱 Outlook not so good.",
        "🎱 Don't count on it.", "🎱 My sources say no.", "🎱 Very doubtful.",
        "🎱 Signs point to yes.",
    ]
    embed = discord.Embed(
        title="🎱 Magic 8-Ball",
        description=f"**Q:** {question}\n\n**A:** {random.choice(answers)}",
        color=EmbedFactory.PREMIUM,
    )
    embed.set_footer(text=EmbedFactory.FOOTER_TEXT, icon_url=EmbedFactory.BOT_ICON)
    await interaction.response.send_message(embed=embed)


# ═══════════════════════════════════════════════════════════════════════════════
# DISCORD LOGGING SYSTEM - Send logs to channel without spam
# ═══════════════════════════════════════════════════════════════════════════════

# Log colors
LOG_COLORS = {
    "success": 0x2ECC71,  # Green
    "error": 0xE74C3C,    # Red 
    "warning": 0xFFA500,  # Orange
    "info": 0x3498DB,     # Blue
    "check": 0x9B59B6,    # Purple
}

# Rate limiting for logs
last_log_times = {}
LOG_COOLDOWN = 2  # Minimum seconds between same type logs

async def send_log(title: str, message: str, log_type: str = "info", no_cooldown: bool = False):
    """Send a log message to the logs channel."""
    try:
        channel = bot.get_channel(LOGS_CHANNEL)
        if not channel:
            return
        
        # Rate limiting - prevent spam (skip if no_cooldown is True)
        if not no_cooldown:
            current_time = time.time()
            if log_type in last_log_times:
                if current_time - last_log_times[log_type] < LOG_COOLDOWN:
                    return
            last_log_times[log_type] = current_time
        
        # Create embed
        color = LOG_COLORS.get(log_type, 0x3498DB)
        embed = discord.Embed(
            title=title,
            description=message,
            color=color,
            timestamp=datetime.now(timezone.utc)
        )
        embed.set_footer(text="⚡ MangoliBot Logs", icon_url="https://i.imgur.com/7ZGzqjY.png")
        
        await channel.send(embed=embed)
        
    except Exception as e:
        logger.error(f"Failed to send log: {e}")


@bot.tree.command(name="stats", description="View bot statistics")
async def stats_command(interaction: discord.Interaction):
    """Display bot statistics."""
    
    uptime = datetime.now(timezone.utc) - bot.start_time
    hours, remainder = divmod(int(uptime.total_seconds()), 3600)
    minutes, seconds = divmod(remainder, 60)
    
    embed = discord.Embed(
        title=f"{Emojis.STAR} Bot Statistics",
        description="MangoliBot Performance",
        color=EmbedColors.INFO,
        timestamp=datetime.now(timezone.utc)
    )
    
    embed.add_field(name="⏱️ Uptime", value=f"```{hours}h {minutes}m {seconds}s```", inline=True)
    embed.add_field(name="🗄️ Servers", value=f"```{len(bot.guilds)}```", inline=True)
    embed.add_field(name="📶 Latency", value=f"```{round(bot.latency * 1000)}ms```", inline=True)
    embed.add_field(name="🧵 Thread Pool", value=f"```{MAX_WORKERS} workers```", inline=True)
    embed.add_field(name="⌘ Commands", value=f"```{len(bot.tree.get_commands())}```", inline=True)
    
    embed.set_footer(text=EmbedFactory.FOOTER_TEXT, icon_url=EmbedFactory.BOT_ICON)
    embed.set_thumbnail(url=bot.user.avatar.url if bot.user.avatar else None)
    
    await interaction.response.send_message(embed=embed)


# ═══════════════════════════════════════════════════════════════════════════════
# PREMIUM HELP SYSTEM - Interactive Dropdown Menu
# ═══════════════════════════════════════════════════════════════════════════════

# Command definitions for each category
HELP_CATEGORIES = {
    "checkers": {
        "emoji": "🔍",
        "name": "Account Checkers",
        "description": "Ultra-fast account validation with 50 parallel workers",
        "color": 0x3498DB,
        "icon": "⚡",
        "commands": [
            ("`/check <type> <file>`", "Check accounts from file (minecraft/netflix/etc)"),
            ("`/steam <combo>`", "Check Steam account instantly"),
            ("`/netflix <combo>`", "Verify Netflix subscription"),
            ("`/disney <combo>`", "Check Disney+ status"),
            ("`/crunchyroll <combo>`", "Validate Crunchyroll premium"),
            ("`/spotify <combo>`", "Check Spotify premium"),
        ]
    },
    "ai": {
        "emoji": "🤖",
        "name": "AI & Chat",
        "description": "Advanced AI powered by MiMo & Groq",
        "color": 0x9B59B6,
        "icon": "✨",
        "commands": [
            ("`/ai <prompt>`", "Chat with advanced AI"),
            ("`/personality`", "Change AI personality type"),
            ("`/queue`", "View current AI request queue"),
        ]
    },
    "leveling": {
        "emoji": "📊",
        "name": "Level System",
        "description": "Earn XP, climb ranks & compete",
        "color": 0xFBBF24,
        "icon": "🏆",
        "commands": [
            ("`/rank [@user]`", "Your level, XP, progress & achievements card"),
            ("`/leaderboard`", "Top 10 members by level"),
            ("`/weekly`", "This week's XP race"),
            ("`/achievements [@user]`", "Your unlocked badges"),
            ("`/invites [@user]`", "How many members you invited"),
            ("`/daily`", "Claim your daily XP + coins bonus"),
        ]
    },
    "economy": {
        "emoji": "💰",
        "name": "Economy & Gambling",
        "description": "Coins, betting & the shop",
        "color": 0x57F287,
        "icon": "💎",
        "commands": [
            ("`/balance [@user]`", "Your coin balance & active boosts"),
            ("`/give <@user> <amount>`", "Send coins to a friend"),
            ("`/coinflip <heads|tails> <bet>`", "Bet on a coin flip"),
            ("`/slots <bet>`", "Spin the slot machine"),
            ("`/shop`", "Browse the coin shop"),
            ("`/buy <item>`", "Buy XP boosters & lucky charms"),
            ("`/rich`", "Richest members"),
        ]
    },
    "games": {
        "emoji": "🎮",
        "name": "Mini-Games",
        "description": "Quick fun games to play",
        "color": 0xED4245,
        "icon": "🎲",
        "commands": [
            ("`/rps <choice>`", "Rock paper scissors vs bot"),
            ("`/guess <1-100>`", "Guess the secret number"),
            ("`/8ball <question>`", "Ask the magic 8-ball"),
        ]
    },
    "voice": {
        "emoji": "🔊",
        "name": "Voice Channel",
        "description": "Moroccan meme sounds 24/7",
        "color": 0x5865F2,
        "icon": "🎵",
        "commands": [
            ("`/voicejoin <channel>`", "Join & play random sounds"),
            ("`/voicestop`", "Pause sound playback"),
            ("`/voiceplay`", "Resume sound playback"),
            ("`/voiceleave`", "Disconnect from voice"),
            ("`/voicestatus`", "Check voice status"),
            ("`/playsoundlink <url>`", "Play MyInstants link"),
        ]
    },
    "general": {
        "emoji": "⚙️",
        "name": "General",
        "description": "Bot info & utilities",
        "color": 0x34495E,
        "icon": "🔧",
        "commands": [
            ("`/help`", "This interactive help menu"),
            ("`/stats`", "Bot statistics & uptime"),
            ("`/serverstats`", "Server dashboard"),
            ("`/profile [@user]`", "User profile card"),
            ("`/personality`", "Change AI personality"),
            ("`/poll <question> <options>`", "Create interactive poll"),
        ]
    }
}


class HelpCategorySelect(discord.ui.Select):
    """Dropdown select for help categories."""
    
    def __init__(self):
        options = [
            discord.SelectOption(
                label=cat["name"],
                value=key,
                description=cat["description"][:50],
                emoji=cat["emoji"]
            )
            for key, cat in HELP_CATEGORIES.items()
        ]
        super().__init__(
            placeholder="📂 Select a category...",
            options=options,
            min_values=1,
            max_values=1
        )
    
    async def callback(self, interaction: discord.Interaction):
        """Handle category selection."""
        category_key = self.values[0]
        category = HELP_CATEGORIES[category_key]
        
        # Use category-specific color if available, otherwise default to PRIMARY
        color = category.get('color', EmbedFactory.PRIMARY)
        icon = category.get('icon', '')
        
        embed = EmbedFactory.custom(
            title=f"{category['name']}",
            description=category['description'],
            color=color,
            emoji=category['emoji']
        )
        
        # Add commands as fields with better formatting
        for cmd, desc in category["commands"]:
            embed.add_field(name=f"{icon} {cmd}", value=desc, inline=False)
        
        embed.set_footer(
            text=f"{EmbedFactory.FOOTER_TEXT} • {len(category['commands'])} commands",
            icon_url=EmbedFactory.BOT_ICON,
        )
        await interaction.response.edit_message(embed=embed)


class HelpView(discord.ui.View):
    """Interactive help view with dropdown and navigation."""
    
    def __init__(self, author_id: int):
        super().__init__(timeout=60)
        self.author_id = author_id
        self.add_item(HelpCategorySelect())
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Only allow the command author to interact."""
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "❌ This menu isn't for you!", ephemeral=True
            )
            return False
        return True
    
    async def on_timeout(self):
        """Disable all components when timeout."""
        for item in self.children:
            item.disabled = True
    
    def create_home_embed(self) -> discord.Embed:
        """Create the main help menu embed with modern design."""
        total_commands = sum(len(c["commands"]) for c in HELP_CATEGORIES.values())
        
        # Create a beautiful gradient-style embed
        embed = discord.Embed(
            title="✨ MANGOLIBOT HELP CENTER",
            description=(
                "**Welcome to MangoliBot!** 🚀\n\n"
                "Your all-in-one Discord bot for account checking, AI chat, leveling, economy, and more!\n"
                "Select a category from the dropdown below to explore commands."
            ),
            color=EmbedFactory.PRIMARY,
            timestamp=datetime.now(timezone.utc)
        )
        embed.set_footer(text=EmbedFactory.FOOTER_TEXT, icon_url=EmbedFactory.BOT_ICON)
        
        # Build category list with emojis and formatting
        categories_text = ""
        for cat in HELP_CATEGORIES.values():
            icon = cat.get('icon', '▫️')
            categories_text += f"{cat['emoji']} **{cat['name']}**\n{icon} {cat['description']}\n\n"
        
        embed.add_field(name="📂 Available Categories", value=categories_text[:1024], inline=False)
        
        # Add stats with better visual appeal
        embed.add_field(
            name="⚡ Quick Stats",
            value=f"> Commands: `{total_commands}`\n> Categories: `{len(HELP_CATEGORIES)}`\n> Status: `Online`",
            inline=True,
        )
        embed.add_field(
            name="🏆 Get Started",
            value="> Chat & voice for XP\n> `/daily` for bonuses\n> Invite friends for rewards",
            inline=True,
        )
        embed.add_field(
            name="🔗 Useful Links",
            value="> [Dashboard](http://localhost:5000)\n> [Support Server](https://discord.gg/nokiatis)\n> [Invite Bot](https://discord.com/oauth2/authorize)",
            inline=True,
        )
        
        # Add a nice thumbnail or image if available
        # embed.set_thumbnail(url=EmbedFactory.BOT_ICON)
        
        return embed
    
    @discord.ui.button(label="Home", style=discord.ButtonStyle.primary, emoji="🏠", row=1)
    async def home_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Return to home menu."""
        embed = self.create_home_embed()
        await interaction.response.edit_message(embed=embed)
    
    @discord.ui.button(label="Close", style=discord.ButtonStyle.danger, emoji="❌", row=1)
    async def close_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Close the help menu."""
        embed = EmbedFactory.info("Help Closed", "Use `/help` to open again.")
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(embed=embed, view=self)
        self.stop()


@bot.tree.command(name="help", description="📚 Interactive help menu with all commands")
async def help_command(interaction: discord.Interaction):
    """Display interactive help with dropdown navigation."""
    view = HelpView(interaction.user.id)
    embed = view.create_home_embed()
    await interaction.response.send_message(embed=embed, view=view)


@bot.tree.command(name="personality", description="🎭 Change AI personality")
@app_commands.describe(
    personality="Choose a personality for the AI"
)
async def personality_command(interaction: discord.Interaction, personality: str = None):
    """Change the AI personality."""
    # Create a dropdown menu if no personality specified
    if personality is None:
        view = PersonalityView()
        embed = discord.Embed(
            title="🎭 AI Personality Settings",
            description="Choose a personality for Mangoli AI:",
            color=0x5865F2
        )
        await interaction.response.send_message(embed=embed, view=view)
        return

    # Validate and set personality
    personality = personality.lower()
    valid_personalities = ["default", "ultra_toxic", "professional", "friendly", "funny", "wise", "tech", "creative", "teacher", "detective", "pirate", "gangster", "roast_master", "sarcastic", "angry"]

    if personality not in valid_personalities:
        await interaction.response.send_message(
            f"❌ Invalid personality! Available personalities: {', '.join(valid_personalities)}",
            ephemeral=True
        )
        return

    # Set personality
    async with MiMoAI(MIMO_API_KEY) as ai:
        success = ai.set_personality(personality)
        if success:
            personality_info = ai.personalities[personality]
            embed = discord.Embed(
                title="✅ Personality Changed!",
                description=f"Mangoli AI is now using the **{personality}** personality!",
                color=0x57F287
            )
            embed.add_field(name="Name", value=personality_info["name"], inline=True)
            embed.add_field(name="Language", value=personality_info["language"], inline=True)
            embed.add_field(name="Style", value=personality_info["style"], inline=False)
            embed.add_field(name="Traits", value=personality_info["traits"], inline=False)
            embed.set_footer(text=f"Changed by {interaction.user.name}", icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message("❌ Failed to change personality. Please try again.", ephemeral=True)


class PersonalityView(discord.ui.View):
    """Dropdown menu for selecting AI personality."""

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.select(
        placeholder="Choose a personality...",
        min_values=1,
        max_values=1,
        options=[
            discord.SelectOption(
                label="Default (Toxic)",
                description="Very toxic and rude personality",
                emoji="💀",
                value="default"
            ),
            discord.SelectOption(
                label="Ultra Toxic",
                description="MOST TOXIC personality ever",
                emoji="☠️",
                value="ultra_toxic"
            ),
            discord.SelectOption(
                label="Professional",
                description="Formal and helpful assistant",
                emoji="👔",
                value="professional"
            ),
            discord.SelectOption(
                label="Friendly",
                description="Warm and approachable",
                emoji="😊",
                value="friendly"
            ),
            discord.SelectOption(
                label="Funny",
                description="Hilarious and witty",
                emoji="😂",
                value="funny"
            ),
            discord.SelectOption(
                label="Wise",
                description="Philosophical and thoughtful",
                emoji="🧙",
                value="wise"
            ),
            discord.SelectOption(
                label="Tech",
                description="Tech-savvy and innovative",
                emoji="💻",
                value="tech"
            ),
            discord.SelectOption(
                label="Creative",
                description="Artistic and innovative",
                emoji="🎨",
                value="creative"
            ),
            discord.SelectOption(
                label="Teacher",
                description="Patient and educational",
                emoji="📚",
                value="teacher"
            ),
            discord.SelectOption(
                label="Detective",
                description="Investigative and analytical",
                emoji="🔍",
                value="detective"
            ),
            discord.SelectOption(
                label="Pirate",
                description="Adventure-loving pirate",
                emoji="🏴‍☠️",
                value="pirate"
            ),
            discord.SelectOption(
                label="Gangster",
                description="Street thug personality",
                emoji="🔫",
                value="gangster"
            ),
            discord.SelectOption(
                label="Roast Master",
                description="Legendary roaster",
                emoji="🔥",
                value="roast_master"
            ),
            discord.SelectOption(
                label="Sarcastic",
                description="Extremely sarcastic",
                emoji="😏",
                value="sarcastic"
            ),
            discord.SelectOption(
                label="Angry",
                description="Always angry and yelling",
                emoji="😤",
                value="angry"
            )
        ]
    )
    async def callback(self, interaction: discord.Interaction):
        """Handle personality selection."""
        personality = self.values[0]

        # Set personality
        async with MiMoAI(MIMO_API_KEY) as ai:
            success = ai.set_personality(personality)
            if success:
                personality_info = ai.personalities[personality]
                embed = discord.Embed(
                    title="✅ Personality Changed!",
                    description=f"Mangoli AI is now using the **{personality}** personality!",
                    color=0x57F287
                )
                embed.add_field(name="Name", value=personality_info["name"], inline=True)
                embed.add_field(name="Language", value=personality_info["language"], inline=True)
                embed.add_field(name="Style", value=personality_info["style"], inline=False)
                embed.add_field(name="Traits", value=personality_info["traits"], inline=False)
                embed.set_footer(text=f"Changed by {interaction.user.name}", icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
                await interaction.response.edit_message(embed=embed, view=None)
            else:
                await interaction.response.send_message("❌ Failed to change personality. Please try again.", ephemeral=True)


# ═══════════════════════════════════════════════════════════════════════════════
# NEW PREMIUM FEATURES
# ═══════════════════════════════════════════════════════════════════════════════

@bot.tree.command(name="serverstats", description="📊 View server statistics dashboard")
async def serverstats_command(interaction: discord.Interaction):
    """Display comprehensive server statistics."""
    guild = interaction.guild
    if not guild:
        await interaction.response.send_message("This command only works in a server!", ephemeral=True)
        return
    
    # Calculate member stats
    total_members = guild.member_count
    online = sum(1 for m in guild.members if m.status != discord.Status.offline)
    humans = sum(1 for m in guild.members if not m.bot)
    bots = sum(1 for m in guild.members if m.bot)
    
    # Create embed
    embed = EmbedFactory.custom(
        title=f"{guild.name}",
        description="Server Statistics Dashboard",
        color=EmbedFactory.PRIMARY,
        emoji="📊"
    )
    
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    
    # Member stats
    embed.add_field(
        name="👥 Members",
        value=f"```yaml\nTotal: {total_members:,}\nOnline: {online:,}\nHumans: {humans:,}\nBots: {bots:,}\n```",
        inline=True
    )
    
    # Boost stats
    embed.add_field(
        name="🚀 Boosts",
        value=f"```yaml\nLevel: {guild.premium_tier}\nBoosts: {guild.premium_subscription_count or 0}\n```",
        inline=True
    )
    
    # Server info
    embed.add_field(
        name="📅 Created",
        value=f"<t:{int(guild.created_at.timestamp())}:D>",
        inline=True
    )
    
    # Channels
    text_channels = len(guild.text_channels)
    voice_channels = len(guild.voice_channels)
    categories = len(guild.categories)
    
    embed.add_field(
        name="💬 Channels",
        value=f"```yaml\nText: {text_channels}\nVoice: {voice_channels}\nCategories: {categories}\n```",
        inline=True
    )
    
    # Roles
    embed.add_field(
        name="🎭 Roles",
        value=f"```{len(guild.roles)} roles```",
        inline=True
    )
    
    # Owner
    embed.add_field(
        name="👑 Owner",
        value=f"{guild.owner.mention if guild.owner else 'Unknown'}",
        inline=True
    )
    
    embed.set_footer(text=EmbedFactory.FOOTER_TEXT, icon_url=EmbedFactory.BOT_ICON)
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="profile", description="👤 View user profile card")
@app_commands.describe(user="The user to view (leave empty for yourself)")
async def profile_command(interaction: discord.Interaction, user: Optional[discord.Member] = None):
    """Display a rich user profile card."""
    target = user or interaction.user
    
    embed = EmbedFactory.custom(
        title=f"{target.display_name}",
        description=f"{target.mention}",
        color=target.color if target.color != discord.Color.default() else EmbedFactory.PRIMARY,
        emoji="👤"
    )
    
    if target.avatar:
        embed.set_thumbnail(url=target.avatar.url)
    
    # Account info
    embed.add_field(
        name="📅 Account Created",
        value=f"<t:{int(target.created_at.timestamp())}:D>\n(<t:{int(target.created_at.timestamp())}:R>)",
        inline=True
    )
    
    # Server join
    if hasattr(target, 'joined_at') and target.joined_at:
        embed.add_field(
            name="📥 Joined Server",
            value=f"<t:{int(target.joined_at.timestamp())}:D>\n(<t:{int(target.joined_at.timestamp())}:R>)",
            inline=True
        )
    
    # Status
    status_map = {
        discord.Status.online: "🟢 Online",
        discord.Status.idle: "🟡 Idle",
        discord.Status.dnd: "🔴 Do Not Disturb",
        discord.Status.offline: "⚫ Offline"
    }
    embed.add_field(
        name="📊 Status",
        value=status_map.get(target.status, "❓ Unknown"),
        inline=True
    )
    
    # Roles (top 10)
    roles = [r.mention for r in target.roles[1:] if r.name != "@everyone"][:10]
    roles_text = ", ".join(roles) if roles else "No roles"
    if len(target.roles) > 11:
        roles_text += f" +{len(target.roles) - 11} more"
    embed.add_field(name=f"🎭 Roles [{len(target.roles) - 1}]", value=roles_text, inline=False)
    
    # Badges
    badges = []
    if target.premium_since:
        badges.append("💎 Server Booster")
    if target.bot:
        badges.append("🤖 Bot")
    if target.id == interaction.guild.owner_id:
        badges.append("👑 Owner")
    
    if badges:
        embed.add_field(name="🏷️ Badges", value=" ".join(badges), inline=False)

    # Level / XP info (if they have any activity)
    try:
        lv_stats = level_system.get_user_stats(interaction.guild_id, target.id)
        if lv_stats and lv_stats.get("xp", 0) > 0:
            embed.add_field(
                name=f"{level_system.level_emoji(lv_stats['level'])} Level {lv_stats['level']}",
                value=f"`{lv_stats['xp']:,}` XP · `{economy_system.get_balance(interaction.guild_id, target.id):,}` coins",
                inline=True,
            )
    except Exception:
        pass
    
    await interaction.response.send_message(embed=embed)


# Poll system with voting
class PollView(discord.ui.View):
    """Interactive poll view with voting buttons."""
    
    def __init__(self, question: str, options: list, author_id: int, duration: int = 300):
        super().__init__(timeout=duration)
        self.question = question
        self.options = options
        self.author_id = author_id
        self.message = None
        self.votes = {i: set() for i in range(len(options))}  # option_index: set of user_ids
        
        # Create voting buttons
        for i, option in enumerate(options[:5]):  # Max 5 options
            button = discord.ui.Button(
                label=f"{i+1}",
                style=discord.ButtonStyle.primary,
                emoji=["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"][i],
                custom_id=f"poll_vote_{i}"
            )
            button.callback = self.create_vote_callback(i)
            self.add_item(button)
    
    def create_vote_callback(self, option_index: int):
        async def callback(interaction: discord.Interaction):
            user_id = interaction.user.id
            
            # Remove previous vote
            for votes in self.votes.values():
                votes.discard(user_id)
            
            # Add new vote
            self.votes[option_index].add(user_id)
            
            # Update embed
            embed = self.create_poll_embed()
            await interaction.response.edit_message(embed=embed)
        
        return callback
    
    def create_poll_embed(self) -> discord.Embed:
        """Create poll embed with bar chart."""
        embed = EmbedFactory.custom(
            title=self.question,
            description="Click a button to vote!",
            color=EmbedFactory.PRIMARY,
            emoji="📊"
        )
        
        total_votes = sum(len(v) for v in self.votes.values())
        
        for i, option in enumerate(self.options):
            vote_count = len(self.votes[i])
            percentage = (vote_count / total_votes * 100) if total_votes > 0 else 0
            
            # Create bar
            filled = int(percentage / 5)  # 20 chars total
            bar = "█" * filled + "░" * (20 - filled)
            
            emoji = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"][i]
            embed.add_field(
                name=f"{emoji} {option}",
                value=f"`{bar}` {percentage:.0f}% ({vote_count})",
                inline=False
            )
        
        embed.add_field(
            name="📈 Total Votes",
            value=f"`{total_votes}` votes",
            inline=False
        )
        
        return embed
    
    async def on_timeout(self):
        """Disable buttons when poll ends and reflect it in the message."""
        for item in self.children:
            item.disabled = True
        if self.message is not None:
            try:
                embed = self.create_poll_embed()
                embed.set_footer(text="🔒 Poll ended")
                await self.message.edit(embed=embed, view=self)
            except Exception:
                pass


@bot.tree.command(name="poll", description="📊 Create an interactive poll")
@app_commands.describe(
    question="The poll question",
    options="Options separated by commas (max 5)"
)
async def poll_command(interaction: discord.Interaction, question: str, options: str):
    """Create an interactive poll with voting."""
    option_list = [o.strip() for o in options.split(",") if o.strip()][:5]
    
    if len(option_list) < 2:
        embed = EmbedFactory.error("Invalid Poll", "Please provide at least 2 options separated by commas.")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    view = PollView(question, option_list, interaction.user.id)
    embed = view.create_poll_embed()
    
    await interaction.response.send_message(embed=embed, view=view)


# ═══════════════════════════════════════════════════════════════════════════════
# ERROR HANDLING
# ═══════════════════════════════════════════════════════════════════════════════

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    """Global error handler for slash commands."""
    
    if isinstance(error, app_commands.CommandOnCooldown):
        embed = discord.Embed(
            title=f"{Emojis.WARNING} Cooldown Active",
            description=f"Please wait **{error.retry_after:.1f}s** before using this command again.",
            color=EmbedColors.WARNING
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
    elif isinstance(error, app_commands.MissingPermissions):
        embed = discord.Embed(
            title=f"{Emojis.ERROR} Permission Denied",
            description="You don't have permission to use this command.",
            color=EmbedColors.ERROR
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
    else:
        logger.error(f"Command error: {error}")
        embed = EmbedFactory.error(
            title="Error",
            description=f"An error occurred:\n```{str(error)[:200]}```"
        )
        try:
            if interaction.response.is_done():
                await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                await interaction.response.send_message(embed=embed, ephemeral=True)
        except:
            pass

# ═══════════════════════════════════════════════════════════════════════════════
# VOICE CHANNEL COMMANDS - 24/7 Voice with Game Lobby Sounds
# ═══════════════════════════════════════════════════════════════════════════════

# Voice state tracking
voice_clients = {}   # Guild ID -> VoiceClient
voice_tasks = {}     # Guild ID -> Background task
voice_enabled = {}   # Guild ID -> Bool
voice_paused = {}    # Guild ID -> Bool (for stop/resume)

# 🇲🇦 MOROCCAN MEMES ONLY - from myinstants.com/en/index/ma/
GAME_SOUNDS = {
    "moroccan": [
        # Top trending Moroccan sounds
        "https://www.myinstants.com/media/sounds/tir-bzokok.mp3",
        "https://www.myinstants.com/media/sounds/fahhhhhhhhhhhhhh.mp3",
        "https://www.myinstants.com/media/sounds/wi-wi-wi-wi.mp3",
        "https://www.myinstants.com/media/sounds/nari-9wedtiha.mp3",
        "https://www.myinstants.com/media/sounds/l3azwa.mp3",
        "https://www.myinstants.com/media/sounds/ayeh-ayeh-ayeh.mp3",
        "https://www.myinstants.com/media/sounds/merhba-biiiik.mp3",
        "https://www.myinstants.com/media/sounds/l7loobn-awlidi.mp3",
        "https://www.myinstants.com/media/sounds/faaah.mp3",
        "https://www.myinstants.com/media/sounds/nivo-taaaaaye7.mp3",
        "https://www.myinstants.com/media/sounds/sir-lay3tik-l7wa.mp3",
        "https://www.myinstants.com/media/sounds/wata-sir-tkawd.mp3",
        "https://www.myinstants.com/media/sounds/romanceeeeeeeeeeeeee.mp3",
        "https://www.myinstants.com/media/sounds/sabab-ach-wlah-ma3rfna.mp3",
        "https://www.myinstants.com/media/sounds/a-sbhanlah-a-wld-lk.mp3",
        "https://www.myinstants.com/media/sounds/le-ileha-ella-allah.mp3",
        "https://www.myinstants.com/media/sounds/wyly-wyly-l-fy.mp3",
        "https://www.myinstants.com/media/sounds/layn3el-dil-babakom-monafi9in.mp3",
        # More Moroccan sounds
        "https://www.myinstants.com/media/sounds/dexter-song-2.mp3",
        "https://www.myinstants.com/media/sounds/mi-bombo.mp3",
        "https://www.myinstants.com/media/sounds/oh-my-god-bro-oh-hell-nah-man.mp3",
        "https://www.myinstants.com/media/sounds/tuco-get-out.mp3",
        "https://www.myinstants.com/media/sounds/hello-motherf-r.mp3",
        "https://www.myinstants.com/media/sounds/snore-mimimimimimi.mp3",
        "https://www.myinstants.com/media/sounds/pew_pew.mp3",
        "https://www.myinstants.com/media/sounds/gay-mp3.mp3",
        "https://www.myinstants.com/media/sounds/spongebob-fail.mp3",
        # Arabic/Darija memes
        "https://www.myinstants.com/media/sounds/hhhhhh.mp3",
        "https://www.myinstants.com/media/sounds/wallah.mp3",
        "https://www.myinstants.com/media/sounds/yallah.mp3",
        "https://www.myinstants.com/media/sounds/habibi.mp3",
        "https://www.myinstants.com/media/sounds/allah-akbar.mp3",
        "https://www.myinstants.com/media/sounds/bismillah.mp3",
        "https://www.myinstants.com/media/sounds/mashallah.mp3",
        "https://www.myinstants.com/media/sounds/inshallah.mp3",
        "https://www.myinstants.com/media/sounds/subhanallah.mp3",
        "https://www.myinstants.com/media/sounds/astaghfirullah.mp3",
    ]
}

# Flatten all sounds into one list
ALL_SOUNDS = []
for sounds in GAME_SOUNDS.values():
    ALL_SOUNDS.extend(sounds)


async def play_random_game_sounds(voice_client, guild_id):
    """Background task to play random game sounds in voice channel."""
    while voice_enabled.get(guild_id, False) and voice_client and voice_client.is_connected():
        try:
            # Check if paused
            if voice_paused.get(guild_id, False):
                await asyncio.sleep(5)
                continue
            
            # Wait random interval between sounds (20-90 seconds)
            await asyncio.sleep(random.randint(20, 90))
            
            if not voice_enabled.get(guild_id, False) or voice_paused.get(guild_id, False):
                continue
                
            if voice_client and voice_client.is_connected() and not voice_client.is_playing():
                # Pick random game and sound
                game = random.choice(list(GAME_SOUNDS.keys()))
                sound_url = random.choice(GAME_SOUNDS[game])
                
                try:
                    audio_source = discord.FFmpegPCMAudio(
                        sound_url,
                        before_options="-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"
                    )
                    voice_client.play(audio_source)
                    logger.info(f"Playing {game} sound in guild {guild_id}")
                except Exception as e:
                    logger.error(f"Error playing sound: {e}")
                    
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Voice loop error: {e}")
            await asyncio.sleep(10)


@bot.tree.command(name="voicejoin", description="🔊 Join a voice channel and play random game sounds 24/7")
@app_commands.describe(channel="The voice channel to join")
async def voicejoin_command(interaction: discord.Interaction, channel: discord.VoiceChannel):
    """Join a voice channel and play random game sounds."""
    guild_id = interaction.guild_id
    
    # Defer immediately to prevent interaction timeout during slow connections
    await interaction.response.defer()

    # Check voice prerequisites before attempting to connect
    if shutil.which("ffmpeg") is None:
        embed = EmbedFactory.warning(
            title="Voice Not Available",
            description=(
                "`ffmpeg` is not installed on this host, so the bot cannot play audio.\n\n"
                "**How to fix:**\n"
                "• Linux: `sudo apt install ffmpeg`\n"
                "• Windows: download from ffmpeg.org and add it to PATH\n\n"
                "Note: discord.py 2.7+ also requires the `davey` package for voice."
            )
        )
        await interaction.followup.send(embed=embed, ephemeral=True)
        return

    try:
        # Disconnect from any existing voice
        if guild_id in voice_clients and voice_clients[guild_id]:
            try:
                voice_enabled[guild_id] = False
                await voice_clients[guild_id].disconnect()
            except:
                pass
        
        # Cancel existing task
        if guild_id in voice_tasks and voice_tasks[guild_id]:
            voice_tasks[guild_id].cancel()
        
        # Connect to new channel with timeout
        try:
            voice_client = await asyncio.wait_for(channel.connect(), timeout=15.0)
        except asyncio.TimeoutError:
            embed = EmbedFactory.error(
                title="Connection Timeout",
                description="Could not connect to voice server in time.\n\n**Possible causes:**\n• Network/DNS issues\n• Discord voice servers unavailable\n• Firewall blocking voice"
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        voice_clients[guild_id] = voice_client
        voice_enabled[guild_id] = True
        voice_paused[guild_id] = False
        
        # Start background sound task
        task = asyncio.create_task(play_random_game_sounds(voice_client, guild_id))
        voice_tasks[guild_id] = task
        
        # List available games
        games_list = ", ".join([f"🎮 {g.title()}" for g in GAME_SOUNDS.keys()])
        
        embed = EmbedFactory.success(
            title="Joined Voice Channel!",
            description=f"```yaml\nChannel: {channel.name}\nMode: 24/7 Game Sounds\nStatus: Playing\n```",
        )
        embed.timestamp = datetime.now(timezone.utc)
        embed.add_field(
            name="🎮 Game Sounds",
            value=games_list,
            inline=False
        )
        embed.add_field(
            name="⚡ Commands",
            value="```\n/voicestop  - Pause sounds\n/voiceplay  - Resume sounds\n/voiceleave - Disconnect\n/voicestatus - Check status\n```",
            inline=False
        )
        embed.set_footer(text="⚡ MangoliBot Voice • 24/7 Game Lobby")
        
        await interaction.followup.send(embed=embed)
        logger.info(f"Joined voice: {channel.name} in {interaction.guild.name}")
        
    except discord.errors.ClientException:
        embed = EmbedFactory.error(
            title="Already Connected",
            description="Use `/voiceleave` first, then try again."
        )
        await interaction.followup.send(embed=embed, ephemeral=True)
        
    except Exception as e:
        error_msg = str(e)[:150]
        # Check for common network errors
        if "getaddrinfo failed" in str(e) or "DNS" in str(e):
            embed = EmbedFactory.error(
                title="DNS/Network Error",
                description="Could not resolve Discord voice server.\n\n**Try these fixes:**\n• Check your internet connection\n• Restart your router\n• Use Google DNS (8.8.8.8)\n• Disable VPN if using one"
            )
        else:
            embed = EmbedFactory.error(
                title="Failed to Join",
                description=f"```{error_msg}```\n\n**Requirements:**\n• `pip install PyNaCl`\n• FFmpeg installed"
            )
        await interaction.followup.send(embed=embed, ephemeral=True)


@bot.tree.command(name="voicestop", description="⏸️ Pause playing sounds (stay connected)")
async def voicestop_command(interaction: discord.Interaction):
    """Pause sound playback but stay connected."""
    guild_id = interaction.guild_id
    
    if guild_id not in voice_clients or not voice_clients[guild_id]:
        embed = EmbedFactory.error(
            title="Not Connected",
            description="Use `/voicejoin` first."
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    # Stop current sound if playing
    if voice_clients[guild_id].is_playing():
        voice_clients[guild_id].stop()
    
    voice_paused[guild_id] = True
    
    embed = discord.Embed(
        title="⏸️ Sounds Paused",
        description="Bot will stay in channel but won't play sounds.\nUse `/voiceplay` to resume.",
        color=0xFFA500,
        timestamp=datetime.now(timezone.utc)
    )
    embed.set_footer(text="⚡ MangoliBot Voice")
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="voiceplay", description="▶️ Resume playing sounds")
async def voiceplay_command(interaction: discord.Interaction):
    """Resume sound playback."""
    guild_id = interaction.guild_id
    
    if guild_id not in voice_clients or not voice_clients[guild_id]:
        embed = discord.Embed(
            title="❌ Not Connected",
            description="Use `/voicejoin` first.",
            color=0xE74C3C
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    voice_paused[guild_id] = False
    
    embed = discord.Embed(
        title="▶️ Sounds Resumed",
        description="Game sounds will play again!\nUse `/voicestop` to pause.",
        color=0x00FF00,
        timestamp=datetime.now(timezone.utc)
    )
    embed.set_footer(text="⚡ MangoliBot Voice")
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="voiceleave", description="🔇 Leave the voice channel")
async def voiceleave_command(interaction: discord.Interaction):
    """Leave the current voice channel."""
    guild_id = interaction.guild_id
    
    if guild_id not in voice_clients or not voice_clients[guild_id]:
        embed = discord.Embed(
            title="❌ Not Connected",
            description="Bot is not in any voice channel.",
            color=0xE74C3C
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    try:
        voice_enabled[guild_id] = False
        voice_paused[guild_id] = False
        
        # Cancel task
        if guild_id in voice_tasks and voice_tasks[guild_id]:
            voice_tasks[guild_id].cancel()
            del voice_tasks[guild_id]
        
        # Disconnect
        await voice_clients[guild_id].disconnect()
        del voice_clients[guild_id]
        
        embed = discord.Embed(
            title="🔇 Disconnected",
            description="Successfully left the voice channel.",
            color=0xFFA500,
            timestamp=datetime.now(timezone.utc)
        )
        embed.set_footer(text="⚡ MangoliBot Voice")
        await interaction.response.send_message(embed=embed)
        
    except Exception as e:
        embed = discord.Embed(
            title="❌ Error",
            description=f"```{str(e)[:200]}```",
            color=0xE74C3C
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="voicestatus", description="📊 Check voice channel status")
async def voicestatus_command(interaction: discord.Interaction):
    """Check the current voice status."""
    guild_id = interaction.guild_id
    
    is_connected = guild_id in voice_clients and voice_clients[guild_id] and voice_clients[guild_id].is_connected()
    is_playing = is_connected and voice_clients[guild_id].is_playing()
    is_paused = voice_paused.get(guild_id, False)
    
    if is_connected:
        channel_name = voice_clients[guild_id].channel.name
        status = "⏸️ Paused" if is_paused else ("🔊 Playing" if is_playing else "⏳ Waiting")
        
        embed = discord.Embed(
            title="📊 Voice Status",
            color=0x00FF00 if not is_paused else 0xFFA500,
            timestamp=datetime.now(timezone.utc)
        )
        embed.add_field(
            name="Connection",
            value=f"```yaml\nChannel: {channel_name}\nStatus: {status}\nMode: Game Lobby Sounds\n```",
            inline=False
        )
        embed.add_field(
            name="🎮 Games",
            value=", ".join([g.title() for g in GAME_SOUNDS.keys()]),
            inline=False
        )
    else:
        embed = discord.Embed(
            title="📊 Voice Status",
            description="```yaml\nConnected: No\n```\nUse `/voicejoin` to connect.",
            color=0xFFA500,
            timestamp=datetime.now(timezone.utc)
        )
    
    embed.set_footer(text="⚡ MangoliBot Voice")
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="playsoundlink", description="🔊 Play a custom MyInstants sound link")
@app_commands.describe(link="The MyInstants link (e.g. https://www.myinstants.com/en/instant/tir-bzokok-74808/)")
async def playsoundlink_command(interaction: discord.Interaction, link: str):
    """Play a custom sound from MyInstants link."""
    guild_id = interaction.guild_id
    
    # Check if connected to voice
    if guild_id not in voice_clients or not voice_clients[guild_id]:
        embed = discord.Embed(
            title="❌ Not Connected",
            description="Use `/voicejoin` first to join a voice channel.",
            color=0xE74C3C
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    # Extract sound name from link and build MP3 URL
    try:
        # Handle different myinstants URL formats
        # https://www.myinstants.com/en/instant/tir-bzokok-74808/
        # https://www.myinstants.com/instant/tir-bzokok-74808/
        
        if "myinstants.com" not in link:
            embed = discord.Embed(
                title="❌ Invalid Link",
                description="Please provide a valid MyInstants link.\nExample: `https://www.myinstants.com/en/instant/tir-bzokok-74808/`",
                color=0xE74C3C
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Extract the sound name from URL
        # Remove trailing slash and get last part
        parts = link.rstrip('/').split('/')
        sound_name = parts[-1]
        
        # Remove number suffix like -74808 to get clean sound name
        # tir-bzokok-74808 -> tir-bzokok
        sound_parts = sound_name.rsplit('-', 1)
        if len(sound_parts) == 2 and sound_parts[1].isdigit():
            sound_name = sound_parts[0]
        
        # Build MP3 URL
        mp3_url = f"https://www.myinstants.com/media/sounds/{sound_name}.mp3"
        
        # Stop current sound if playing
        if voice_clients[guild_id].is_playing():
            voice_clients[guild_id].stop()
        
        # Play the sound
        audio_source = discord.FFmpegPCMAudio(
            mp3_url,
            before_options="-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"
        )
        voice_clients[guild_id].play(audio_source)
        
        embed = discord.Embed(
            title="🔊 Playing Sound",
            description=f"```yaml\nSound: {sound_name}\nStatus: Playing...\n```",
            color=0x00FF00,
            timestamp=datetime.now(timezone.utc)
        )
        embed.add_field(
            name="🔗 Link",
            value=f"[MyInstants]({link})",
            inline=False
        )
        embed.set_footer(text="⚡ MangoliBot Voice")
        await interaction.response.send_message(embed=embed)
        logger.info(f"Playing custom sound: {sound_name}")
        
    except Exception as e:
        embed = discord.Embed(
            title="❌ Error Playing Sound",
            description=f"```{str(e)[:200]}```\n\nMake sure the link is valid!",
            color=0xE74C3C
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        logger.error(f"Error playing custom sound: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    logger.info("Starting MangoliBot...")
    logger.info("=" * 60)

    # ── Graceful startup checks ──────────────────────────────────────────────
    # 1. Missing / placeholder token
    if not TOKEN or not TOKEN.strip():
        logger.error("❌  No bot token is set!")
        logger.error("    Edit the TOKEN variable at the top of bot.py")
        logger.error("    (or set it via the DISCORD_TOKEN environment variable) and restart.")
        logger.error("    Get a token at https://discord.com/developers/applications")
        sys.exit(1)

    try:
        bot.run(TOKEN)
    except discord.errors.LoginFailure:
        logger.error("❌  Login failed — the bot token is invalid or has been revoked.")
        logger.error("    Generate a new token at https://discord.com/developers/applications")
        logger.error("    → Bot → Reset Token, then paste it into bot.py.")
    except discord.errors.PrivilegedIntentsRequired:
        logger.error("❌  Missing privileged intents.")
        logger.error("    Enable 'MESSAGE CONTENT INTENT' in the Discord Developer Portal")
        logger.error("    → Bot → Privileged Gateway Intents.")
    except discord.HTTPException as e:
        logger.error(f"❌  Discord HTTP error while starting: {e}")
        logger.error("    This is usually a temporary network or Discord-side issue — try again.")
    except Exception as e:
        logger.error(f"❌  Failed to start bot: {e}")
    finally:
        executor.shutdown(wait=False)
