"""
═══════════════════════════════════════════════════════════════════════════════
ECONOMY SYSTEM
Coins, gambling, shop & XP boosters for the Mangoli bot.
by Nokiatis Community
═══════════════════════════════════════════════════════════════════════════════

Coins are earned passively (chat/voice/daily) and spent on gambling or shop
items (XP boosters). Balances persist to economy_data.json.
"""

import json
import os
import random
import threading
import time

DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'economy_data.json')
_lock = threading.Lock()

DEFAULT_SETTINGS = {
    "starting_coins": 100,
    "chat_coin_chance": 0.25,       # 25% chance to earn coins on an XP message
    "chat_coin_min": 5,
    "chat_coin_max": 15,
    "voice_coins_per_minute": 2,
    "daily_coins": 150,
    "coinflip_min_bet": 10,
    "slots_min_bet": 10,
}

# Shop: id -> {name, emoji, cost, description, effect}
SHOP_ITEMS = {
    "xp_boost_1h": {
        "name": "XP Boost (1 hour)",
        "emoji": "⚡",
        "cost": 250,
        "description": "Double XP for 1 hour",
        "effect": {"type": "xp_boost", "duration": 3600, "multiplier": 2.0},
    },
    "xp_boost_3h": {
        "name": "XP Boost (3 hours)",
        "emoji": "🔥",
        "cost": 600,
        "description": "Double XP for 3 hours",
        "effect": {"type": "xp_boost", "duration": 10800, "multiplier": 2.0},
    },
    "xp_boost_1d": {
        "name": "XP Boost (24 hours)",
        "emoji": "💎",
        "cost": 4000,
        "description": "Double XP for 24 hours",
        "effect": {"type": "xp_boost", "duration": 86400, "multiplier": 2.0},
    },
    "lucky_charm": {
        "name": "Lucky Charm",
        "emoji": "🍀",
        "cost": 300,
        "description": "+10% win chance on gambling for 1 hour",
        "effect": {"type": "luck", "duration": 3600, "amount": 0.10},
    },
}


def _default_user():
    return {
        "balance": DEFAULT_SETTINGS["starting_coins"],
        "lifetime_earned": 0,
        "lifetime_spent": 0,
        "boost_until": 0.0,
        "boost_multiplier": 1.0,
        "luck_until": 0.0,
        "luck_amount": 0.0,
        "inventory": [],
    }


def _default_guild():
    return {"users": {}, "settings": dict(DEFAULT_SETTINGS)}


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
            print(f"[Economy] save error: {e}")


def _guild(data, guild_id):
    gid = str(guild_id)
    return data.setdefault("guilds", {}).setdefault(gid, _default_guild())


def _user(data, guild_id, user_id):
    g = _guild(data, guild_id)
    uid = str(user_id)
    if uid not in g["users"]:
        g["users"][uid] = _default_user()
    return g["users"][uid]


def _peek_user(data, guild_id, user_id):
    """Return the user dict WITHOUT creating it (None if absent)."""
    g = data.get("guilds", {}).get(str(guild_id))
    if g is None:
        return None
    return g.get("users", {}).get(str(user_id))


def get_settings(guild_id):
    data = load()
    return _guild(data, guild_id)["settings"]


def get_balance(guild_id, user_id):
    """Return the user's balance WITHOUT creating a record (no side effects)."""
    data = load()
    u = _peek_user(data, guild_id, user_id)
    if u is None:
        return DEFAULT_SETTINGS["starting_coins"]
    return u["balance"]


def get_all_balances(guild_id):
    """Return {user_id: balance} for a guild in a single load (for dashboards)."""
    data = load()
    g = data.get("guilds", {}).get(str(guild_id), {})
    out = {}
    for uid, u in g.get("users", {}).items():
        out[uid] = u.get("balance", 0)
    return out


def add_coins(guild_id, user_id, amount, reason="earn"):
    """Add coins. Returns new balance."""
    data = load()
    u = _user(data, guild_id, user_id)
    u["balance"] = u.get("balance", 0) + amount
    if reason == "earn":
        u["lifetime_earned"] = u.get("lifetime_earned", 0) + amount
    save(data)
    return u["balance"]


def spend_coins(guild_id, user_id, amount):
    """Deduct coins if affordable. Returns (ok, new_balance)."""
    data = load()
    u = _user(data, guild_id, user_id)
    if u.get("balance", 0) < amount:
        return False, u["balance"]
    u["balance"] -= amount
    u["lifetime_spent"] = u.get("lifetime_spent", 0) + amount
    save(data)
    return True, u["balance"]


def transfer(guild_id, sender_id, receiver_id, amount):
    """Move coins between users. Returns (ok, message)."""
    if sender_id == receiver_id:
        return False, "You can't send coins to yourself."
    ok, _ = spend_coins(guild_id, sender_id, amount)
    if not ok:
        return False, "Insufficient coins."
    add_coins(guild_id, receiver_id, amount, reason="transfer")
    return True, f"Sent {amount} coins."


# ── Boosts ────────────────────────────────────────────────────────────────────

def get_boost(guild_id, user_id):
    """Return (multiplier, luck_amount) currently active. No side effects."""
    data = load()
    u = _peek_user(data, guild_id, user_id)
    if u is None:
        return 1.0, 0.0
    now = time.time()
    mult = u.get("boost_multiplier", 1.0)
    luck = u.get("luck_amount", 0.0)
    if u.get("boost_until", 0) <= now:
        mult = 1.0
    if u.get("luck_until", 0) <= now:
        luck = 0.0
    return mult, luck


def apply_purchase(guild_id, user_id, item_id):
    """Buy a shop item. Returns (ok, message)."""
    item = SHOP_ITEMS.get(item_id)
    if not item:
        return False, "Unknown item."
    ok, _ = spend_coins(guild_id, user_id, item["cost"])
    if not ok:
        return False, f"Insufficient coins — {item['name']} costs {item['cost']} coins."
    data = load()
    u = _user(data, guild_id, user_id)
    eff = item["effect"]
    now = time.time()
    if eff["type"] == "xp_boost":
        u["boost_until"] = max(u.get("boost_until", 0), now) + eff["duration"]
        u["boost_multiplier"] = eff["multiplier"]
    elif eff["type"] == "luck":
        u["luck_until"] = max(u.get("luck_until", 0), now) + eff["duration"]
        u["luck_amount"] = eff["amount"]
    u.setdefault("inventory", []).append(item_id)
    save(data)
    return True, f"Purchased {item['emoji']} {item['name']}!"


def active_effects(guild_id, user_id):
    """Human-readable list of active effects. No side effects."""
    data = load()
    u = _peek_user(data, guild_id, user_id)
    if u is None:
        return []
    out = []
    now = time.time()
    if u.get("boost_until", 0) > now:
        mins = int((u["boost_until"] - now) // 60)
        out.append(f"⚡ {u.get('boost_multiplier', 2.0)}x XP for {mins} min")
    if u.get("luck_until", 0) > now:
        mins = int((u["luck_until"] - now) // 60)
        out.append(f"🍀 +{int(u.get('luck_amount', 0.10)*100)}% luck for {mins} min")
    return out


# ── Gambling ──────────────────────────────────────────────────────────────────

def coinflip(guild_id, user_id, side, bet):
    """Bet on heads/tails. Returns (ok, won, result_side, message)."""
    min_bet = get_settings(guild_id).get("coinflip_min_bet", 10)
    if bet < min_bet:
        return False, None, None, f"Minimum bet is {min_bet} coins."
    ok, _ = spend_coins(guild_id, user_id, bet)
    if not ok:
        return False, None, None, "Insufficient coins."
    _, luck = get_boost(guild_id, user_id)
    result = random.choice(["heads", "tails"])
    # Lucky charm makes the coin land on your side with `luck` probability
    if luck > 0 and random.random() < luck:
        result = side
    won = (result == side)
    if won:
        payout = bet * 2
        add_coins(guild_id, user_id, payout, reason="gamble_win")
        return True, True, result, f"It's **{result}**! You won {payout} coins! 🎉"
    return True, False, result, f"It's **{result}**! You lost {bet} coins. 😢"


def slots(guild_id, user_id, bet):
    """Play a 3-reel slot. Returns (ok, payout, reels, message)."""
    min_bet = get_settings(guild_id).get("slots_min_bet", 10)
    if bet < min_bet:
        return False, 0, None, f"Minimum bet is {min_bet} coins."
    ok, _ = spend_coins(guild_id, user_id, bet)
    if not ok:
        return False, 0, None, "Insufficient coins."
    _, luck = get_boost(guild_id, user_id)
    symbols = ["🍒", "🍋", "🔔", "💎", "7️⃣", "⭐"]
    # weights: rare symbols pay more
    weights = [30, 25, 18, 12, 10, 5]
    reels = [random.choices(symbols, weights=weights)[0] for _ in range(3)]
    payout = 0
    if reels[0] == reels[1] == reels[2]:
        idx = symbols.index(reels[0])
        # rare symbol => bigger multiplier (tuned for ~0.85 RTP)
        mult = {0: 8, 1: 10, 2: 14, 3: 20, 4: 30, 5: 50}[idx]
        payout = bet * mult
    elif reels[0] == reels[1] or reels[1] == reels[2]:
        payout = bet  # pair refunds your bet (break-even, feels better)
    if payout > 0:
        add_coins(guild_id, user_id, payout, reason="gamble_win")
        return True, payout, reels, f"`{' '.join(reels)}` — You won {payout} coins! 🎉"
    return True, 0, reels, f"`{' '.join(reels)}` — No match. Lost {bet} coins. 😢"


def get_balance_leaderboard(guild_id):
    """[(user_id, balance)] sorted desc."""
    data = load()
    g = _guild(data, guild_id)
    board = [(uid, u.get("balance", 0)) for uid, u in g["users"].items()]
    board.sort(key=lambda t: -t[1])
    return board


print("[Economy] Economy system loaded")
