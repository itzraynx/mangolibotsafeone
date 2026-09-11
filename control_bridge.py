"""
═══════════════════════════════════════════════════════════════════════════════
CONTROL BRIDGE
Bridge between the Discord bot and the web dashboard.
by Nokiatis Community
═══════════════════════════════════════════════════════════════════════════════

Shared state + control functions used by the Flask dashboard API. The Flask
server runs in a different thread from the bot's asyncio loop, so every bot
operation goes through run_on_loop() which schedules coroutines safely.
"""

import asyncio
import json
import os
import sys
import threading
import time
from collections import deque
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SETTINGS_FILE = os.path.join(BASE_DIR, 'dashboard_settings.json')

_lock = threading.Lock()

# ── Bot references (set by bot.py at startup) ─────────────────────────────────
bot = None
bot_loop = None
_api_key = None

# Voice state references (set by bot.py)
voice_clients = {}
voice_tasks = {}
voice_enabled = {}
voice_paused = {}
GAME_SOUNDS = {}
ALL_SOUNDS = []
_sound_loop = None

# Log ring buffer
MAX_LOGS = 500
_logs = deque(maxlen=MAX_LOGS)

# Command usage counters
_command_counts = {}

# Disabled commands (name -> Command object so we can restore them)
_disabled_commands = {}

# Bot start time
_bot_start_time = None

# Applied presence (tracked here because discord.py only updates bot.activity
# after a gateway round-trip, which makes direct reads stale)
_applied_presence = {}

DEFAULT_SETTINGS = {
    "ai_enabled": True,
    "ai_personality": "default",
    "ai_channel_id": "",
    "ai_custom_persona": "",
    "presence_status": "online",
    "presence_activity_type": "streaming",
    "presence_text": "Nokiatis Community 🎮",
    "presence_stream_url": "https://twitch.tv/nokiatis",
}


# ═══════════════════════════════════════════════════════════════════════════════
# REGISTRATION
# ═══════════════════════════════════════════════════════════════════════════════

def set_bot(b, voice_state=None, sounds=None, sound_loop=None, api_key=None):
    """Register the running bot (and its voice state) with the bridge."""
    global bot, bot_loop, voice_clients, voice_tasks, voice_enabled, voice_paused
    global GAME_SOUNDS, ALL_SOUNDS, _sound_loop, _api_key, _bot_start_time
    with _lock:
        bot = b
        bot_loop = b.loop
        _api_key = api_key
        _bot_start_time = datetime.now()
        if voice_state:
            voice_clients = voice_state.get('clients', voice_clients)
            voice_tasks = voice_state.get('tasks', voice_tasks)
            voice_enabled = voice_state.get('enabled', voice_enabled)
            voice_paused = voice_state.get('paused', voice_paused)
        if sounds:
            GAME_SOUNDS = sounds
            ALL_SOUNDS = []
            for s in sounds.values():
                ALL_SOUNDS.extend(s)
        if sound_loop:
            _sound_loop = sound_loop
    add_log("INFO", "Bot registered with the dashboard control bridge")


def run_on_loop(coro, timeout=20):
    """Schedule a coroutine on the bot's loop from another thread and wait."""
    if bot_loop is None or bot_loop.is_closed():
        try:
            coro.close()  # avoid "never awaited" warnings
        except Exception:
            pass
        return {"ok": False, "error": "Bot event loop is not running"}
    future = asyncio.run_coroutine_threadsafe(coro, bot_loop)
    try:
        return future.result(timeout=timeout)
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ═══════════════════════════════════════════════════════════════════════════════
# LOGGING
# ═══════════════════════════════════════════════════════════════════════════════

def add_log(level, message):
    with _lock:
        _logs.append({
            "level": str(level).upper(),
            "message": message,
            "time": datetime.now().isoformat(),
        })


def get_logs(level=None, limit=200):
    with _lock:
        logs = list(_logs)
    if level and level.upper() != "ALL":
        logs = [l for l in logs if l["level"] == level.upper()]
    return logs[-limit:]


def get_log_text(level=None):
    lines = []
    for l in get_logs(level=level, limit=MAX_LOGS):
        lines.append(f"[{l['time']}] [{l['level']}] {l['message']}")
    return "\n".join(lines)


def clear_logs():
    with _lock:
        _logs.clear()
    add_log("INFO", "Logs cleared from dashboard")


# ═══════════════════════════════════════════════════════════════════════════════
# COMMAND COUNTERS
# ═══════════════════════════════════════════════════════════════════════════════

def increment_command(name):
    with _lock:
        _command_counts[name] = _command_counts.get(name, 0) + 1


def get_command_counts():
    with _lock:
        return dict(_command_counts)


def reset_command_counts():
    with _lock:
        _command_counts.clear()
    add_log("INFO", "Command statistics reset")


# ═══════════════════════════════════════════════════════════════════════════════
# SETTINGS
# ═══════════════════════════════════════════════════════════════════════════════

def load_settings():
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                return {**DEFAULT_SETTINGS, **json.load(f)}
    except Exception:
        pass
    return dict(DEFAULT_SETTINGS)


def save_settings(settings):
    with _lock:
        try:
            with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=2)
        except Exception:
            pass


def get_settings():
    with _lock:
        return load_settings()


def list_personalities():
    try:
        from mimo_ai import MiMoAI
        return MiMoAI("").list_personalities()
    except Exception:
        return ["default"]


async def _apply_personality(personality, custom_persona):
    if not _api_key:
        return {"ok": False, "error": "No AI API key configured"}
    from mimo_ai import MiMoAI
    ai = MiMoAI(_api_key)
    if not ai.set_personality(personality):
        return {"ok": False, "error": "Unknown personality"}
    ai.set_custom_persona(custom_persona)
    # apply immediately to the singleton-ish behavior via settings is enough;
    # the bot reads settings per-message.
    return {"ok": True}


def set_settings(data):
    """Persist settings and apply live effects (personality)."""
    settings = load_settings()
    for key in DEFAULT_SETTINGS:
        if key in data:
            settings[key] = data[key]
    save_settings(settings)

    if ("ai_personality" in data or "ai_custom_persona" in data) and bot is not None:
        run_on_loop(_apply_personality(settings.get("ai_personality", "default"),
                                       settings.get("ai_custom_persona", "")))

    add_log("INFO", "Dashboard settings updated")
    return settings


# ═══════════════════════════════════════════════════════════════════════════════
# PRESENCE
# ═══════════════════════════════════════════════════════════════════════════════

async def _apply_presence(status, activity_type, text, stream_url):
    import discord
    status_map = {
        "online": discord.Status.online,
        "idle": discord.Status.idle,
        "dnd": discord.Status.dnd,
        "invisible": discord.Status.invisible,
    }
    st = status_map.get(status, discord.Status.online)

    if activity_type == "streaming":
        activity = discord.Streaming(name=text or "Twitch", url=stream_url or "https://twitch.tv/")
    else:
        atype_map = {
            "playing": discord.ActivityType.playing,
            "watching": discord.ActivityType.watching,
            "listening": discord.ActivityType.listening,
            "competing": discord.ActivityType.competing,
        }
        activity = discord.Activity(type=atype_map.get(activity_type, discord.ActivityType.playing), name=text or "")

    await bot.change_presence(status=st, activity=activity)
    return {"ok": True}


def set_presence(status, activity_type, text, stream_url=None):
    settings = load_settings()
    settings["presence_status"] = status
    settings["presence_activity_type"] = activity_type
    settings["presence_text"] = text
    if stream_url is not None:
        settings["presence_stream_url"] = stream_url
    save_settings(settings)

    global _applied_presence
    _applied_presence = {
        "status": status,
        "activity_type": activity_type,
        "activity_name": text,
        "stream_url": stream_url if activity_type == "streaming" else None,
    }

    add_log("INFO", f"Presence updated: {status} / {activity_type} / {text}")
    if bot is not None:
        return run_on_loop(_apply_presence(status, activity_type, text, settings.get("presence_stream_url", "")))
    return {"ok": True}


# ═══════════════════════════════════════════════════════════════════════════════
# COMMAND TOGGLES
# ═══════════════════════════════════════════════════════════════════════════════

async def _disable_command(name):
    cmd = bot.tree.get_command(name)
    if cmd is None:
        return {"ok": False, "error": f"Command '{name}' not found"}
    _disabled_commands[name] = cmd
    bot.tree.remove_command(name)
    try:
        await bot.tree.sync()
    except Exception as e:
        return {"ok": False, "error": str(e)}
    add_log("WARNING", f"Command /{name} disabled from dashboard")
    return {"ok": True}


async def _enable_command(name):
    cmd = _disabled_commands.pop(name, None)
    if cmd is None:
        return {"ok": False, "error": f"Command '{name}' is not disabled"}
    bot.tree.add_command(cmd)
    try:
        await bot.tree.sync()
    except Exception as e:
        return {"ok": False, "error": str(e)}
    add_log("INFO", f"Command /{name} enabled from dashboard")
    return {"ok": True}


def disable_command(name):
    return run_on_loop(_disable_command(name))


def enable_command(name):
    return run_on_loop(_enable_command(name))


# ═══════════════════════════════════════════════════════════════════════════════
# BROADCAST / MESSAGE
# ═══════════════════════════════════════════════════════════════════════════════

async def _send_message(guild_id, channel_id, text):
    guild = bot.get_guild(int(guild_id))
    if not guild:
        return {"ok": False, "error": "Guild not found"}
    channel = guild.get_channel(int(channel_id))
    if not channel:
        return {"ok": False, "error": "Channel not found"}
    await channel.send(text)
    add_log("INFO", f"Broadcast sent to #{channel.name} in {guild.name}")
    return {"ok": True}


def send_message(guild_id, channel_id, text):
    return run_on_loop(_send_message(guild_id, channel_id, text))


# ═══════════════════════════════════════════════════════════════════════════════
# SHUTDOWN / RESTART
# ═══════════════════════════════════════════════════════════════════════════════

async def _shutdown():
    add_log("WARNING", "Bot shutdown requested from dashboard")
    await bot.close()
    return {"ok": True}


def shutdown_bot():
    return run_on_loop(_shutdown())


def restart_bot():
    """Restart the whole process (bot + dashboard) via exec."""
    def _restart():
        time.sleep(1.5)
        os.execv(sys.executable, [sys.executable] + sys.argv)
    add_log("WARNING", "Restart requested from dashboard")
    threading.Thread(target=_restart, daemon=True).start()
    return {"ok": True, "message": "Restarting…"}


# ═══════════════════════════════════════════════════════════════════════════════
# BOT STATUS
# ═══════════════════════════════════════════════════════════════════════════════

def _presence_summary():
    """Snapshot of the bot's current presence (from what we last applied)."""
    if _applied_presence:
        return dict(_applied_presence)
    # fall back to live bot state (may be None right after startup)
    try:
        if bot is None or not bot.is_ready():
            return {}
        a = bot.activity
        return {
            "status": str(bot.status),
            "activity_type": a.type.name if a else None,
            "activity_name": a.name if a else None,
            "stream_url": a.url if isinstance(a, __import__('discord').Streaming) else None,
        }
    except Exception:
        return {}


def get_status():
    if bot is None:
        return {"connected": False, "bot_name": "Mangoli", "reason": "Bot not started"}

    try:
        if not bot.is_ready():
            return {"connected": False, "bot_name": bot.user.name if bot.user else "Mangoli",
                    "reason": "Connecting…"}
    except Exception:
        pass

    uptime = 0
    if _bot_start_time:
        uptime = int((datetime.now() - _bot_start_time).total_seconds())

    with _lock:
        total_commands = sum(_command_counts.values())
        disabled = list(_disabled_commands.keys())

    return {
        "connected": True,
        "bot_name": bot.user.name if bot.user else "Mangoli",
        "bot_id": str(bot.user.id) if bot.user else None,
        "avatar_url": str(bot.user.avatar.url) if bot.user and bot.user.avatar else None,
        "latency_ms": round(bot.latency * 1000) if bot.latency else 0,
        "guild_count": len(bot.guilds),
        "uptime_seconds": uptime,
        "command_count": total_commands,
        "disabled_commands": disabled,
        "presence": _presence_summary(),
    }


def get_system_info():
    import platform
    info = {
        "python": platform.python_version(),
        "platform": platform.system() + " " + platform.release(),
        "os": platform.platform(),
    }
    try:
        import resource
        rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        info["max_rss_kb"] = rss
    except Exception:
        pass
    return info


# ═══════════════════════════════════════════════════════════════════════════════
# VOICE CONTROL
# ═══════════════════════════════════════════════════════════════════════════════

def get_voice_status():
    result = []
    with _lock:
        items = list(voice_clients.items())
    for guild_id, vc in items:
        try:
            if not vc or not vc.is_connected():
                continue
            guild = bot.get_guild(int(guild_id)) if bot else None
            result.append({
                "guild_id": str(guild_id),
                "guild_name": guild.name if guild else "Unknown",
                "channel_id": str(vc.channel.id) if vc.channel else None,
                "channel_name": vc.channel.name if vc.channel else "Unknown",
                "playing": vc.is_playing(),
                "paused": voice_paused.get(guild_id, False),
                "enabled": voice_enabled.get(guild_id, False),
            })
        except Exception:
            continue
    return result


def get_sound_library():
    lib = []
    for category, urls in GAME_SOUNDS.items():
        for u in urls:
            name = u.rsplit('/', 1)[-1].replace('.mp3', '')
            lib.append({"category": category, "name": name, "url": u})
    return lib


async def _voice_join(guild_id, channel_id):
    guild = bot.get_guild(int(guild_id))
    if not guild:
        return {"ok": False, "error": "Guild not found"}
    channel = guild.get_channel(int(channel_id))
    if not channel:
        return {"ok": False, "error": "Channel not found"}

    gid = int(guild_id)
    if gid in voice_clients and voice_clients[gid]:
        try:
            voice_enabled[gid] = False
            await voice_clients[gid].disconnect()
        except Exception:
            pass
    if gid in voice_tasks and voice_tasks[gid]:
        voice_tasks[gid].cancel()

    try:
        vc = await channel.connect()
    except Exception as e:
        return {"ok": False, "error": str(e)}

    voice_clients[gid] = vc
    voice_enabled[gid] = True
    voice_paused[gid] = False

    if _sound_loop:
        task = asyncio.create_task(_sound_loop(vc, gid))
        voice_tasks[gid] = task

    add_log("INFO", f"Joined voice channel '{channel.name}' in '{guild.name}'")
    return {"ok": True, "channel": channel.name, "guild": guild.name}


async def _voice_leave(guild_id):
    gid = int(guild_id)
    if gid not in voice_clients or not voice_clients[gid]:
        return {"ok": False, "error": "Not connected"}
    voice_enabled[gid] = False
    if gid in voice_tasks and voice_tasks[gid]:
        voice_tasks[gid].cancel()
        del voice_tasks[gid]
    await voice_clients[gid].disconnect()
    del voice_clients[gid]
    add_log("INFO", f"Left voice channel in guild {guild_id}")
    return {"ok": True}


async def _voice_pause(guild_id):
    gid = int(guild_id)
    if gid not in voice_clients or not voice_clients[gid]:
        return {"ok": False, "error": "Not connected"}
    voice_paused[gid] = True
    if voice_clients[gid].is_playing():
        voice_clients[gid].pause()
    add_log("INFO", f"Paused voice in guild {guild_id}")
    return {"ok": True}


async def _voice_resume(guild_id):
    gid = int(guild_id)
    if gid not in voice_clients or not voice_clients[gid]:
        return {"ok": False, "error": "Not connected"}
    voice_paused[gid] = False
    if voice_clients[gid].is_paused():
        voice_clients[gid].resume()
    add_log("INFO", f"Resumed voice in guild {guild_id}")
    return {"ok": True}


async def _voice_play(guild_id, url):
    import discord as _discord
    gid = int(guild_id)
    if gid not in voice_clients or not voice_clients[gid]:
        return {"ok": False, "error": "Not connected"}
    vc = voice_clients[gid]
    if not vc.is_connected():
        return {"ok": False, "error": "Voice client disconnected"}
    try:
        if vc.is_playing():
            vc.stop()
        source = _discord.FFmpegPCMAudio(
            url,
            before_options="-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
        )
        vc.play(source)
        add_log("INFO", f"Playing sound in guild {guild_id}")
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


async def _voice_stop(guild_id):
    gid = int(guild_id)
    if gid not in voice_clients or not voice_clients[gid]:
        return {"ok": False, "error": "Not connected"}
    if voice_clients[gid].is_playing():
        voice_clients[gid].stop()
    return {"ok": True}


def voice_join(guild_id, channel_id):
    return run_on_loop(_voice_join(guild_id, channel_id))


def voice_leave(guild_id):
    return run_on_loop(_voice_leave(guild_id))


def voice_pause(guild_id):
    return run_on_loop(_voice_pause(guild_id))


def voice_resume(guild_id):
    return run_on_loop(_voice_resume(guild_id))


def voice_play(guild_id, url):
    return run_on_loop(_voice_play(guild_id, url))


def voice_stop(guild_id):
    return run_on_loop(_voice_stop(guild_id))


# ═══════════════════════════════════════════════════════════════════════════════
# GUILDS & COMMANDS
# ═══════════════════════════════════════════════════════════════════════════════

def get_guilds():
    if bot is None:
        return []
    guilds = []
    for g in bot.guilds:
        text_channels = []
        voice_channels = []
        for c in g.channels:
            if isinstance(c, __import__('discord').TextChannel):
                text_channels.append({"id": str(c.id), "name": c.name})
            elif isinstance(c, __import__('discord').VoiceChannel):
                voice_channels.append({"id": str(c.id), "name": c.name})
        guilds.append({
            "id": str(g.id),
            "name": g.name,
            "icon_url": str(g.icon.url) if g.icon else None,
            "member_count": g.member_count,
            "text_channels": text_channels,
            "voice_channels": voice_channels,
        })
    return guilds


def get_commands():
    if bot is None:
        return []
    result = []
    with _lock:
        counts = dict(_command_counts)
        disabled = list(_disabled_commands.keys())
    for c in bot.tree.get_commands():
        result.append({
            "name": c.name,
            "description": c.description or "",
            "uses": counts.get(c.name, 0),
            "enabled": True,
        })
    # include disabled ones (not in tree anymore)
    for name in disabled:
        result.append({
            "name": name,
            "description": "",
            "uses": counts.get(name, 0),
            "enabled": False,
        })
    result.sort(key=lambda x: (-x["enabled"], -x["uses"]))
    return result


# ═══════════════════════════════════════════════════════════════════════════════
# MUSIC CONTROL (dashboard)
# ═══════════════════════════════════════════════════════════════════════════════

def _music_node():
    try:
        import wavelink
    except ImportError:
        return None
    if not wavelink.Pool.nodes:
        return None
    return wavelink.Pool.get_node()


def get_music_status():
    """Return current music state across all guilds."""
    node = _music_node()
    if node is None:
        return {"available": False, "players": []}

    out = []
    for guild_id, player in list(node.players.items()):
        try:
            track = player.current
            queue = list(player.queue)
            out.append({
                "guild_id": str(guild_id),
                "playing": player.playing,
                "paused": player.paused,
                "volume": player.volume,
                "loop": player.queue.mode.name if hasattr(player.queue, 'mode') else 'normal',
                "current": {
                    "title": track.title if track else None,
                    "author": track.author if track else None,
                    "artwork": track.artwork if track else None,
                    "length": track.length if track else 0,
                    "position": player.position,
                } if track else None,
                "queue": [
                    {"title": t.title, "author": t.author, "length": t.length}
                    for t in queue[:10]
                ],
                "queue_count": len(queue),
            })
        except Exception:
            continue
    return {"available": True, "players": out}


async def _music_control(guild_id, action, value=None):
    import wavelink
    node = _music_node()
    if node is None:
        return {"ok": False, "error": "Lavalink not connected"}
    player = node.get_player(int(guild_id))
    if not player:
        return {"ok": False, "error": "No active player in this guild"}

    if action == 'pause':
        await player.pause(True)
    elif action == 'resume':
        await player.pause(False)
    elif action == 'skip':
        await player.skip()
    elif action == 'stop':
        player.queue.clear()
        await player.stop()
    elif action == 'shuffle':
        player.queue.shuffle()
    elif action == 'volume':
        v = int(value) if value is not None else 100
        await player.set_volume(max(0, min(200, v)))
    elif action == 'loop':
        modes = ['normal', 'loop', 'loop_all']
        idx = modes.index(getattr(player.queue.mode, 'name', 'normal'))
        nxt = modes[(idx + 1) % 3]
        player.queue.mode = wavelink.QueueMode[nxt]
    elif action == 'play':
        query = value
        if not query:
            return {"ok": False, "error": "query required"}
        search = await wavelink.Playable.search(query)
        if not search:
            return {"ok": False, "error": "No results"}
        if isinstance(search[0], wavelink.Playlist):
            for t in search[0].tracks:
                player.queue.put(t)
            if not player.playing:
                await player.play(player.queue.get())
        else:
            track = search[0]
            if player.playing:
                player.queue.put(track)
            else:
                await player.play(track)
    else:
        return {"ok": False, "error": f"Unknown action '{action}'"}

    add_log("INFO", f"Music control from dashboard: {action} in guild {guild_id}")
    return {"ok": True}


def music_control(guild_id, action, value=None):
    return run_on_loop(_music_control(guild_id, action, value))


# ═══════════════════════════════════════════════════════════════════════════════
# MODERATION (dashboard)
# ═══════════════════════════════════════════════════════════════════════════════

_warnings = {}  # guild_id -> {user_id: [warnings]}


def get_members(guild_id):
    """Return all members with basic info for the moderation panel."""
    if bot is None:
        return []
    guild = bot.get_guild(int(guild_id))
    if not guild:
        return []
    out = []
    for m in guild.members:
        out.append({
            "user_id": str(m.id),
            "name": m.display_name,
            "username": str(m),
            "avatar_url": str(m.display_avatar.url) if m.display_avatar else None,
            "is_bot": m.bot,
            "joined_at": m.joined_at.isoformat() if m.joined_at else None,
            "top_role": m.top_role.name if m.top_role else "",
            "warnings": len(_warnings.get(str(guild.id), {}).get(str(m.id), [])),
        })
    out.sort(key=lambda x: (x["is_bot"], x["name"].lower()))
    return out


async def _mod_action(guild_id, action, user_id, reason=None):
    guild = bot.get_guild(int(guild_id))
    if not guild:
        return {"ok": False, "error": "Guild not found"}
    member = guild.get_member(int(user_id))
    if not member:
        return {"ok": False, "error": "Member not found"}

    gid = str(guild_id)
    uid = str(user_id)

    try:
        if action == 'kick':
            await member.kick(reason=reason or "Kicked from dashboard")
            msg = f"Kicked {member.display_name}"
        elif action == 'ban':
            await member.ban(reason=reason or "Banned from dashboard", delete_message_days=1)
            msg = f"Banned {member.display_name}"
        elif action == 'warn':
            _warnings.setdefault(gid, {}).setdefault(uid, []).append({
                "reason": reason or "No reason", "time": datetime.now().isoformat(),
            })
            msg = f"Warned {member.display_name}"
        elif action == 'clear_warns':
            _warnings.setdefault(gid, {}).pop(uid, None)
            msg = f"Cleared warnings for {member.display_name}"
        else:
            return {"ok": False, "error": f"Unknown action '{action}'"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

    add_log("WARNING", f"Moderation from dashboard: {action} {member.display_name}")
    return {"ok": True, "message": msg}


def mod_action(guild_id, action, user_id, reason=None):
    return run_on_loop(_mod_action(guild_id, action, user_id, reason))


# ═══════════════════════════════════════════════════════════════════════════════
# GIVEAWAYS (dashboard)
# ═══════════════════════════════════════════════════════════════════════════════

import time as _time

_giveaways = {}  # giveaway_id -> dict
_giveaway_seq = 0


def get_giveaways():
    """List active giveaways (not ended)."""
    out = []
    for gid, g in _giveaways.items():
        out.append({
            "giveaway_id": gid,
            "guild_id": g["guild_id"],
            "prize": g["prize"],
            "winners": g["winners"],
            "ends_at": g["ends_at"],
            "entries": list(g["entries"]),
            "entry_count": len(g["entries"]),
            "channel_id": g["channel_id"],
            "ended": _time.time() >= g["ends_at"],
        })
    out.sort(key=lambda x: x["ends_at"])
    return out


def create_giveaway(guild_id, prize, winners, duration_minutes, channel_id=None):
    global _giveaway_seq
    _giveaway_seq += 1
    gid = f"gw_{_giveaway_seq}"
    _giveaways[gid] = {
        "guild_id": str(guild_id),
        "prize": prize,
        "winners": int(winners),
        "ends_at": _time.time() + (int(duration_minutes) * 60),
        "entries": [],
        "channel_id": str(channel_id) if channel_id else None,
    }
    add_log("INFO", f"Giveaway created: {prize} ({winners} winner(s))")
    return gid


def end_giveaway(giveaway_id):
    gw = _giveaways.get(giveaway_id)
    if not gw:
        return {"ok": False, "error": "Giveaway not found"}
    entries = gw["entries"]
    import random
    if not entries:
        return {"ok": False, "error": "No entries"}
    n = min(int(gw["winners"]), len(entries))
    winners = random.sample(entries, n)
    return {"ok": True, "winners": winners, "prize": gw["prize"]}


def delete_giveaway(giveaway_id):
    if giveaway_id in _giveaways:
        del _giveaways[giveaway_id]
        return {"ok": True}
    return {"ok": False, "error": "Giveaway not found"}


# ═══════════════════════════════════════════════════════════════════════════════
# SCHEDULED ANNOUNCEMENTS (dashboard)
# ═══════════════════════════════════════════════════════════════════════════════

_announcements = {}  # ann_id -> dict
_announce_seq = 0


def get_announcements():
    out = []
    for aid, a in _announcements.items():
        out.append({
            "announcement_id": aid,
            "guild_id": a["guild_id"],
            "channel_id": a["channel_id"],
            "channel_name": a.get("channel_name", ""),
            "message": a["message"],
            "send_at": a["send_at"],
            "sent": a["sent"],
        })
    out.sort(key=lambda x: x["send_at"])
    return out


def create_announcement(guild_id, channel_id, channel_name, message, send_at):
    """send_at: unix timestamp (seconds)."""
    global _announce_seq
    _announce_seq += 1
    aid = f"ann_{_announce_seq}"
    _announcements[aid] = {
        "guild_id": str(guild_id),
        "channel_id": str(channel_id),
        "channel_name": channel_name,
        "message": message,
        "send_at": float(send_at),
        "sent": False,
    }
    add_log("INFO", f"Announcement scheduled for {channel_name}")
    return aid


def delete_announcement(aid):
    if aid in _announcements:
        del _announcements[aid]
        return {"ok": True}
    return {"ok": False, "error": "Announcement not found"}


async def _check_announcements():
    """Background: send due announcements. Called periodically."""
    import discord as _discord
    now = _time.time()
    due = [(aid, a) for aid, a in _announcements.items() if not a["sent"] and a["send_at"] <= now]
    for aid, a in due:
        if bot is None:
            continue
        guild = bot.get_guild(int(a["guild_id"]))
        if not guild:
            continue
        channel = guild.get_channel(int(a["channel_id"]))
        if channel:
            try:
                embed = _discord.Embed(
                    title="📢 Announcement",
                    description=a["message"],
                    color=0x5865F2,
                    timestamp=datetime.now(timezone.utc),
                )
                embed.set_footer(text="Mangoli Bot • Scheduled Announcement")
                await channel.send(embed=embed)
            except Exception as e:
                add_log("ERROR", f"Announcement send failed: {e}")
        a["sent"] = True
    # cleanup old sent announcements (keep last 100)
    sent = [aid for aid, a in _announcements.items() if a["sent"]]
    for aid in sent[:-100]:
        _announcements.pop(aid, None)


def get_due_announcements_now():
    """Non-async helper: returns due announcements for the loop."""
    now = _time.time()
    return [(aid, a) for aid, a in _announcements.items() if not a["sent"] and a["send_at"] <= now]


# ═══════════════════════════════════════════════════════════════════════════════
# MEMBER MANAGEMENT (dashboard)
# ═══════════════════════════════════════════════════════════════════════════════

def get_roles(guild_id):
    if bot is None:
        return []
    guild = bot.get_guild(int(guild_id))
    if not guild:
        return []
    out = []
    for r in guild.roles:
        if r.name == "@everyone":
            continue
        out.append({"id": str(r.id), "name": r.name, "color": str(r.color), "position": r.position})
    out.sort(key=lambda x: -x["position"])
    return out


async def _role_action(guild_id, user_id, role_id, action):
    guild = bot.get_guild(int(guild_id))
    if not guild:
        return {"ok": False, "error": "Guild not found"}
    member = guild.get_member(int(user_id))
    if not member:
        return {"ok": False, "error": "Member not found"}
    role = guild.get_role(int(role_id))
    if not role:
        return {"ok": False, "error": "Role not found"}

    try:
        if action == 'add':
            await member.add_roles(role, reason="Added from dashboard")
            msg = f"Added role {role.name}"
        elif action == 'remove':
            await member.remove_roles(role, reason="Removed from dashboard")
            msg = f"Removed role {role.name}"
        else:
            return {"ok": False, "error": f"Unknown action '{action}'"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

    add_log("INFO", f"Role {action}: {role.name} for {member.display_name}")
    return {"ok": True, "message": msg}


def role_action(guild_id, user_id, role_id, action):
    return run_on_loop(_role_action(guild_id, user_id, role_id, action))


# ═══════════════════════════════════════════════════════════════════════════════
# AUTO-RESPONDER (dashboard)
# ═══════════════════════════════════════════════════════════════════════════════

_autoresponders = {}  # guild_id -> {trigger: response}
_ar_seq = 0


def get_autoresponders(guild_id=None):
    if guild_id:
        return dict(_autoresponders.get(str(guild_id), {}))
    return dict(_autoresponders)


def add_autoresponder(guild_id, trigger, response):
    gid = str(guild_id)
    _autoresponders.setdefault(gid, {})[trigger.lower().strip()] = response.strip()
    add_log("INFO", f"Auto-responder added: '{trigger}'")
    return {"ok": True}


def remove_autoresponder(guild_id, trigger):
    gid = str(guild_id)
    if gid in _autoresponders and trigger in _autoresponders[gid]:
        del _autoresponders[gid][trigger]
        return {"ok": True}
    return {"ok": False, "error": "Trigger not found"}


def check_autoresponders(guild_id, message):
    """Return the matching response (or None) for a message."""
    gid = str(guild_id)
    text = message.lower()
    for trigger, response in _autoresponders.get(gid, {}).items():
        if trigger in text:
            return response
    return None


# ═══════════════════════════════════════════════════════════════════════════════
# WEBHOOK MANAGEMENT (dashboard)
# ═══════════════════════════════════════════════════════════════════════════════

async def _get_webhooks(guild_id):
    guild = bot.get_guild(int(guild_id))
    if not guild:
        return []
    out = []
    try:
        for wh in await guild.webhooks():
            out.append({
                "id": str(wh.id),
                "name": wh.name,
                "channel_id": str(wh.channel_id),
                "channel_name": wh.channel.name if wh.channel else "",
            })
    except Exception as e:
        return [{"error": str(e)}]
    return out


def get_webhooks(guild_id):
    return run_on_loop(_get_webhooks(guild_id), timeout=15)


async def _create_webhook(guild_id, channel_id, name):
    guild = bot.get_guild(int(guild_id))
    if not guild:
        return {"ok": False, "error": "Guild not found"}
    channel = guild.get_channel(int(channel_id))
    if not channel:
        return {"ok": False, "error": "Channel not found"}
    try:
        wh = await channel.create_webhook(name=name or "Mangoli Webhook")
        return {"ok": True, "id": str(wh.id), "url": wh.url}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def create_webhook(guild_id, channel_id, name):
    return run_on_loop(_create_webhook(guild_id, channel_id, name), timeout=15)


async def _delete_webhook(guild_id, webhook_id):
    guild = bot.get_guild(int(guild_id))
    if not guild:
        return {"ok": False, "error": "Guild not found"}
    try:
        for wh in await guild.webhooks():
            if str(wh.id) == str(webhook_id):
                await wh.delete()
                return {"ok": True}
        return {"ok": False, "error": "Webhook not found"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def delete_webhook(guild_id, webhook_id):
    return run_on_loop(_delete_webhook(guild_id, webhook_id), timeout=15)


print("[ControlBridge] Control bridge loaded")
