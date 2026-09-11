"""
═══════════════════════════════════════════════════════════════════════════════
MANGOLI BOT DASHBOARD API
Web control panel backend for the Discord bot.
by Nokiatis Community
═══════════════════════════════════════════════════════════════════════════════

Serves the dashboard UI and a JSON API that lets you control the running bot:
status, voice (join / pause / resume / leave / play), logs, servers, commands,
and settings — all routed through control_bridge.
"""

from flask import Flask, jsonify, redirect, render_template, request, send_from_directory, session, url_for
from flask_cors import CORS
import os
import secrets
import threading
import time
from datetime import datetime

import control_bridge
import security

# ═══════════════════════════════════════════════════════════════════════════════
# APP SETUP
# ═══════════════════════════════════════════════════════════════════════════════

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__, static_folder='dashboard', template_folder='dashboard')
app = security.setup_security(app)

# CORS is restricted now: same-origin only (the dashboard is served by Flask).
# This prevents other websites from making cross-site requests to the API.
CORS(app, resources={r"/api/*": {"origins": []}})

# ═══════════════════════════════════════════════════════════════════════════════
# AUTHENTICATION (global protection)
# ═══════════════════════════════════════════════════════════════════════════════

# TEMP: dashboard protection toggle.
# Set to False to DISABLE the login wall (for testing). Keep the code intact.
SECURITY_ENABLED = True


@app.before_request
def enforce_security():
    # If protection is temporarily disabled, allow everything through.
    if not SECURITY_ENABLED:
        return None

    path = request.path

    # 1. Public paths (no auth needed)
    if path in ('/login', '/logout', '/api/health'):
        return None

    # 2. Static assets (CSS/JS/images) — needed to render the login page
    if path.startswith('/static') or path.endswith(('.css', '.js', '.png', '.jpg', '.jpeg', '.svg', '.ico', '.woff', '.woff2')):
        return None

    # 3. Everything else requires a valid session
    if not session.get('authenticated'):
        if path.startswith('/api/'):
            return jsonify({"ok": False, "error": "unauthorized", "login": True}), 401
        return redirect(url_for('login_page'))

    # 4. CSRF protection on state-changing API requests
    if request.method in ('POST', 'PUT', 'DELETE', 'PATCH') and path.startswith('/api/'):
        token = request.headers.get('X-CSRF-Token') or request.form.get('csrf_token')
        expected = session.get('csrf_token')
        if not token or not expected or not secrets.compare_digest(token, expected):
            return jsonify({"ok": False, "error": "invalid CSRF token"}), 403

    return None


@app.route('/login', methods=['GET'])
def login_page():
    return render_template('login.html')


@app.route('/login', methods=['POST'])
def login_submit():
    data = request.get_json(silent=True) or {}
    password = data.get('password', '')

    ip = security._client_ip()

    # Reject if this IP is locked out
    if security.is_locked_out(ip):
        return jsonify({"ok": False, "error": "Too many attempts. Try again in a few minutes."}), 429

    if security.verify_password(password):
        security.record_success(ip)
        session.clear()
        session['authenticated'] = True
        session['csrf_token'] = secrets.token_hex(16)
        session['session_id'] = secrets.token_hex(16)
        session.permanent = True
        security._sessions[session['session_id']] = time.time()
        return jsonify({"ok": True, "csrf_token": session['csrf_token']})

    fails, lockout = security.record_failure(ip)
    if lockout:
        return jsonify({"ok": False, "error": f"Too many failed attempts. Locked out for {lockout} seconds."}), 429
    remaining = security.MAX_ATTEMPTS - fails
    return jsonify({"ok": False, "error": f"Wrong password. {max(0, remaining)} attempts left."}), 401


@app.route('/logout', methods=['GET', 'POST'])
def logout():
    session.clear()
    return redirect(url_for('login_page'))


@app.route('/api/csrf', methods=['GET'])
def get_csrf():
    return jsonify({"csrf_token": session.get('csrf_token', '')})


# ═══════════════════════════════════════════════════════════════════════════════
# STATIC FILE ROUTES
# ═══════════════════════════════════════════════════════════════════════════════

@app.route('/')
def serve_dashboard():
    return send_from_directory('dashboard', 'index.html')


@app.route('/<path:filename>')
def serve_static(filename):
    return send_from_directory('dashboard', filename)


# ═══════════════════════════════════════════════════════════════════════════════
# API ROUTES
# ═══════════════════════════════════════════════════════════════════════════════

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
    })


@app.route('/api/status', methods=['GET'])
def api_status():
    return jsonify(control_bridge.get_status())


@app.route('/api/voice', methods=['GET'])
def api_voice_status():
    return jsonify({"connections": control_bridge.get_voice_status()})


@app.route('/api/voice/join', methods=['POST'])
def api_voice_join():
    data = request.get_json(silent=True) or {}
    guild_id = data.get("guild_id")
    channel_id = data.get("channel_id")
    if not guild_id or not channel_id:
        return jsonify({"ok": False, "error": "guild_id and channel_id are required"}), 400
    return jsonify(control_bridge.voice_join(guild_id, channel_id))


@app.route('/api/voice/leave', methods=['POST'])
def api_voice_leave():
    data = request.get_json(silent=True) or {}
    guild_id = data.get("guild_id")
    if not guild_id:
        return jsonify({"ok": False, "error": "guild_id is required"}), 400
    return jsonify(control_bridge.voice_leave(guild_id))


@app.route('/api/voice/pause', methods=['POST'])
def api_voice_pause():
    data = request.get_json(silent=True) or {}
    guild_id = data.get("guild_id")
    if not guild_id:
        return jsonify({"ok": False, "error": "guild_id is required"}), 400
    return jsonify(control_bridge.voice_pause(guild_id))


@app.route('/api/voice/resume', methods=['POST'])
def api_voice_resume():
    data = request.get_json(silent=True) or {}
    guild_id = data.get("guild_id")
    if not guild_id:
        return jsonify({"ok": False, "error": "guild_id is required"}), 400
    return jsonify(control_bridge.voice_resume(guild_id))


@app.route('/api/voice/play', methods=['POST'])
def api_voice_play():
    data = request.get_json(silent=True) or {}
    guild_id = data.get("guild_id")
    url = data.get("url")
    if not guild_id or not url:
        return jsonify({"ok": False, "error": "guild_id and url are required"}), 400
    return jsonify(control_bridge.voice_play(guild_id, url))


@app.route('/api/voice/tts', methods=['POST'])
def api_voice_tts():
    """Text-to-Speech: build a free Google Translate TTS URL and play it."""
    import urllib.parse
    data = request.get_json(silent=True) or {}
    guild_id = data.get("guild_id")
    text = (data.get("text") or "").strip()
    lang = data.get("lang") or "en"
    if not guild_id or not text:
        return jsonify({"ok": False, "error": "guild_id and text are required"}), 400
    if len(text) > 190:
        return jsonify({"ok": False, "error": "Text too long (max 190 characters)"}), 400

    # Free Google Translate TTS (no API key required)
    url = (
        "https://translate.google.com/translate_tts?ie=UTF-8&client=tw-ob"
        f"&q={urllib.parse.quote(text)}&tl={urllib.parse.quote(lang)}"
    )
    result = control_bridge.voice_play(guild_id, url)
    if result.get("ok"):
        control_bridge.add_log("INFO", f"TTS speaking ({lang}): {text[:60]}")
    return jsonify(result)


@app.route('/api/logs', methods=['GET'])
def api_logs():
    level = request.args.get('level', 'ALL')
    limit = request.args.get('limit', 200, type=int)
    return jsonify(control_bridge.get_logs(level=level, limit=limit))


@app.route('/api/logs/clear', methods=['POST'])
def api_logs_clear():
    control_bridge.clear_logs()
    return jsonify({"ok": True})


@app.route('/api/logs/export', methods=['GET'])
def api_logs_export():
    from flask import Response
    level = request.args.get('level', 'ALL')
    text = control_bridge.get_log_text(level=level)
    return Response(
        text,
        mimetype="text/plain",
        headers={"Content-Disposition": "attachment; filename=mangoli_logs.txt"},
    )


@app.route('/api/presence', methods=['POST'])
def api_presence():
    data = request.get_json(silent=True) or {}
    status = data.get("status", "online")
    activity_type = data.get("activity_type", "playing")
    text = data.get("text", "")
    stream_url = data.get("stream_url")
    result = control_bridge.set_presence(status, activity_type, text, stream_url)
    return jsonify(result)


@app.route('/api/commands/toggle', methods=['POST'])
def api_command_toggle():
    data = request.get_json(silent=True) or {}
    name = data.get("name")
    enabled = data.get("enabled")
    if not name:
        return jsonify({"ok": False, "error": "name is required"}), 400
    if enabled:
        return jsonify(control_bridge.enable_command(name))
    return jsonify(control_bridge.disable_command(name))


@app.route('/api/broadcast', methods=['POST'])
def api_broadcast():
    data = request.get_json(silent=True) or {}
    guild_id = data.get("guild_id")
    channel_id = data.get("channel_id")
    text = data.get("text")
    if not guild_id or not channel_id or not text:
        return jsonify({"ok": False, "error": "guild_id, channel_id and text are required"}), 400
    return jsonify(control_bridge.send_message(guild_id, channel_id, text))


@app.route('/api/voice/stop', methods=['POST'])
def api_voice_stop():
    data = request.get_json(silent=True) or {}
    guild_id = data.get("guild_id")
    if not guild_id:
        return jsonify({"ok": False, "error": "guild_id is required"}), 400
    return jsonify(control_bridge.voice_stop(guild_id))


@app.route('/api/sounds', methods=['GET'])
def api_sounds():
    return jsonify({"sounds": control_bridge.get_sound_library()})


@app.route('/api/system', methods=['GET'])
def api_system():
    return jsonify(control_bridge.get_system_info())


@app.route('/api/commands/stats/reset', methods=['POST'])
def api_command_stats_reset():
    control_bridge.reset_command_counts()
    return jsonify({"ok": True})


@app.route('/api/bot/shutdown', methods=['POST'])
def api_shutdown():
    return jsonify(control_bridge.shutdown_bot())


@app.route('/api/bot/restart', methods=['POST'])
def api_restart():
    return jsonify(control_bridge.restart_bot())


@app.route('/api/guilds', methods=['GET'])
def api_guilds():
    return jsonify({"guilds": control_bridge.get_guilds()})


@app.route('/api/levels', methods=['GET'])
def api_levels():
    """Leaderboard for a guild, merged with member info. Defaults to the largest guild."""
    import level_system
    guild_id = request.args.get('guild_id')
    bot = control_bridge.bot

    guild = None
    if bot is not None:
        if guild_id:
            try:
                guild = bot.get_guild(int(guild_id))
            except (ValueError, TypeError):
                guild = None
        if guild is None and bot.guilds:
            guild = max(bot.guilds, key=lambda g: g.member_count)

    if guild is None:
        return jsonify({"guild": None, "members": [], "settings": level_system.DEFAULT_SETTINGS})

    board = level_system.get_leaderboard(guild.id)
    stats_by_uid = {uid: s for uid, s in board}

    # Merge with ALL guild members so everyone shows (0 XP for newcomers)
    members = []
    seen = set()
    for m in guild.members:
        uid = str(m.id)
        seen.add(uid)
        s = stats_by_uid.get(uid, {
            "xp": 0, "level": 0, "messages": 0, "voice_minutes": 0, "invites": 0,
            "streak": 0, "weekly_xp": 0, "xp_into_level": 0, "xp_needed": 0, "progress": 0,
        })
        members.append({
            "user_id": uid,
            "name": m.display_name,
            "username": str(m),
            "avatar_url": str(m.display_avatar.url) if m.display_avatar else None,
            "is_bot": m.bot,
            "xp": s["xp"],
            "level": s["level"],
            "xp_into_level": s.get("xp_into_level", 0),
            "xp_needed": s.get("xp_needed", 0),
            "progress": s.get("progress", 0),
            "messages": s["messages"],
            "voice_minutes": s["voice_minutes"],
            "invites": s["invites"],
            "streak": s.get("streak", 0),
            "weekly_xp": s.get("weekly_xp", 0),
        })

    # any users with XP but no longer in guild (safety)
    for uid, s in stats_by_uid.items():
        if uid not in seen:
            members.append({
                "user_id": uid,
                "name": f"User {uid}",
                "username": f"User {uid}",
                "avatar_url": None,
                "is_bot": False,
                "xp": s["xp"],
                "level": s["level"],
                "xp_into_level": s.get("xp_into_level", 0),
                "xp_needed": s.get("xp_needed", 0),
                "progress": s.get("progress", 0),
                "messages": s["messages"],
                "voice_minutes": s["voice_minutes"],
                "invites": s["invites"],
                "streak": s.get("streak", 0),
                "weekly_xp": s.get("weekly_xp", 0),
            })

    members.sort(key=lambda m: -m["xp"])
    for i, m in enumerate(members):
        m["rank"] = i + 1

    # merge coin balances in a single load (avoids N file reads + no side effects)
    import economy_system
    balances = economy_system.get_all_balances(guild.id)
    for m in members:
        m["coins"] = balances.get(m["user_id"], economy_system.DEFAULT_SETTINGS["starting_coins"])

    return jsonify({
        "guild": {"id": str(guild.id), "name": guild.name, "member_count": guild.member_count},
        "members": members,
        "settings": level_system.get_settings(guild.id),
    })


@app.route('/api/commands', methods=['GET'])
def api_commands():
    return jsonify({"commands": control_bridge.get_commands()})


# ═══════════════════════════════════════════════════════════════════════════════
# TICKET MANAGEMENT (dashboard)
# ═══════════════════════════════════════════════════════════════════════════════

def _pick_guild(bot, guild_id):
    if guild_id:
        try:
            g = bot.get_guild(int(guild_id))
            if g:
                return g
        except (ValueError, TypeError):
            pass
    if bot and bot.guilds:
        return max(bot.guilds, key=lambda g: g.member_count)
    return None


# ═══════════════════════════════════════════════════════════════════════════════
# ECONOMY MANAGEMENT (dashboard)
# ═══════════════════════════════════════════════════════════════════════════════

@app.route('/api/economy', methods=['GET'])
def api_economy_list():
    import economy_system
    guild = _pick_guild(control_bridge.bot, request.args.get('guild_id'))
    if guild is None:
        return jsonify({"guild": None, "members": [], "shop": economy_system.SHOP_ITEMS})

    balances = economy_system.get_all_balances(guild.id)
    members = []
    for m in guild.members:
        if m.bot:
            continue
        members.append({
            "user_id": str(m.id),
            "name": m.display_name,
            "avatar_url": str(m.display_avatar.url) if m.display_avatar else None,
            "balance": balances.get(str(m.id), economy_system.DEFAULT_SETTINGS["starting_coins"]),
        })
    members.sort(key=lambda x: -x["balance"])
    for i, m in enumerate(members):
        m["rank"] = i + 1

    return jsonify({
        "guild": {"id": str(guild.id), "name": guild.name},
        "members": members,
        "shop": economy_system.SHOP_ITEMS,
    })


@app.route('/api/economy/action', methods=['POST'])
def api_economy_action():
    import economy_system
    data = request.get_json(silent=True) or {}
    guild = _pick_guild(control_bridge.bot, data.get('guild_id'))
    if guild is None:
        return jsonify({"ok": False, "error": "Bot has no guilds"})

    action = data.get('action')
    user_id = data.get('user_id')
    amount = data.get('amount', 0)

    if not user_id:
        return jsonify({"ok": False, "error": "user_id required"})

    try:
        if action == 'add':
            economy_system.add_coins(guild.id, user_id, int(amount))
        elif action == 'remove':
            ok, _ = economy_system.spend_coins(guild.id, user_id, int(amount))
            if not ok:
                return jsonify({"ok": False, "error": "Insufficient coins"})
        elif action == 'set':
            # set exact balance
            current = economy_system.get_balance(guild.id, user_id)
            diff = int(amount) - current
            if diff >= 0:
                economy_system.add_coins(guild.id, user_id, diff)
            else:
                ok, _ = economy_system.spend_coins(guild.id, user_id, -diff)
                if not ok:
                    return jsonify({"ok": False, "error": "Insufficient coins"})
        else:
            return jsonify({"ok": False, "error": f"Unknown action '{action}'"})
    except (ValueError, TypeError):
        return jsonify({"ok": False, "error": "Invalid amount"})

    new_balance = economy_system.get_balance(guild.id, user_id)
    control_bridge.add_log("INFO", f"Economy: {action} {amount} coins for user {user_id} (from dashboard)")
    return jsonify({"ok": True, "balance": new_balance})


# ═══════════════════════════════════════════════════════════════════════════════
# MUSIC CONTROL (dashboard)
# ═══════════════════════════════════════════════════════════════════════════════

@app.route('/api/music', methods=['GET'])
def api_music_status():
    return jsonify(control_bridge.get_music_status())


@app.route('/api/music/control', methods=['POST'])
def api_music_control():
    data = request.get_json(silent=True) or {}
    guild_id = data.get('guild_id')
    action = data.get('action')
    if not guild_id or not action:
        return jsonify({"ok": False, "error": "guild_id and action required"})
    return jsonify(control_bridge.music_control(guild_id, action, data.get('value')))


# ═══════════════════════════════════════════════════════════════════════════════
# MODERATION (dashboard)
# ═══════════════════════════════════════════════════════════════════════════════

@app.route('/api/members', methods=['GET'])
def api_members():
    guild = _pick_guild(control_bridge.bot, request.args.get('guild_id'))
    if guild is None:
        return jsonify({"guild": None, "members": []})
    return jsonify({
        "guild": {"id": str(guild.id), "name": guild.name},
        "members": control_bridge.get_members(guild.id),
    })


@app.route('/api/moderate', methods=['POST'])
def api_moderate():
    data = request.get_json(silent=True) or {}
    guild_id = data.get('guild_id')
    action = data.get('action')
    user_id = data.get('user_id')
    if not guild_id or not action or not user_id:
        return jsonify({"ok": False, "error": "guild_id, action and user_id required"})
    return jsonify(control_bridge.mod_action(guild_id, action, user_id, data.get('reason')))


# ═══════════════════════════════════════════════════════════════════════════════
# GIVEAWAYS (dashboard)
# ═══════════════════════════════════════════════════════════════════════════════

@app.route('/api/giveaways', methods=['GET'])
def api_giveaways():
    return jsonify({"giveaways": control_bridge.get_giveaways()})


@app.route('/api/giveaways/create', methods=['POST'])
def api_giveaway_create():
    data = request.get_json(silent=True) or {}
    prize = data.get('prize')
    winners = data.get('winners', 1)
    duration = data.get('duration_minutes', 60)
    if not prize:
        return jsonify({"ok": False, "error": "prize required"})
    gw_id = control_bridge.create_giveaway(
        data.get('guild_id'), prize, winners, duration, data.get('channel_id')
    )
    return jsonify({"ok": True, "giveaway_id": gw_id})


@app.route('/api/giveaways/<gw_id>/end', methods=['POST'])
def api_giveaway_end(gw_id):
    return jsonify(control_bridge.end_giveaway(gw_id))


@app.route('/api/giveaways/<gw_id>/delete', methods=['POST'])
def api_giveaway_delete(gw_id):
    return jsonify(control_bridge.delete_giveaway(gw_id))


# ═══════════════════════════════════════════════════════════════════════════════
# SCHEDULED ANNOUNCEMENTS (dashboard)
# ═══════════════════════════════════════════════════════════════════════════════

@app.route('/api/announcements', methods=['GET'])
def api_announcements():
    return jsonify({"announcements": control_bridge.get_announcements()})


@app.route('/api/announcements/create', methods=['POST'])
def api_announcement_create():
    data = request.get_json(silent=True) or {}
    message = data.get('message')
    channel_id = data.get('channel_id')
    send_at = data.get('send_at')  # unix seconds
    if not message or not channel_id or not send_at:
        return jsonify({"ok": False, "error": "message, channel_id and send_at required"})
    channel_name = data.get('channel_name', '')
    ann_id = control_bridge.create_announcement(
        data.get('guild_id'), channel_id, channel_name, message, send_at
    )
    return jsonify({"ok": True, "announcement_id": ann_id})


@app.route('/api/announcements/<ann_id>/delete', methods=['POST'])
def api_announcement_delete(ann_id):
    return jsonify(control_bridge.delete_announcement(ann_id))


# ═══════════════════════════════════════════════════════════════════════════════
# STATS & ACTIVITY (dashboard)
# ═══════════════════════════════════════════════════════════════════════════════

@app.route('/api/stats/activity', methods=['GET'])
def api_stats_activity():
    import level_system
    import economy_system
    guild = _pick_guild(control_bridge.bot, request.args.get('guild_id'))
    if guild is None:
        return jsonify({"guild": None, "totals": {}, "top": []})

    board = level_system.get_leaderboard(guild.id)
    totals = {
        "xp": sum(s["xp"] for _, s in board),
        "messages": sum(s["messages"] for _, s in board),
        "voice_minutes": sum(s["voice_minutes"] for _, s in board),
        "invites": sum(s["invites"] for _, s in board),
        "tracked_members": len(board),
    }

    # top 5 by activity (messages + voice)
    top = []
    for uid, s in board[:8]:
        member = guild.get_member(int(uid))
        name = member.display_name if member else f"User {uid}"
        top.append({
            "name": name,
            "xp": s["xp"],
            "messages": s["messages"],
            "voice_minutes": s["voice_minutes"],
            "invites": s["invites"],
            "level": s["level"],
        })

    return jsonify({"guild": {"id": str(guild.id), "name": guild.name}, "totals": totals, "top": top})


# ═══════════════════════════════════════════════════════════════════════════════
# MEMBER MANAGEMENT (dashboard)
# ═══════════════════════════════════════════════════════════════════════════════

@app.route('/api/roles', methods=['GET'])
def api_roles():
    guild = _pick_guild(control_bridge.bot, request.args.get('guild_id'))
    if guild is None:
        return jsonify({"roles": []})
    return jsonify({"roles": control_bridge.get_roles(guild.id)})


@app.route('/api/role', methods=['POST'])
def api_role_action():
    data = request.get_json(silent=True) or {}
    guild_id = data.get('guild_id')
    user_id = data.get('user_id')
    role_id = data.get('role_id')
    action = data.get('action')
    if not all([guild_id, user_id, role_id, action]):
        return jsonify({"ok": False, "error": "guild_id, user_id, role_id and action required"})
    return jsonify(control_bridge.role_action(guild_id, user_id, role_id, action))


# ═══════════════════════════════════════════════════════════════════════════════
# AUTO-RESPONDER (dashboard)
# ═══════════════════════════════════════════════════════════════════════════════

@app.route('/api/autoresponders', methods=['GET'])
def api_autoresponders():
    guild_id = request.args.get('guild_id')
    return jsonify({"autoresponders": control_bridge.get_autoresponders(guild_id)})


@app.route('/api/autoresponders/add', methods=['POST'])
def api_autoresponder_add():
    data = request.get_json(silent=True) or {}
    trigger = data.get('trigger')
    response = data.get('response')
    guild_id = data.get('guild_id')
    if not trigger or not response or not guild_id:
        return jsonify({"ok": False, "error": "guild_id, trigger and response required"})
    return jsonify(control_bridge.add_autoresponder(guild_id, trigger, response))


@app.route('/api/autoresponders/remove', methods=['POST'])
def api_autoresponder_remove():
    data = request.get_json(silent=True) or {}
    trigger = data.get('trigger')
    guild_id = data.get('guild_id')
    if not trigger or not guild_id:
        return jsonify({"ok": False, "error": "guild_id and trigger required"})
    return jsonify(control_bridge.remove_autoresponder(guild_id, trigger))


# ═══════════════════════════════════════════════════════════════════════════════
# BACKUP / EXPORT (dashboard)
# ═══════════════════════════════════════════════════════════════════════════════

DATA_FILES = ['levels_data.json', 'economy_data.json', 'tickets.json', 'dashboard_settings.json']


@app.route('/api/backup/status', methods=['GET'])
def api_backup_status():
    import os
    files = []
    for fn in DATA_FILES:
        p = os.path.join(BASE_DIR, fn)
        if os.path.exists(p):
            files.append({"name": fn, "size": os.path.getsize(p), "modified": os.path.getmtime(p)})
    return jsonify({"files": files})


@app.route('/api/backup/download', methods=['GET'])
def api_backup_download():
    import io
    import json as _json
    import os
    from flask import Response
    bundle = {}
    for fn in DATA_FILES:
        p = os.path.join(BASE_DIR, fn)
        if os.path.exists(p):
            try:
                with open(p, 'r', encoding='utf-8') as f:
                    bundle[fn] = _json.load(f)
            except Exception:
                pass
    data = _json.dumps(bundle, indent=2, ensure_ascii=False)
    return Response(
        data,
        mimetype="application/json",
        headers={"Content-Disposition": "attachment; filename=mangoli_backup.json"},
    )


@app.route('/api/backup/restore', methods=['POST'])
def api_backup_restore():
    import json as _json
    import os
    data = request.get_json(silent=True) or {}
    bundle = data.get('bundle')
    if not bundle:
        return jsonify({"ok": False, "error": "No backup data provided"})
    restored = []
    for fn, content in bundle.items():
        if fn not in DATA_FILES:
            continue
        p = os.path.join(BASE_DIR, fn)
        try:
            with open(p, 'w', encoding='utf-8') as f:
                _json.dump(content, f, indent=2)
            restored.append(fn)
        except Exception as e:
            return jsonify({"ok": False, "error": f"Failed to restore {fn}: {e}"})
    control_bridge.add_log("INFO", f"Backup restored: {', '.join(restored)}")
    return jsonify({"ok": True, "restored": restored})


# ═══════════════════════════════════════════════════════════════════════════════
# WEBHOOK MANAGEMENT (dashboard)
# ═══════════════════════════════════════════════════════════════════════════════

@app.route('/api/webhooks', methods=['GET'])
def api_webhooks():
    guild = _pick_guild(control_bridge.bot, request.args.get('guild_id'))
    if guild is None:
        return jsonify({"webhooks": [], "channels": []})
    webhooks = control_bridge.get_webhooks(guild.id)
    channels = [{"id": str(c.id), "name": c.name} for c in guild.text_channels]
    return jsonify({"webhooks": webhooks, "channels": channels})


@app.route('/api/webhooks/create', methods=['POST'])
def api_webhook_create():
    data = request.get_json(silent=True) or {}
    guild_id = data.get('guild_id')
    channel_id = data.get('channel_id')
    name = data.get('name', 'Mangoli Webhook')
    if not guild_id or not channel_id:
        return jsonify({"ok": False, "error": "guild_id and channel_id required"})
    return jsonify(control_bridge.create_webhook(guild_id, channel_id, name))


@app.route('/api/webhooks/delete', methods=['POST'])
def api_webhook_delete():
    data = request.get_json(silent=True) or {}
    guild_id = data.get('guild_id')
    webhook_id = data.get('webhook_id')
    if not guild_id or not webhook_id:
        return jsonify({"ok": False, "error": "guild_id and webhook_id required"})
    return jsonify(control_bridge.delete_webhook(guild_id, webhook_id))


@app.route('/api/tickets', methods=['GET'])
def api_tickets_list():
    import tickets
    guild_id = request.args.get('guild_id')
    guild = _pick_guild(control_bridge.bot, guild_id)
    if guild is None:
        return jsonify({"guild": None, "tickets": [], "config": {"configured": False}})
    return jsonify({
        "guild": {"id": str(guild.id), "name": guild.name},
        "tickets": tickets.get_dashboard_tickets(guild.id, bot=control_bridge.bot),
        "config": tickets.get_dashboard_config(guild.id),
    })


@app.route('/api/tickets/config', methods=['GET'])
def api_tickets_config():
    import tickets
    guild_id = request.args.get('guild_id')
    guild = _pick_guild(control_bridge.bot, guild_id)
    if guild is None:
        return jsonify({"configured": False, "channels": [], "roles": [], "categories_channels": []})
    config = tickets.get_dashboard_config(guild.id)
    config["channels"] = [{"id": str(c.id), "name": c.name} for c in guild.text_channels]
    config["categories_channels"] = [{"id": str(c.id), "name": c.name} for c in guild.categories]
    config["roles"] = [{"id": str(r.id), "name": r.name} for r in guild.roles if r.name != "@everyone"]
    return jsonify(config)


@app.route('/api/tickets/config', methods=['POST'])
def api_tickets_config_save():
    import tickets
    data = request.get_json(silent=True) or {}
    guild = _pick_guild(control_bridge.bot, data.get('guild_id'))
    if guild is None:
        return jsonify({"ok": False, "error": "Bot has no guilds"})
    config = tickets.set_dashboard_config(guild.id, data)
    return jsonify({"ok": True, "config": config})


@app.route('/api/tickets/preview', methods=['POST'])
def api_tickets_preview():
    import tickets
    data = request.get_json(silent=True) or {}
    preview = tickets.preview_ticket_message(data.get("panel"), data.get("category_id"))
    return jsonify({"preview": preview})


@app.route('/api/tickets/<ticket_id>/action', methods=['POST'])
def api_tickets_action(ticket_id):
    import tickets
    data = request.get_json(silent=True) or {}
    guild = _pick_guild(control_bridge.bot, data.get('guild_id'))
    if guild is None:
        return jsonify({"ok": False, "error": "Bot has no guilds"})
    ok, msg = tickets.ticket_action(guild.id, ticket_id, data.get('action'), bot=control_bridge.bot)
    return jsonify({"ok": ok, "message": msg})


@app.route('/api/tickets/panel/send', methods=['POST'])
def api_tickets_panel_send():
    import tickets
    data = request.get_json(silent=True) or {}
    guild = _pick_guild(control_bridge.bot, data.get('guild_id'))
    channel_id = data.get('channel_id')
    if guild is None or not channel_id:
        return jsonify({"ok": False, "error": "guild/channel required"})
    channel = guild.get_channel(int(channel_id))
    if channel is None:
        return jsonify({"ok": False, "error": "Channel not found"})

    d, g = tickets.guild_conf(guild.id)
    panel = g.get("panel_data")
    if not panel:
        return jsonify({"ok": False, "error": "No panel configured"})
    panel["channel_id"] = str(channel.id)
    tickets.save(d)

    # Send the actual panel via the bot loop
    async def send_panel():
        embed = tickets.build_panel_embed(panel)
        if panel.get("display_type") == "buttons":
            view = tickets.PanelButtonsView(panel)
        else:
            view = tickets.PanelView(panel)
        sent = await channel.send(embed=embed, view=view)
        panel["message_id"] = str(sent.id)
        tickets.save(tickets.load())

    if control_bridge.bot and control_bridge.bot.loop.is_running():
        control_bridge.run_on_loop(send_panel())
        return jsonify({"ok": True, "channel": channel.name})
    return jsonify({"ok": False, "error": "Bot loop not running"})


@app.route('/api/settings', methods=['GET'])
def api_get_settings():
    return jsonify({
        "settings": control_bridge.get_settings(),
        "personalities": control_bridge.list_personalities(),
    })


@app.route('/api/settings', methods=['POST'])
def api_set_settings():
    data = request.get_json(silent=True) or {}
    settings = control_bridge.set_settings(data)
    return jsonify({"ok": True, "settings": settings})


# ═══════════════════════════════════════════════════════════════════════════════
# ERROR HANDLERS
# ═══════════════════════════════════════════════════════════════════════════════

@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Not found"}), 404


@app.errorhandler(500)
def server_error(e):
    return jsonify({"error": "Server error"}), 500


# ═══════════════════════════════════════════════════════════════════════════════
# SERVER STARTUP
# ═══════════════════════════════════════════════════════════════════════════════

def start_dashboard_server(port=16086, debug=False):
    """Start the dashboard server in a separate thread."""
    def run():
        app.run(host='0.0.0.0', port=port, debug=debug, use_reloader=False, threaded=True)

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    print(f"\n{'═' * 60}")
    print("  📊 MANGOLI BOT DASHBOARD")
    print(f"  🌐 Running at: http://localhost:{port}")
    print(f"{'═' * 60}\n")
    return thread


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=16086, debug=True)
