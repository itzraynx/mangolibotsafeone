"""
═══════════════════════════════════════════════════════════════════════════════
LEVEL SYSTEM
XP, levels, ranks, invite tracking & leaderboards for the Novagen bot.
by Nokiatis Community
═══════════════════════════════════════════════════════════════════════════════

XP sources:
  • Chat  — random 15–25 XP per message (60s cooldown to stop spam)
  • Voice — 5 XP / minute, +3 bonus / minute when in a channel with others
  • Invites — 50 XP per real invite
  • Daily — /daily gives a once-per-day bonus

Level curve:  xp_required(level) = 5·level² + 50·level + 100
(level 0→1 = 100 XP, 1→2 = 155, 2→3 = 220, …)

All data is persisted to levels_data.json next to this file.
"""

import json
import os
import threading
import time
from datetime import datetime

DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'levels_data.json')

_lock = threading.Lock()

DEFAULT_SETTINGS = {
    "level_up_channel": 1538702988821139547,   # where level-up cards are posted
    "message_xp_min": 15,
    "message_xp_max": 25,
    "message_cooldown": 60,                    # seconds between message XP
    "message_min_length": 3,                   # min chars for a message to count (anti-spam)
    "voice_xp_per_minute": 5,
    "voice_bonus_with_others": 3,
    "invite_xp": 50,
    "daily_xp": 100,
    # Optional role rewards: level -> role name to auto-assign (best effort)
    "role_rewards": {},
}


def _default_user():
    return {
        "xp": 0,
        "messages": 0,
        "voice_minutes": 0,
        "invites": 0,
        "last_message_xp": 0,
        "last_daily": "",
        "joined_at": datetime.now().isoformat(),
        "streak": 0,             # consecutive days with activity
        "last_active_day": "",
        "weekly_xp": 0,          # XP this week
        "week_key": "",
        "achievements": {},      # id -> unlocked timestamp
    }


# ── Achievements ──────────────────────────────────────────────────────────────

ACHIEVEMENTS = {
    "first_steps":   {"name": "First Steps", "emoji": "🐣", "desc": "Send your first message"},
    "chatterbox":    {"name": "Chatterbox", "emoji": "💬", "desc": "Send 100 messages"},
    "socialite":     {"name": "Socialite", "emoji": "🗣️", "desc": "Send 500 messages"},
    "voice_newbie":  {"name": "Voice Newbie", "emoji": "🎙️", "desc": "Spend 60 minutes in voice"},
    "voice_addict":  {"name": "Voice Addict", "emoji": "🔊", "desc": "Spend 10 hours in voice"},
    "recruiter":     {"name": "Recruiter", "emoji": "📨", "desc": "Invite 1 member"},
    "talent_scout":  {"name": "Talent Scout", "emoji": "🌟", "desc": "Invite 5 members"},
    "level_5":       {"name": "Rising Star", "emoji": "⭐", "desc": "Reach level 5"},
    "level_10":      {"name": "Veteran", "emoji": "🏅", "desc": "Reach level 10"},
    "level_25":      {"name": "Legend", "emoji": "👑", "desc": "Reach level 25"},
    "streak_3":      {"name": "On Fire", "emoji": "🔥", "desc": "3-day activity streak"},
    "streak_7":      {"name": "Unstoppable", "emoji": "🚀", "desc": "7-day activity streak"},
}


def _check_achievements(u, level, streak):
    """Unlock any achievements the user now qualifies for. Returns list of new unlocks."""
    unlocked = u.setdefault("achievements", {})
    now = datetime.now().isoformat()
    new = []
    conds = {
        "first_steps": u.get("messages", 0) >= 1,
        "chatterbox": u.get("messages", 0) >= 100,
        "socialite": u.get("messages", 0) >= 500,
        "voice_newbie": u.get("voice_minutes", 0) >= 60,
        "voice_addict": u.get("voice_minutes", 0) >= 600,
        "recruiter": u.get("invites", 0) >= 1,
        "talent_scout": u.get("invites", 0) >= 5,
        "level_5": level >= 5,
        "level_10": level >= 10,
        "level_25": level >= 25,
        "streak_3": streak >= 3,
        "streak_7": streak >= 7,
    }
    for aid, met in conds.items():
        if met and aid not in unlocked:
            unlocked[aid] = now
            new.append(aid)
    return new


def unlocked_achievements(user_data):
    """List of achievement dicts the user has unlocked."""
    unlocked = user_data.get("achievements", {})
    return [ACHIEVEMENTS[k] for k in ACHIEVEMENTS if k in unlocked]


def _default_guild():
    return {
        "users": {},
        "invites": {},        # code -> {"uses": int, "inviter_id": str}
        "settings": dict(DEFAULT_SETTINGS),
    }


def load():
    with _lock:
        try:
            if os.path.exists(DATA_FILE):
                with open(DATA_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception:
            pass
        return {"guilds": {}}


def save(data):
    with _lock:
        try:
            with open(DATA_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"[Levels] save error: {e}")


def get_guild(data, guild_id, create=True):
    gid = str(guild_id)
    if gid not in data.setdefault("guilds", {}):
        if not create:
            return None
        data["guilds"][gid] = _default_guild()
    return data["guilds"][gid]


def get_user(data, guild_id, user_id, create=True):
    g = get_guild(data, guild_id, create=create)
    if g is None:
        return None
    uid = str(user_id)
    if uid not in g["users"]:
        if not create:
            return None
        g["users"][uid] = _default_user()
    return g["users"][uid]


def get_settings(guild_id):
    data = load()
    g = get_guild(data, guild_id, create=True)
    return g["settings"]


# ── XP math ───────────────────────────────────────────────────────────────────

def xp_required(level):
    """XP needed to go from `level` to `level + 1`."""
    return 5 * (level ** 2) + 50 * level + 100


def level_from_xp(xp):
    """Highest level reached with the given total XP (O(level) — fine for sane values)."""
    level = 0
    spent = 0
    while True:
        need = xp_required(level)
        if xp < spent + need:
            return level
        spent += need
        level += 1


def level_progress(xp):
    """(level, xp_into_level, xp_needed_for_next) for a progress bar."""
    level = level_from_xp(xp)
    spent = 0
    for l in range(level):
        spent += xp_required(l)
    cur = xp - spent
    need = xp_required(level)
    return level, cur, need


def level_emoji(level):
    """A rank emoji that scales with level, for nicer cards."""
    if level >= 50:
        return "👑"
    if level >= 25:
        return "💎"
    if level >= 15:
        return "🏅"
    if level >= 10:
        return "🥇"
    if level >= 5:
        return "🥈"
    if level >= 3:
        return "🥉"
    if level >= 1:
        return "⭐"
    return "🌱"


# ── XP grants ─────────────────────────────────────────────────────────────────

def _week_key():
    """ISO year-week string, used to reset weekly XP on a new week."""
    d = datetime.now()
    return f"{d.isocalendar()[0]}-W{d.isocalendar()[1]}"


def add_xp(guild_id, user_id, amount, source="misc"):
    """Add XP. Returns (old_level, new_level, leveled_up, xp, new_achievements)."""
    data = load()
    u = get_user(data, guild_id, user_id, create=True)

    # streak tracking (activity = message/voice/daily)
    today = datetime.now().strftime("%Y-%m-%d")
    if u.get("last_active_day") != today:
        yesterday = (datetime.fromordinal(datetime.now().toordinal() - 1)).strftime("%Y-%m-%d")
        if u.get("last_active_day") == yesterday:
            u["streak"] = u.get("streak", 0) + 1
        else:
            u["streak"] = 1
        u["last_active_day"] = today

    # weekly XP (reset on new week)
    wk = _week_key()
    if u.get("week_key") != wk:
        u["week_key"] = wk
        u["weekly_xp"] = 0
    u["weekly_xp"] = u.get("weekly_xp", 0) + amount

    old_level = level_from_xp(u["xp"])
    u["xp"] = u.get("xp", 0) + amount

    if source == "message":
        u["messages"] = u.get("messages", 0) + 1
    elif source == "voice":
        u["voice_minutes"] = u.get("voice_minutes", 0) + 1
    elif source == "invite":
        u["invites"] = u.get("invites", 0) + 1

    new_level = level_from_xp(u["xp"])
    leveled_up = new_level > old_level

    # achievements
    new_achievements = _check_achievements(u, new_level, u.get("streak", 0))

    save(data)
    return old_level, new_level, leveled_up, u["xp"], new_achievements


def message_xp_allowed(guild_id, user_id):
    """Cooldown check — returns True if this message can grant XP."""
    data = load()
    u = get_user(data, guild_id, user_id, create=True)
    cfg = get_settings(guild_id)
    cooldown = cfg.get("message_cooldown", 60)
    last = u.get("last_message_xp", 0)
    if time.time() - last >= cooldown:
        u["last_message_xp"] = time.time()
        save(data)
        return True
    return False


def daily_claim(guild_id, user_id):
    """Try to claim the daily bonus. Returns (ok, xp_granted, message, new_achievements)."""
    data = load()
    u = get_user(data, guild_id, user_id, create=True)
    today = datetime.now().strftime("%Y-%m-%d")
    if u.get("last_daily") == today:
        return False, 0, "already claimed", []

    # streak: claiming daily counts as activity
    if u.get("last_active_day") != today:
        yesterday = (datetime.fromordinal(datetime.now().toordinal() - 1)).strftime("%Y-%m-%d")
        u["streak"] = (u.get("streak", 0) + 1) if u.get("last_active_day") == yesterday else 1
        u["last_active_day"] = today

    amount = get_settings(guild_id).get("daily_xp", 100)
    u["last_daily"] = today
    u["xp"] = u.get("xp", 0) + amount
    # weekly XP
    wk = _week_key()
    if u.get("week_key") != wk:
        u["week_key"] = wk
        u["weekly_xp"] = 0
    u["weekly_xp"] = u.get("weekly_xp", 0) + amount

    # achievements (streak unlocks via daily too)
    new_achievements = _check_achievements(u, level_from_xp(u["xp"]), u.get("streak", 0))

    save(data)
    return True, amount, "ok", new_achievements


def get_weekly_leaderboard(guild_id):
    """[(user_id, weekly_xp)] sorted desc for the current week."""
    data = load()
    g = get_guild(data, guild_id, create=False)
    if g is None:
        return []
    wk = _week_key()
    board = []
    for uid, u in g["users"].items():
        if u.get("week_key") == wk:
            board.append((uid, u.get("weekly_xp", 0)))
    board.sort(key=lambda t: -t[1])
    return board


# ── Invite tracking ───────────────────────────────────────────────────────────

def cache_invites(guild_id, invites):
    """Store {code: {uses, inviter_id}} for a guild (called on_ready + on_invite_create)."""
    data = load()
    g = get_guild(data, guild_id, create=True)
    for inv in invites:
        code = inv.code
        g["invites"][code] = {
            "uses": inv.uses or 0,
            "inviter_id": str(inv.inviter.id) if inv.inviter else None,
        }
    save(data)


def find_used_invite(guild_id, fresh_invites):
    """Compare fresh invites to the cache; return the invite whose uses grew."""
    data = load()
    g = get_guild(data, guild_id, create=True)
    cached = g["invites"]
    for inv in fresh_invites:
        code = inv.code
        old_uses = cached.get(code, {}).get("uses", 0)
        if inv.uses and inv.uses > old_uses:
            cached[code] = {"uses": inv.uses, "inviter_id": str(inv.inviter.id) if inv.inviter else None}
            save(data)
            return inv
    return None


# ── Leaderboard / profile ─────────────────────────────────────────────────────

def get_user_stats(guild_id, user_id):
    data = load()
    u = get_user(data, guild_id, user_id, create=False)
    if u is None:
        return None
    xp = u.get("xp", 0)
    level, cur, need = level_progress(xp)
    return {
        "xp": xp,
        "level": level,
        "xp_into_level": cur,
        "xp_needed": need,
        "progress": round(cur / need * 100, 1) if need else 100,
        "messages": u.get("messages", 0),
        "voice_minutes": u.get("voice_minutes", 0),
        "invites": u.get("invites", 0),
        "streak": u.get("streak", 0),
        "weekly_xp": u.get("weekly_xp", 0),
        "achievements": [ACHIEVEMENTS[k] for k in u.get("achievements", {}) if k in ACHIEVEMENTS],
    }


def get_leaderboard(guild_id):
    """[(user_id, stats)] sorted by XP desc."""
    data = load()
    g = get_guild(data, guild_id, create=False)
    if g is None:
        return []
    board = []
    for uid, u in g["users"].items():
        xp = u.get("xp", 0)
        level, cur, need = level_progress(xp)
        board.append((uid, {
            "xp": xp,
            "level": level,
            "xp_into_level": cur,
            "xp_needed": need,
            "progress": round(cur / need * 100, 1) if need else 100,
            "messages": u.get("messages", 0),
            "voice_minutes": u.get("voice_minutes", 0),
            "invites": u.get("invites", 0),
            "streak": u.get("streak", 0),
            "weekly_xp": u.get("weekly_xp", 0),
        }))
    board.sort(key=lambda t: -t[1]["xp"])
    return board


def get_rank(guild_id, user_id):
    board = get_leaderboard(guild_id)
    for i, (uid, _) in enumerate(board):
        if uid == str(user_id):
            return i + 1
    return None


print("[Levels] Level system loaded")
