"""
═══════════════════════════════════════════════════════════════════════════════
CUSTOM EMOJIS — Mangoli Bot
═══════════════════════════════════════════════════════════════════════════════

Uses the SAME emoji names as the Titan X ticket bot. When you upload emojis
with these names to your server, the bot looks them up BY NAME automatically
(IDs differ per server, so name-lookup is the correct approach).

The hardcoded IDs below are the original Titan X IDs — they act as a reference
and are replaced at runtime by the real IDs found in your guild.
"""

import discord

# Titan X emoji name -> original ID (reference; real IDs resolved at runtime)
TITAN_EMOJIS = {
    "ticket":     "1535619183277113375",
    "claim":      "1535619248599339019",
    "lock":       "1535619217397784658",
    "unlock":     "1535619172048969828",
    "trash":      "1535619177602220042",
    "add":        "1535619242781712406",
    "remove":     "1535619205922299966",
    "transcript": "1535619254236225547",
    "reopen":     "1536046619869585458",
    "cross":      "1535619229749878825",   # the "X" emoji is named "cross" in the guild
    "check":      "1535619236435857438",
    "starFill":   "1535619188767588443",
    "starEmpty":  "1535619193867731045",
    "settings":   "1535619200142549012",
    "dashboard":  "1535619223995420672",
    "logs":       "1535619211747926076",
    "timer":      "1535619260024496128",
    "mail":       "1536046625623900340",
}

# Semantic name (used by our code) -> Titan X emoji name
SEMANTIC = {
    "ticket":     "ticket",
    "claim":      "claim",
    "close":      "lock",       # the "close ticket" button uses the lock emoji
    "lock":       "lock",
    "reopen":     "reopen",
    "unlock":     "unlock",
    "delete":     "trash",
    "trash":      "trash",
    "add":        "add",
    "remove":     "remove",
    "transcript": "transcript",
    "check":      "check",
    "success":    "check",
    "cross":      "cross",
    "error":      "cross",
    "star_fill":  "starFill",
    "star_empty": "starEmpty",
    "settings":   "settings",
    "dashboard":  "dashboard",
    "logs":       "logs",
    "timer":      "timer",
    "mail":       "mail",
}

# Unicode fallbacks for names without a Titan equivalent
FALLBACK = {
    "ticket": "🎫", "claim": "🙋", "close": "🔒", "reopen": "🔓",
    "transcript": "📄", "add": "➕", "remove": "➖", "delete": "🗑️",
    "ping": "🔔", "help": "❓", "tickethour": "🕒",
    "coin": "💰", "gem": "💎", "shop": "🛒", "gift": "🎁",
    "slot": "🎰", "coinflip": "🪙",
    "trophy": "🏆", "fire": "🔥", "star": "⭐", "crown": "👑",
    "levelup": "🎉", "medal": "🏅", "rocket": "🚀",
    "success": "✅", "error": "❌", "warning": "⚠️", "info": "ℹ️",
    "loading": "⏳",
    "music": "🎵", "play": "▶️", "pause": "⏸️", "skip": "⏭️",
    "stop": "⏹️", "volume": "🔊", "shuffle": "🔀", "loop": "🔁",
    "lyrics": "📝", "rps": "✊", "guess": "🔢", "eightball": "🎱",
    "stats": "📊", "profile": "👤", "poll": "📊", "server": "🖥️",
    "voice": "🎙️", "invite": "📨", "daily": "📅", "warning2": "🚨",
    "check": "✅", "cross": "❌", "star_fill": "⭐", "star_empty": "☆",
    "settings": "⚙️", "dashboard": "📊", "logs": "📃", "timer": "⏱️",
    "mail": "📧", "unlock": "🔓", "lock": "🔒", "trash": "🗑️",
}

# Runtime-resolved mapping: titan_emoji_name -> resolved emoji string
_resolved = {}


def refresh_from_guild(guild):
    """Look up the guild's emojis by name and cache their real <:name:id> strings."""
    global _resolved
    import logging
    log = logging.getLogger('Emojis')
    if not guild:
        return
    found = 0
    for name in TITAN_EMOJIS:
        emoji = discord.utils.get(guild.emojis, name=name)
        if emoji:
            _resolved[name] = str(emoji)
            found += 1
    log.info(f"Resolved {found} custom emojis from guild '{guild.name}'")


def _titan_name(semantic):
    return SEMANTIC.get(semantic, semantic)


def em(name):
    """Return the custom emoji string, or unicode fallback."""
    # 1. runtime-resolved from guild (real IDs)
    tn = _titan_name(name)
    if tn in _resolved:
        return _resolved[tn]
    # 2. hardcoded Titan ID reference (only works on the original server)
    if tn in TITAN_EMOJIS:
        return f"<:{tn}:{TITAN_EMOJIS[tn]}>"
    # 3. unicode fallback
    return FALLBACK.get(name, "")


def raw(name):
    """Return the unicode fallback character."""
    return FALLBACK.get(name, "")


def partial(name):
    """Return a discord.PartialEmoji (for buttons), or None."""
    tn = _titan_name(name)
    if tn in _resolved:
        # parse "<:name:id>" back to a PartialEmoji
        s = _resolved[tn]
        import re
        m = re.match(r"<a?:(\w+):(\d+)>", s)
        if m:
            return discord.PartialEmoji(name=m.group(1), id=int(m.group(2)), animated=(s.startswith("<a")))
    if tn in TITAN_EMOJIS:
        try:
            return discord.PartialEmoji(name=tn, id=int(TITAN_EMOJIS[tn]))
        except (ValueError, TypeError):
            return None
    return None


print("[Emojis] Custom emoji map loaded")
