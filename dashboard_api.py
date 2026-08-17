"""
═══════════════════════════════════════════════════════════════════════════════
NOVAGEN BOT DASHBOARD API
Web control panel backend for the Discord bot.
by Nokiatis Community
═══════════════════════════════════════════════════════════════════════════════

Serves the dashboard UI and a JSON API that lets you control the running bot:
status, voice (join / pause / resume / leave / play), logs, servers, commands,
and settings — all routed through control_bridge.
"""

from flask import Flask, jsonify, send_from_directory, request
from flask_cors import CORS
import os
import threading
from datetime import datetime

import control_bridge

# ═══════════════════════════════════════════════════════════════════════════════
# APP SETUP
# ═══════════════════════════════════════════════════════════════════════════════

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__, static_folder='dashboard')
CORS(app, resources={r"/api/*": {"origins": "*"}})


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
        headers={"Content-Disposition": "attachment; filename=novagen_logs.txt"},
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

def start_dashboard_server(port=5000, debug=False):
    """Start the dashboard server in a separate thread."""
    def run():
        app.run(host='0.0.0.0', port=port, debug=debug, use_reloader=False, threaded=True)

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    print(f"\n{'═' * 60}")
    print("  📊 NOVAGEN BOT DASHBOARD")
    print(f"  🌐 Running at: http://localhost:{port}")
    print(f"{'═' * 60}\n")
    return thread


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
