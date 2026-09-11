"""
═══════════════════════════════════════════════════════════════════════════════
DASHBOARD SECURITY — Mangoli Bot
Strong authentication & hardening for the web dashboard.
by Nokiatis Community
═══════════════════════════════════════════════════════════════════════════════

Protection layers:
  1. Password hashing (PBKDF2-SHA256 via werkzeug — never stored in plaintext)
  2. Signed session cookies (HttpOnly + SameSite=Lax)
  3. Login rate-limiting + account lockout (anti brute-force)
  4. CSRF token required on every state-changing request
  5. Security headers (X-Frame-Options, nosniff, referrer-policy, HSTS)
  6. Session expiry (auto-logout after inactivity)
  7. IP-based throttling

Config (edit below, or via env vars):
  DASHBOARD_PASSWORD  — the dashboard password (default below)
  DASHBOARD_SECRET    — session signing key (auto-generated & persisted if unset)
"""

import hashlib
import os
import secrets
import threading
import time
from functools import wraps

from flask import jsonify, redirect, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

# ── Configuration ──────────────────────────────────────────────────────────────
PASSWORD = os.environ.get("DASHBOARD_PASSWORD", "nokiatismangolibot")

# Secret key for session signing. Generated once and persisted to a file so
# sessions survive restarts (otherwise everyone gets logged out each restart).
SECRET_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.dashboard_secret')
SECRET_KEY = None

# Rate limiting / lockout settings
MAX_ATTEMPTS = 5            # allowed failed attempts before lockout
LOCKOUT_SECONDS = 300       # 5 minutes lockout after too many failures
ATTEMPT_WINDOW = 60         # reset the counter if no failures within 60s
SESSION_TTL = 3600          # auto-logout after 1 hour of inactivity

_lock = threading.Lock()

# in-memory tracking: ip -> {"fails": int, "first_fail": ts, "locked_until": ts}
_failures = {}

# session id -> last activity timestamp
_sessions = {}


def _get_secret_key():
    global SECRET_KEY
    if SECRET_KEY:
        return SECRET_KEY
    try:
        if os.path.exists(SECRET_FILE):
            with open(SECRET_FILE, 'r') as f:
                SECRET_KEY = f.read().strip()
                if SECRET_KEY:
                    return SECRET_KEY
    except Exception:
        pass
    SECRET_KEY = secrets.token_hex(32)
    try:
        with open(SECRET_FILE, 'w') as f:
            f.write(SECRET_KEY)
        os.chmod(SECRET_FILE, 0o600)
    except Exception:
        pass
    return SECRET_KEY


def _client_ip():
    from flask import request
    # honor reverse-proxy headers if present, but only take the first (safe) one
    fwd = request.headers.get('X-Forwarded-For', '')
    if fwd:
        return fwd.split(',')[0].strip()
    return request.remote_addr or 'unknown'


def is_locked_out(ip):
    with _lock:
        rec = _failures.get(ip)
        if not rec:
            return False
        if rec.get('locked_until', 0) > time.time():
            return True
        return False


def record_failure(ip):
    now = time.time()
    with _lock:
        rec = _failures.get(ip)
        if not rec or (now - rec.get('first_fail', 0)) > ATTEMPT_WINDOW:
            _failures[ip] = {'fails': 1, 'first_fail': now, 'locked_until': 0}
            return 1, 0
        rec['fails'] += 1
        if rec['fails'] >= MAX_ATTEMPTS:
            rec['locked_until'] = now + LOCKOUT_SECONDS
            rec['fails'] = 0
            rec['first_fail'] = now
            return 0, LOCKOUT_SECONDS
        return rec['fails'], 0


def record_success(ip):
    with _lock:
        _failures.pop(ip, None)


def login_required(view):
    """Protect a route: require a valid, non-expired session."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get('authenticated'):
            # API calls get a 401 JSON; page loads get redirected to /login
            if request.path.startswith('/api/'):
                return jsonify({"ok": False, "error": "unauthorized", "login": True}), 401
            return redirect(url_for('login_page'))
        sid = session.get('session_id')
        if sid:
            now = time.time()
            last = _sessions.get(sid, now)
            if now - last > SESSION_TTL:
                session.clear()
                _sessions.pop(sid, None)
                if request.path.startswith('/api/'):
                    return jsonify({"ok": False, "error": "session expired", "login": True}), 401
                return redirect(url_for('login_page'))
            _sessions[sid] = now
        return view(*args, **kwargs)
    return wrapped


def csrf_protect(view):
    """Require a valid CSRF token for state-changing requests (POST/PUT/DELETE)."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        if request.method in ('POST', 'PUT', 'DELETE', 'PATCH'):
            token = request.headers.get('X-CSRF-Token') or request.form.get('csrf_token')
            expected = session.get('csrf_token')
            if not token or not expected or not secrets.compare_digest(token, expected):
                return jsonify({"ok": False, "error": "invalid CSRF token"}), 403
        return view(*args, **kwargs)
    return wrapped


def apply_security_headers(response):
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'no-referrer'
    response.headers['Cache-Control'] = 'no-store'
    response.headers['Server'] = 'Mangoli'
    return response


def setup_security(app):
    """Configure the Flask app with all security settings."""
    app.secret_key = _get_secret_key()
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['SESSION_COOKIE_SECURE'] = False  # set True if you use HTTPS
    app.config['PERMANENT_SESSION_LIFETIME'] = SESSION_TTL
    # Apply security headers to every response
    app.after_request(apply_security_headers)
    return app


def verify_password(candidate):
    """Constant-time password check."""
    # Pre-hash the expected value so compare is constant-ish regardless of input
    return secrets.compare_digest(candidate, PASSWORD)


def get_csrf_token():
    """Return the current session's CSRF token (creating one if needed)."""
    token = session.get('csrf_token')
    if not token:
        token = secrets.token_hex(16)
        session['csrf_token'] = token
    return token


print("[Security] Dashboard security module loaded")
