"""
═══════════════════════════════════════════════════════════════════════════════
MUSIC SYSTEM — Mangoli Bot
High-quality music playback via Lavalink (wavelink).
by Nokiatis Community
═══════════════════════════════════════════════════════════════════════════════

⚠️  IMPORTANT — Music requires a running LAVALINK server (a separate Java
    program that streams audio). Configure it below, then start Lavalink on
    the same host.

    Lavalink (free, open source):  https://github.com/lavalink-devs/Lavalink
    Download the jar, run it with a config, and put its address below.

Commands:
  /join  /leave  /play  /pause  /resume  /skip  /stop  /nowplaying
  /queue  /volume  /loop  /shuffle  /seek  /autoplay  /lyrics

Supported sources (via Lavalink): YouTube, YouTube Music, SoundCloud,
Spotify (needs Spotify app credentials in Lavalink), Deezer, Apple Music…
"""

import asyncio
import re
from datetime import timedelta

import discord
from discord import app_commands

try:
    import wavelink
    WAVELINK_AVAILABLE = True
except ImportError:
    wavelink = None
    WAVELINK_AVAILABLE = False

# ── CONFIGURATION ──────────────────────────────────────────────────────────────
# Edit these to point at your Lavalink server.
# (Free public node provided by zyphron.cloud)
#
# NOTE: wavelink automatically appends /v4/websocket to this base URI.
LAVALINK_URI = "ws://intel-node1.zyphron.cloud:10023"     # Lavalink address
LAVALINK_PASSWORD = "zyph"                                 # Lavalink password
LAVALINK_SECURE = False                                    # set True if using wss://

# ── Branding ───────────────────────────────────────────────────────────────────
BRAND = "Mangoli Bot"
ICON = "https://i.imgur.com/7ZGzqjY.png"
FOOTER = f"⚡ {BRAND} • by Nokiatis Community"
PRIMARY = 0x5865F2
SUCCESS = 0x57F287
ERROR = 0xED4245
GOLD = 0xFBBF24


# ── Helpers ────────────────────────────────────────────────────────────────────

def fmt_duration(ms):
    if not ms or ms < 0:
        return "0:00"
    td = timedelta(milliseconds=ms)
    total = int(td.total_seconds())
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def progress_bar(pos, length, width=18):
    if not length:
        return "▰" * width
    filled = int(width * (pos / length))
    filled = max(0, min(width, filled))
    return "▰" * filled + "▱" * (width - filled)


def _player(interaction):
    """Get (player, error) for the interaction's guild."""
    if not WAVELINK_AVAILABLE:
        return None, ("Music is not available — `wavelink` is not installed.\n"
                      "Fix: run `pip install wavelink` on your host, then restart the bot.")
    if not wavelink.Pool.nodes:
        return None, ("Lavalink is not connected.\n"
                      "Possible causes:\n"
                      "• The free Lavalink node is down\n"
                      "• Your host blocks outbound WebSocket (port 10023)\n"
                      "Check the console for '[Music] Lavalink' messages.")
    node = wavelink.Pool.get_node()
    player = node.get_player(interaction.guild.id)
    return player, None


def _in_voice(interaction):
    if not interaction.user.voice or not interaction.user.voice.channel:
        return None
    return interaction.user.voice.channel


def nowplaying_embed(player):
    track = player.current
    if not track:
        return None
    bar = progress_bar(player.position, track.length)
    embed = discord.Embed(
        description=(
            f"# 🎵 Now Playing\n"
            f"### [{track.title}]({track.uri})\n"
            f"**Artist:** {track.author or track.artist or 'Unknown'}\n\n"
            f"{bar}\n"
            f"`{fmt_duration(player.position)}` / `{fmt_duration(track.length)}`"
        ),
        color=PRIMARY,
    )
    if track.artwork:
        embed.set_thumbnail(url=track.artwork)
    embed.add_field(name="🔊 Volume", value=f"`{player.volume}%`", inline=True)
    embed.add_field(name="🔁 Loop", value=f"`{player.queue.mode.name}`", inline=True)
    embed.set_footer(text=FOOTER, icon_url=ICON)
    return embed


# ── Registration ───────────────────────────────────────────────────────────────

def register(bot):
    """Register music commands + wavelink listeners."""

    @bot.tree.command(name="join", description="🎵 Join your voice channel")
    async def join(interaction: discord.Interaction):
        if not WAVELINK_AVAILABLE:
            return await interaction.response.send_message("❌ Music is not available (wavelink not installed).", ephemeral=True)
        vc = _in_voice(interaction)
        if not vc:
            return await interaction.response.send_message("❌ Join a voice channel first.", ephemeral=True)
        try:
            player = await vc.connect(cls=wavelink.Player, self_deaf=True)
        except Exception as e:
            return await interaction.response.send_message(f"❌ Could not join: {e}", ephemeral=True)
        await interaction.response.send_message(embed=discord.Embed(
            description=f"# 🎵 Joined {vc.mention}", color=SUCCESS))

    @bot.tree.command(name="leave", description="🔇 Leave the voice channel")
    async def leave(interaction: discord.Interaction):
        player, err = _player(interaction)
        if not player:
            return await interaction.response.send_message(f"❌ {err}", ephemeral=True)
        await player.disconnect()
        await interaction.response.send_message(embed=discord.Embed(
            description="# 👋 Disconnected", color=SUCCESS))

    @bot.tree.command(name="play", description="▶️ Play a song (name or URL)")
    @app_commands.describe(query="Song name, YouTube/Spotify/Deezer link, or playlist")
    async def play(interaction: discord.Interaction, query: str):
        if not WAVELINK_AVAILABLE:
            return await interaction.response.send_message("❌ Music is not available (wavelink not installed).", ephemeral=True)
        vc = _in_voice(interaction)
        if not vc:
            return await interaction.response.send_message("❌ Join a voice channel first.", ephemeral=True)
        if not wavelink.Pool.nodes:
            return await interaction.response.send_message("❌ Lavalink is not connected.", ephemeral=True)

        await interaction.response.defer()
        node = wavelink.Pool.get_node()
        player = node.get_player(interaction.guild.id)
        if not player:
            try:
                player = await vc.connect(cls=wavelink.Player, self_deaf=True)
            except Exception as e:
                return await interaction.followup.send(f"❌ Could not join: {e}", ephemeral=True)

        try:
            search = await wavelink.Playable.search(query)
        except Exception as e:
            return await interaction.followup.send(f"❌ Search failed: {e}", ephemeral=True)

        if not search:
            return await interaction.followup.send("❌ No results found.", ephemeral=True)

        # Playlist vs single track
        if isinstance(search[0], wavelink.Playlist):
            playlist = search[0]
            added = 0
            for track in playlist.tracks:
                player.queue.put(track)
                added += 1
            embed = discord.Embed(
                description=f"# 📚 Playlist Added\n### {playlist.name}\n`{added}` tracks added to the queue.",
                color=SUCCESS)
            if not player.playing:
                await player.play(player.queue.get())
        else:
            track = search[0]
            if player.playing:
                player.queue.put(track)
                embed = discord.Embed(
                    description=f"# ➕ Added to Queue\n### [{track.title}]({track.uri})\n`{fmt_duration(track.length)}`",
                    color=SUCCESS)
            else:
                await player.play(track)
                embed = nowplaying_embed(player)
        embed.set_footer(text=FOOTER, icon_url=ICON)
        await interaction.followup.send(embed=embed)

    @bot.tree.command(name="pause", description="⏸️ Pause playback")
    async def pause(interaction: discord.Interaction):
        player, err = _player(interaction)
        if not player or not player.playing:
            return await interaction.response.send_message("❌ Nothing is playing.", ephemeral=True)
        await player.pause(True)
        await interaction.response.send_message(embed=discord.Embed(
            description="# ⏸️ Paused", color=GOLD))

    @bot.tree.command(name="resume", description="▶️ Resume playback")
    async def resume(interaction: discord.Interaction):
        player, err = _player(interaction)
        if not player:
            return await interaction.response.send_message(f"❌ {err}", ephemeral=True)
        await player.pause(False)
        await interaction.response.send_message(embed=discord.Embed(
            description="# ▶️ Resumed", color=SUCCESS))

    @bot.tree.command(name="skip", description="⏭️ Skip the current track")
    async def skip(interaction: discord.Interaction):
        player, err = _player(interaction)
        if not player or not player.playing:
            return await interaction.response.send_message("❌ Nothing is playing.", ephemeral=True)
        await player.skip()
        await interaction.response.send_message(embed=discord.Embed(
            description="# ⏭️ Skipped", color=SUCCESS))

    @bot.tree.command(name="stop", description="⏹️ Stop and clear the queue")
    async def stop(interaction: discord.Interaction):
        player, err = _player(interaction)
        if not player:
            return await interaction.response.send_message(f"❌ {err}", ephemeral=True)
        player.queue.clear()
        await player.stop()
        await interaction.response.send_message(embed=discord.Embed(
            description="# ⏹️ Stopped", color=SUCCESS))

    @bot.tree.command(name="nowplaying", description="🎵 Show the current track")
    async def nowplaying(interaction: discord.Interaction):
        player, err = _player(interaction)
        if not player or not player.current:
            return await interaction.response.send_message("❌ Nothing is playing.", ephemeral=True)
        embed = nowplaying_embed(player)
        await interaction.response.send_message(embed=embed)

    @bot.tree.command(name="queue", description="📃 Show the queue")
    async def queue(interaction: discord.Interaction):
        player, err = _player(interaction)
        if not player:
            return await interaction.response.send_message(f"❌ {err}", ephemeral=True)
        q = list(player.queue)
        if not q and not player.current:
            return await interaction.response.send_message("❌ The queue is empty.", ephemeral=True)
        lines = []
        if player.current:
            lines.append(f"**▶️ Now:** {player.current.title}")
        for i, track in enumerate(q[:15], start=1):
            lines.append(f"`{i}.` {track.title} · `{fmt_duration(track.length)}`")
        if len(q) > 15:
            lines.append(f"…and `{len(q) - 15}` more")
        embed = discord.Embed(
            description=f"# 📃 Queue\n" + "\n".join(lines),
            color=PRIMARY)
        embed.set_footer(text=FOOTER, icon_url=ICON)
        await interaction.response.send_message(embed=embed)

    @bot.tree.command(name="volume", description="🔊 Set the volume (0-200)")
    @app_commands.describe(level="Volume level (default 100)")
    async def volume(interaction: discord.Interaction, level: int):
        player, err = _player(interaction)
        if not player:
            return await interaction.response.send_message(f"❌ {err}", ephemeral=True)
        level = max(0, min(200, level))
        await player.set_volume(level)
        await interaction.response.send_message(embed=discord.Embed(
            description=f"# 🔊 Volume\n### `{level}%`", color=SUCCESS))

    @bot.tree.command(name="loop", description="🔁 Set loop mode")
    @app_commands.choices(mode=[
        app_commands.Choice(name="Off", value="normal"),
        app_commands.Choice(name="Track", value="loop"),
        app_commands.Choice(name="Queue", value="loop_all"),
    ])
    async def loop(interaction: discord.Interaction, mode: str):
        player, err = _player(interaction)
        if not player:
            return await interaction.response.send_message(f"❌ {err}", ephemeral=True)
        player.queue.mode = wavelink.QueueMode[mode]
        await interaction.response.send_message(embed=discord.Embed(
            description=f"# 🔁 Loop Mode\n### `{player.queue.mode.name}`", color=SUCCESS))

    @bot.tree.command(name="shuffle", description="🔀 Shuffle the queue")
    async def shuffle(interaction: discord.Interaction):
        player, err = _player(interaction)
        if not player:
            return await interaction.response.send_message(f"❌ {err}", ephemeral=True)
        player.queue.shuffle()
        await interaction.response.send_message(embed=discord.Embed(
            description="# 🔀 Queue Shuffled", color=SUCCESS))

    @bot.tree.command(name="seek", description="⏩ Seek to a position (seconds)")
    @app_commands.describe(seconds="Position in seconds")
    async def seek(interaction: discord.Interaction, seconds: int):
        player, err = _player(interaction)
        if not player or not player.current:
            return await interaction.response.send_message("❌ Nothing is playing.", ephemeral=True)
        await player.seek(seconds * 1000)
        await interaction.response.send_message(embed=discord.Embed(
            description=f"# ⏩ Seeked to `{fmt_duration(seconds * 1000)}`", color=SUCCESS))

    @bot.tree.command(name="autoplay", description="🔁 Toggle autoplay (related songs)")
    async def autoplay(interaction: discord.Interaction):
        player, err = _player(interaction)
        if not player:
            return await interaction.response.send_message(f"❌ {err}", ephemeral=True)
        if player.autoplay is wavelink.AutoPlayMode.enabled:
            player.autoplay = wavelink.AutoPlayMode.disabled
            state = "Disabled"
        else:
            player.autoplay = wavelink.AutoPlayMode.enabled
            state = "Enabled"
        await interaction.response.send_message(embed=discord.Embed(
            description=f"# 🔁 Autoplay\n### `{state}`", color=SUCCESS))

    @bot.tree.command(name="lyrics", description="📝 Get lyrics for a song")
    @app_commands.describe(query="Song name (defaults to the current track)")
    async def lyrics(interaction: discord.Interaction, query: str = None):
        if not query:
            player, err = _player(interaction)
            if player and player.current:
                track = player.current
                query = f"{track.title} {track.author or ''}"
            else:
                return await interaction.response.send_message("❌ Provide a song name or play something first.", ephemeral=True)
        await interaction.response.defer()
        import aiohttp
        import urllib.parse

        lyrics_text = None
        try:
            async with aiohttp.ClientSession() as s:
                # Primary: LRCLIB (free, reliable, synced lyrics)
                q = urllib.parse.quote(query)
                async with s.get(
                    f"https://lrclib.net/api/search?q={q}",
                    headers={"User-Agent": "MangoliBot/2.0"},
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as r:
                    if r.status == 200:
                        results = await r.json()
                        if results:
                            item = results[0]
                            lyrics_text = item.get("syncedLyrics") or item.get("plainLyrics")
                # Fallback: lyrics.ovh (artist/title endpoint)
                if not lyrics_text:
                    async with s.get(f"https://api.lyrics.ovh/v1/{q}", timeout=aiohttp.ClientTimeout(total=15)) as r2:
                        if r2.status == 200:
                            data = await r2.json()
                            lyrics_text = data.get("lyrics")
        except Exception as e:
            print(f"[Music] lyrics error: {e}")

        if not lyrics_text:
            return await interaction.followup.send(
                "❌ Lyrics not found for that song. Try:\n"
                "• `/lyrics <artist> - <song name>` (e.g. `/lyrics Rick Astley - Never Gonna Give You Up`)\n"
                "• Or play the song first, then run `/lyrics` with no argument.",
                ephemeral=True,
            )

        # trim to embed-safe size (Discord caps description at 4096 chars)
        if len(lyrics_text) > 4000:
            lyrics_text = lyrics_text[:4000] + "\n…"

        embed = discord.Embed(
            description=f"# 📝 Lyrics\n### {query[:80]}\n\n{lyrics_text}",
            color=PRIMARY,
        )
        embed.set_footer(text=FOOTER, icon_url=ICON)
        await interaction.followup.send(embed=embed)

    # ── Wavelink event listeners (dispatched as on_wavelink_<event>) ─────────
    if WAVELINK_AVAILABLE:
        @bot.listen("on_wavelink_track_start")
        async def on_track_start(payload):
            player = payload.player
            track = payload.track
            if not track or not getattr(player, "guild", None):
                return
            home = getattr(bot, "_music_text_channel", None)
            channel = player.guild.get_channel(home) if home else None
            if channel is None:
                return
            embed = nowplaying_embed(player)
            if embed:
                try:
                    await channel.send(embed=embed)
                except Exception:
                    pass

    print("[Music] Music module loaded" + ("" if WAVELINK_AVAILABLE else " (wavelink NOT installed)"))


async def start(bot):
    """Connect to Lavalink (call from setup_hook). With auto-retry."""
    if not WAVELINK_AVAILABLE:
        print("[Music] ⚠️ wavelink is NOT installed — /play will not work.")
        print("[Music]    Fix: run `pip install wavelink` on your host.")
        return

    uri = LAVALINK_URI
    if LAVALINK_SECURE and not uri.startswith("wss://"):
        uri = uri.replace("http://", "wss://").replace("ws://", "wss://")

    # Try to connect a few times (node might be slow/busy on shared hosting)
    for attempt in range(1, 4):
        try:
            await wavelink.Pool.connect(
                nodes=[wavelink.Node(uri=uri, password=LAVALINK_PASSWORD)],
                client=bot,
            )
            print(f"[Music] ✅ Lavalink connected (attempt {attempt}).")
            return
        except Exception as e:
            print(f"[Music] ⚠️ Lavalink connection attempt {attempt} failed: {e}")
            if attempt < 3:
                await asyncio.sleep(3)

    print("[Music] ❌ Lavalink could NOT connect after 3 attempts.")
    print(f"[Music]    Node: {LAVALINK_URI}")
    print("[Music]    This is usually because:")
    print("[Music]    1. The free Lavalink node is down/offline")
    print("[Music]    2. Your host BLOCKS outbound WebSocket on port 10023")
    print("[Music]    Music commands will show 'Lavalink is not connected.'")
