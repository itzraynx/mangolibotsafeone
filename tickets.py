"""
═══════════════════════════════════════════════════════════════════════════════
TICKET SYSTEM — Mangoli Bot
Full-featured support ticket system for Mangoli Bot.
by Nokiatis Community
═══════════════════════════════════════════════════════════════════════════════

Features:
  • /panel      — create, configure & deploy an interactive ticket panel
                  (Dropdown or Buttons display mode)
  • /settings   — staff roles + blacklist management
  • /claim /unclaim /close /reopen /delete /add /remove /transcript
  • Pre-ticket questionnaires (modals)
  • Star rating + feedback when closing
  • HTML transcripts
  • 24h inactivity auto-close
  • Blacklist system
  • DM notifications + log channels (create / close / rating)

Storage: tickets.json (consistent with the rest of Mangoli Bot).
"""

import asyncio
import io
import json
import os
import threading
import time
from datetime import datetime, timezone
from html import escape as html_escape

import discord
from discord import app_commands

DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tickets.json')

# ── Branding ───────────────────────────────────────────────────────────────────
BRAND = "Mangoli Bot"
ICON = "https://i.imgur.com/7ZGzqjY.png"
FOOTER = f"⚡ {BRAND} • by Nokiatis Community"
PRIMARY = 0x5865F2
SUCCESS = 0x57F287
ERROR = 0xED4245
WARNING = 0xFEE75C
GOLD = 0xFBBF24

# Emojis
E = {
    "ticket": "🎫", "claim": "🙋", "close": "🔒", "delete": "🗑️", "reopen": "🔓",
    "add": "➕", "remove": "➖", "transcript": "📄", "check": "✅", "cross": "❌",
    "lock": "🔒", "unlock": "🔓", "star_fill": "⭐", "star_empty": "☆",
    "settings": "⚙️", "dashboard": "📊", "warning": "⚠️",
}

# Custom emoji resolution (Titan X emoji names, resolved from the guild)
try:
    from emojis import em as _cem
    E = {
        "ticket": _cem("ticket"), "claim": _cem("claim"), "close": _cem("close"),
        "delete": _cem("delete"), "reopen": _cem("reopen"), "add": _cem("add"),
        "remove": _cem("remove"), "transcript": _cem("transcript"),
        "check": _cem("check"), "cross": _cem("cross"), "lock": _cem("close"),
        "unlock": _cem("reopen"), "star_fill": _cem("star_fill"), "star_empty": _cem("star_empty"),
        "settings": _cem("settings"), "dashboard": _cem("dashboard"), "warning": _cem("warning"),
        "ping": _cem("ping"), "logs": _cem("logs"), "timer": _cem("timer"), "mail": _cem("mail"),
    }
except ImportError:
    pass

DEFAULT_CATEGORIES = {
    "support": {"name": "Support", "emoji": "💬", "desc": "General help & questions"},
    "order":   {"name": "Order / Purchase", "emoji": "🛒", "desc": "Billing & orders"},
    "report":  {"name": "Report User", "emoji": "⚠️", "desc": "Report a rule-breaker"},
    "partnership": {"name": "Partnership", "emoji": "🤝", "desc": "Collabs & partnerships"},
    "other":   {"name": "Other", "emoji": "🎮", "desc": "Anything else"},
}

DEFAULT_SETTINGS = {
    "ping_user": True,
    "ping_role": False,
    "user_can_close": True,
    "max_tickets_per_user": 1,
    "dm_user_on_open": True,
    "dm_user_on_close": True,
    "welcome_message": "",
}

AUTOCLOSE_HOURS = 24

_lock = threading.Lock()

# Module-level bot reference (set by register()) so views can use it.
_bot = None


def _set_bot(b):
    global _bot
    _bot = b


# ── Data layer ─────────────────────────────────────────────────────────────────

def _default_panel(guild_id):
    return {
        "panel_id": f"panel_{guild_id}",
        "guild_id": str(guild_id),
        "name": "Mangoli Tickets",
        "channel_id": None,
        "display_type": "select",        # "select" or "buttons"
        "panel_message": {"title": "Open a Ticket", "description": "Select a category below to create a ticket"},
        "placeholder": "🎫 Choose a category…",
        "categories": {
            cid: {"id": cid, "name": c["name"], "emoji": c["emoji"], "desc": c["desc"],
                  "support_roles": [], "ticket_category_id": None,
                  "naming_format": "ticket-{username}",
                  "settings": dict(DEFAULT_SETTINGS),
                  "questions": [], "active": True}
            for cid, c in DEFAULT_CATEGORIES.items()
        },
        "logs": {"create": None, "close": None, "rating": None},
        "active": True,
        "message_id": None,
    }


def _default_guild(guild_id):
    return {
        "guild_id": str(guild_id),
        "staff_roles": [],
        "blacklist": [],
        "panel": None,          # panel_id or None
        "counter": 0,
        "tickets": {},          # ticket_id -> ticket
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
            print(f"[Tickets] save error: {e}")


def guild_conf(guild_id, create=True):
    data = load()
    gid = str(guild_id)
    if gid not in data.setdefault("guilds", {}):
        if not create:
            return data, None
        data["guilds"][gid] = _default_guild(gid)
        save(data)
    return data, data["guilds"][gid]


def get_panel(guild_id):
    data, g = guild_conf(guild_id, create=False)
    if g is None or g.get("panel") is None:
        return None
    # panel stored inline in guild for simplicity
    return g.get("panel_data") or None


# ── Helpers ────────────────────────────────────────────────────────────────────

def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def is_staff(member, guild_data, category=None):
    """True if the member can manage tickets (manage_channels, staff role, or support role)."""
    if member.guild_permissions.manage_channels:
        return True
    roles = {str(r.id) for r in member.roles}
    if any(r in roles for r in guild_data.get("staff_roles", [])):
        return True
    if category:
        if any(r in roles for r in category.get("support_roles", [])):
            return True
    return False


def is_blacklisted(guild_data, user_id):
    uid = str(user_id)
    return any(b.get("user_id") == uid for b in guild_data.get("blacklist", []))


def channel_name_for(category, user, number):
    fmt = category.get("naming_format") or "ticket-{username}"
    name = fmt.replace("{username}", user.name.lower()[:16]).replace("{number}", str(number).zfill(3))
    return name[:50] or f"ticket-{number}"


def channel_name_for(category, user, number):
    fmt = category.get("naming_format") or "ticket-{username}"
    name = fmt.replace("{username}", user.name.lower()[:16]).replace("{number}", str(number).zfill(3))
    return name[:50] or f"ticket-{number}"


async def get_or_create_ticket_category(guild, cat, data):
    """Return a CategoryChannel for the ticket.

    Priority:
      1. The category explicitly configured in the dashboard (ticket_category_id)
      2. A category this bot auto-created earlier for this ticket type
      3. NEW: auto-create a category named "<Category Name> tickets"
    """
    # 1. explicitly configured category
    if cat.get("ticket_category_id"):
        try:
            existing = guild.get_channel(int(cat["ticket_category_id"]))
            if isinstance(existing, discord.CategoryChannel):
                return existing
        except (ValueError, TypeError):
            pass
    # 2. previously auto-created category (still exists)
    if cat.get("auto_category_id"):
        try:
            existing = guild.get_channel(int(cat["auto_category_id"]))
            if isinstance(existing, discord.CategoryChannel):
                return existing
        except (ValueError, TypeError):
            pass
    # 3. auto-create one named "<name> tickets"
    name = f"{cat.get('name', 'Support')} tickets"[:100]
    try:
        new_cat = await guild.create_category(name=name)
    except Exception:
        return None
    cat["auto_category_id"] = str(new_cat.id)
    save(data)
    return new_cat


async def cleanup_empty_category(bot, guild_id, ticket):
    """Delete an auto-created category if it became empty after a ticket was removed."""
    if not ticket.get("category_id"):
        return
    guild = bot.get_guild(int(guild_id))
    if not guild:
        return
    data, g = guild_conf(guild_id, create=False)
    panel = g.get("panel_data") if g else None
    cat = panel["categories"].get(ticket["category_id"]) if panel else None
    if not cat or not cat.get("auto_category_id"):
        return
    try:
        cat_channel = guild.get_channel(int(cat["auto_category_id"]))
        if isinstance(cat_channel, discord.CategoryChannel) and len(cat_channel.channels) == 0:
            await cat_channel.delete()
            cat.pop("auto_category_id", None)
            save(data)
    except Exception as e:
        print(f"[Tickets] cleanup empty category error: {e}")


async def delete_ticket_channel(bot, guild_id, ticket):
    """Delete a ticket's channel and auto-cleanup its empty category."""
    guild = bot.get_guild(int(guild_id))
    if not guild or not ticket.get("channel_id"):
        return
    ch = guild.get_channel(int(ticket["channel_id"]))
    if ch:
        try:
            await ch.delete()
        except Exception:
            pass
    await cleanup_empty_category(bot, guild_id, ticket)


async def rename_ticket_channel(bot, guild_id, ticket, closed):
    """Rename the ticket channel to reflect its state (add 'closed' prefix)."""
    guild = bot.get_guild(int(guild_id)) if bot else None
    if not guild or not ticket.get("channel_id"):
        return
    ch = guild.get_channel(int(ticket["channel_id"]))
    if not ch:
        return
    try:
        name = ch.name
        # strip any existing "closed-" / "-closed" markers to avoid duplicates
        name = name.replace("closed-", "").replace("-closed", "").replace("closed", "")
        if closed:
            name = f"closed-{name}"
        await ch.edit(name=name[:100])
    except Exception as e:
        print(f"[Tickets] rename channel error: {e}")


# ── Modals ─────────────────────────────────────────────────────────────────────

class CloseReasonModal(discord.ui.Modal, title="Close Ticket"):
    def __init__(self, on_submit):
        super().__init__()
        self.on_submit_cb = on_submit
        self.reason = discord.ui.TextInput(
            label="Reason for closing (optional)",
            style=discord.TextStyle.paragraph,
            placeholder="Provide a reason for closing this ticket…",
            required=False,
            max_length=500,
        )
        self.add_item(self.reason)

    async def on_submit(self, interaction: discord.Interaction):
        await self.on_submit_cb(interaction, self.reason.value.strip() or None)


class TicketQuestionsModal(discord.ui.Modal):
    def __init__(self, title, questions, on_submit):
        super().__init__(title=title[:45] or "Ticket")
        self.questions = questions
        self.on_submit_cb = on_submit
        self.inputs = []
        for q in questions[:5]:
            inp = discord.ui.TextInput(
                label=q["label"][:45],
                placeholder=q.get("placeholder", ""),
                style=discord.TextStyle.paragraph if q.get("style") == "long" else discord.TextStyle.short,
                required=q.get("required", True),
                max_length=1000,
            )
            self.inputs.append(inp)
            self.add_item(inp)

    async def on_submit(self, interaction: discord.Interaction):
        answers = []
        for q, inp in zip(self.questions, self.inputs):
            answers.append({"question": q["label"], "answer": str(inp.value)})
        await self.on_submit_cb(interaction, answers)


class FeedbackModal(discord.ui.Modal, title="Feedback"):
    def __init__(self, stars, on_submit):
        super().__init__()
        self.stars = stars
        self.on_submit_cb = on_submit
        self.feedback = discord.ui.TextInput(
            label="Feedback (optional)",
            style=discord.TextStyle.paragraph,
            placeholder="Tell us what you thought…",
            required=False,
            max_length=1000,
        )
        self.add_item(self.feedback)

    async def on_submit(self, interaction: discord.Interaction):
        await self.on_submit_cb(interaction, self.stars, self.feedback.value.strip() or None)


# ── Ticket creation ────────────────────────────────────────────────────────────

async def create_ticket(guild, member, category_id, answers=None, interaction=None):
    """Create a ticket channel + record. Returns (ok, message/channel)."""
    data, g = guild_conf(guild.id)

    if is_blacklisted(g, member.id):
        return False, "You are blacklisted from opening tickets."

    panel = g.get("panel_data")
    if not panel:
        return False, "No ticket panel configured. Ask staff to run /panel."

    cat = panel["categories"].get(category_id)
    if not cat or not cat.get("active", True):
        return False, "That category is unavailable."

    # Max open tickets per user
    max_open = cat["settings"].get("max_tickets_per_user", 1)
    open_count = sum(
        1 for t in g["tickets"].values()
        if t["user_id"] == str(member.id) and t["status"] == "open"
    )
    if open_count >= max_open:
        return False, f"You already have {open_count} open ticket(s)."

    g["counter"] += 1
    number = g["counter"]
    ticket_id = f"{guild.id}-{number}"

    parent = await get_or_create_ticket_category(guild, cat, data)
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        guild.me: discord.PermissionOverwrite(
            view_channel=True, send_messages=True, manage_channels=True,
            manage_messages=True, read_message_history=True,
        ),
        member: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
    }
    for role_id in cat.get("support_roles", []):
        role = guild.get_role(int(role_id))
        if role:
            overwrites[role] = discord.PermissionOverwrite(
                view_channel=True, send_messages=True, read_message_history=True,
            )

    try:
        channel = await guild.create_text_channel(
            name=channel_name_for(cat, member, number),
            category=parent,
            overwrites=overwrites,
            topic=f"Ticket #{number} | {member}",
        )
    except Exception as e:
        return False, f"Could not create channel: {e}"

    g["tickets"][ticket_id] = {
        "ticket_id": ticket_id,
        "guild_id": str(guild.id),
        "category_id": category_id,
        "channel_id": str(channel.id),
        "user_id": str(member.id),
        "status": "open",
        "answers": answers or [],
        "added_users": [],
        "removed_users": [],
        "control_message_id": None,
        "claimed_by": None,
        "claimed_at": None,
        "last_activity": time.time(),
        "closed_by": None,
        "closed_at": None,
        "close_reason": None,
        "rating": None,
        "number": number,
    }
    save(data)

    # Ping
    ping = ""
    if cat["settings"].get("ping_user", True):
        ping += f"{member.mention} "
    if cat["settings"].get("ping_role", False) and cat.get("support_roles"):
        ping += " ".join(f"<@&{r}>" for r in cat["support_roles"])

    # Welcome embed (control panel) — clean premium layout
    embed = discord.Embed(
        title=f"{cat['emoji']} {cat['name']} — Ticket #{number}",
        description=(
            cat["settings"].get("welcome_message")
            or f"Welcome {member.mention}! Please describe your issue and a staff member will assist you shortly."
        ),
        color=PRIMARY,
    )
    embed.set_author(name=member.display_name, icon_url=member.display_avatar.url)
    embed.set_footer(text=FOOTER, icon_url=ICON)

    # Answers section
    if answers:
        ans_text = "\n".join(f"**{a['question']}:** {a['answer']}" for a in answers)
        embed.add_field(name="📋 Answers", value=ans_text[:1024], inline=False)

    # Control hint (clean field)
    embed.add_field(
        name="🛠️ Ticket Controls",
        value="`Claim` to take it · `Close` to end it · `Add` to invite someone",
        inline=False,
    )

    if ping:
        await channel.send(ping)
    control = await channel.send(embed=embed, view=TicketControlView())
    try:
        await control.pin()
    except Exception:
        pass
    g["tickets"][ticket_id]["control_message_id"] = str(control.id)
    save(data)

    # DM the user
    if cat["settings"].get("dm_user_on_open", True):
        try:
            dm = discord.Embed(
                description=(
                    f"# 🎫 Ticket Created!\n"
                    f"### Ticket **#{number}** — {cat['emoji']} {cat['name']}\n\n"
                    f"Your ticket was opened in {channel.mention}.\n"
                    f"A staff member will assist you shortly. 🙌"
                ),
                color=SUCCESS,
            )
            dm.set_author(name=guild.name, icon_url=guild.icon.url if guild.icon else None)
            dm.set_footer(text=BRAND, icon_url=ICON)
            await member.send(embed=dm)
        except Exception:
            pass

    # Log channel
    log_ch = guild.get_channel(int(panel["logs"]["create"])) if panel["logs"].get("create") else None
    if log_ch:
        try:
            await log_ch.send(embed=discord.Embed(
                description=f"# 🎫 Ticket Created\n**{member.mention}** opened a ticket in {channel.mention}\nCategory: `{cat['name']}`",
                color=PRIMARY,
            ))
        except Exception:
            pass

    return True, channel.mention


# ── Views ──────────────────────────────────────────────────────────────────────

class PanelSelect(discord.ui.Select):
    def __init__(self, panel):
        self.panel = panel
        options = []
        for cid, c in panel["categories"].items():
            if not c.get("active", True):
                continue
            options.append(discord.SelectOption(
                label=c["name"][:100],
                value=cid,
                description=c.get("desc", "")[:50] or None,
                emoji=c.get("emoji"),
            ))
        super().__init__(placeholder=panel.get("placeholder", "Choose a category…"),
                         options=options[:25], min_values=1, max_values=1,
                         custom_id="mangoli_ticket_select")

    async def callback(self, interaction: discord.Interaction):
        category_id = self.values[0]
        data, g = guild_conf(interaction.guild_id)
        panel = g.get("panel_data")
        cat = panel["categories"].get(category_id)

        if cat and cat.get("questions"):
            modal = TicketQuestionsModal(
                title=cat["name"], questions=cat["questions"],
                on_submit=lambda i, answers: _after_questions(i, category_id, answers),
            )
            await interaction.response.send_modal(modal)
            return

        await interaction.response.defer(ephemeral=True)
        ok, msg = await create_ticket(interaction.guild, interaction.user, category_id)
        if ok:
            await interaction.followup.send(f"✅ Ticket created: {msg}", ephemeral=True)
        else:
            await interaction.followup.send(f"❌ {msg}", ephemeral=True)


async def _after_questions(interaction, category_id, answers):
    await interaction.response.defer(ephemeral=True)
    ok, msg = await create_ticket(interaction.guild, interaction.user, category_id, answers=answers)
    if ok:
        await interaction.followup.send(f"✅ Ticket created: {msg}", ephemeral=True)
    else:
        await interaction.followup.send(f"❌ {msg}", ephemeral=True)


class PanelView(discord.ui.View):
    def __init__(self, panel):
        super().__init__(timeout=None)
        self.panel = panel
        self.add_item(PanelSelect(panel))


class PanelButtonsView(discord.ui.View):
    def __init__(self, panel):
        super().__init__(timeout=None)
        self.panel = panel
        active = [cid for cid, c in panel["categories"].items() if c.get("active", True)]
        for cid in active[:25]:
            c = panel["categories"][cid]
            btn = discord.ui.Button(
                label=c["name"][:80], emoji=c.get("emoji"),
                style=discord.ButtonStyle.primary,
                custom_id=f"mangoli_ticket_btn_{cid}",
            )
            btn.callback = self._make_callback(cid)
            self.add_item(btn)

    def _make_callback(self, category_id):
        async def cb(interaction: discord.Interaction):
            data, g = guild_conf(interaction.guild_id)
            panel = g.get("panel_data")
            cat = panel["categories"].get(category_id)
            if cat and cat.get("questions"):
                modal = TicketQuestionsModal(
                    title=cat["name"], questions=cat["questions"],
                    on_submit=lambda i, answers: _after_questions(i, category_id, answers),
                )
                await interaction.response.send_modal(modal)
                return
            await interaction.response.defer(ephemeral=True)
            ok, msg = await create_ticket(interaction.guild, interaction.user, category_id)
            if ok:
                await interaction.followup.send(f"✅ Ticket created: {msg}", ephemeral=True)
            else:
                await interaction.followup.send(f"❌ {msg}", ephemeral=True)
        return cb


class AddUserSelect(discord.ui.UserSelect):
    def __init__(self, view):
        super().__init__(placeholder="Select a user to add…", min_values=1, max_values=1)
        self.parent_view = view

    async def callback(self, interaction: discord.Interaction):
        await self.parent_view.on_add_select(interaction, self.values[0])


class RemoveUserSelect(discord.ui.UserSelect):
    def __init__(self, view):
        super().__init__(placeholder="Select a user to remove…", min_values=1, max_values=1)
        self.parent_view = view

    async def callback(self, interaction: discord.Interaction):
        await self.parent_view.on_remove_select(interaction, self.values[0])


def _pe(name):
    """Return a discord.PartialEmoji for a custom emoji, or None."""
    try:
        from emojis import partial
        return partial(name)
    except ImportError:
        return None


async def dm_ticket_owner(guild, ticket, embed):
    """Send a DM to the ticket owner. Best-effort (ignores closed DMs)."""
    try:
        user = guild.get_member(int(ticket["user_id"])) or await guild.fetch_member(int(ticket["user_id"]))
        if user:
            await user.send(embed=embed)
    except Exception as e:
        print(f"[Tickets] DM to owner error: {e}")


class TicketControlView(discord.ui.View):
    """Buttons shown inside a ticket channel (persistent)."""

    def __init__(self):
        super().__init__(timeout=None)

    async def _ticket(self, interaction):
        data, g = guild_conf(interaction.guild_id)
        ticket = next((t for t in g["tickets"].values() if t["channel_id"] == str(interaction.channel_id)), None)
        return data, g, ticket

    async def _cat(self, g, ticket):
        panel = g.get("panel_data")
        if not panel:
            return None
        return panel.get("categories", {}).get(ticket["category_id"])

    async def _refresh_panel(self, interaction, ticket, cat):
        """Edit the pinned control message to reflect the current ticket state."""
        try:
            data, g = guild_conf(interaction.guild_id)
            msg_id = ticket.get("control_message_id")
            if not msg_id:
                return
            msg = await interaction.channel.fetch_message(int(msg_id))
            if not msg:
                return
            status = ticket.get("status", "open")
            claimed = ticket.get("claimed_by")
            lines = [
                f"# 🎫 Ticket #{ticket.get('number', '?')}",
                f"### {cat['emoji']} {cat['name']}" if cat else "",
                "",
                f"**Status:** {'🟢 Open' if status == 'open' else '🔴 Closed'}",
            ]
            if claimed:
                lines.append(f"**Claimed by:** <@{claimed}>")
            else:
                lines.append(f"**Claimed by:** —")
            embed = discord.Embed(description="\n".join([l for l in lines if l != ""]), color=SUCCESS if status == "open" else GOLD)
            embed.set_footer(text=FOOTER, icon_url=ICON)
            await msg.edit(embed=embed)
        except Exception as e:
            print(f"[Tickets] refresh panel error: {e}")

    @discord.ui.button(label="Claim", style=discord.ButtonStyle.primary, emoji=_pe("claim") or "🙋", custom_id="mangoli_claim")
    async def claim(self, interaction, button):
        data, g, ticket = await self._ticket(interaction)
        if not ticket:
            return await interaction.response.send_message("Not a ticket channel.", ephemeral=True)
        cat = await self._cat(g, ticket)
        if not is_staff(interaction.user, g, cat):
            return await interaction.response.send_message("Only staff can claim tickets.", ephemeral=True)
        if ticket.get("claimed_by"):
            if ticket["claimed_by"] == str(interaction.user.id):
                ticket["claimed_by"] = None
                ticket["claimed_at"] = None
                save(data)
                await interaction.response.send_message(
                    embed=discord.Embed(description=f"# 🔓 Ticket Unclaimed\nThis ticket is no longer assigned.", color=SUCCESS))
            else:
                await interaction.response.send_message(
                    f"Already claimed by <@{ticket['claimed_by']}>.", ephemeral=True)
            return
        ticket["claimed_by"] = str(interaction.user.id)
        ticket["claimed_at"] = _now_iso()
        save(data)
        await interaction.response.send_message(
            embed=discord.Embed(
                description=f"# 🙋 Ticket Claimed\n{interaction.user.mention} will be handling this ticket.",
                color=SUCCESS))
        await self._refresh_panel(interaction, ticket, cat)

        # Ping the ticket owner + DM them that a staff member claimed their ticket
        guild = interaction.guild
        try:
            owner = guild.get_member(int(ticket["user_id"]))
            if owner:
                await interaction.channel.send(
                    f"{owner.mention} 🎫 Your ticket is now being handled by {interaction.user.mention}!",
                    allowed_mentions=discord.AllowedMentions(users=True),
                )
                dm = discord.Embed(
                    title="🙋 Ticket Claimed!",
                    description=(
                        f"**Ticket #{ticket['number']}** — {cat['emoji']} {cat['name']}\n\n"
                        f"A staff member is now handling your ticket:\n"
                        f"**{interaction.user.display_name}** {interaction.user.mention}\n\n"
                        f"You'll get a reply in the ticket channel soon!"
                    ),
                    color=SUCCESS,
                )
                dm.set_author(name=guild.name, icon_url=guild.icon.url if guild.icon else None)
                dm.set_footer(text=BRAND, icon_url=ICON)
                await owner.send(embed=dm)
        except Exception as e:
            print(f"[Tickets] claim notify error: {e}")

    @discord.ui.button(label="Close", style=discord.ButtonStyle.danger, emoji=_pe("close") or "🔒", custom_id="mangoli_close")
    async def close(self, interaction, button):
        data, g, ticket = await self._ticket(interaction)
        if not ticket or ticket["status"] != "open":
            return await interaction.response.send_message("Ticket is not open.", ephemeral=True)
        cat = await self._cat(g, ticket)
        can_close = is_staff(interaction.user, g, cat) or (
            cat and cat["settings"].get("user_can_close", True) and str(interaction.user.id) == ticket["user_id"]
        )
        if not can_close:
            return await interaction.response.send_message("You can't close this ticket.", ephemeral=True)

        modal = CloseReasonModal(on_submit=lambda i, reason: _do_close(i, reason))
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Reopen", style=discord.ButtonStyle.success, emoji=_pe("reopen") or "🔓", custom_id="mangoli_reopen")
    async def reopen(self, interaction, button):
        data, g, ticket = await self._ticket(interaction)
        if not ticket:
            return await interaction.response.send_message("Not a ticket channel.", ephemeral=True)
        cat = await self._cat(g, ticket)
        if not is_staff(interaction.user, g, cat):
            return await interaction.response.send_message("Only staff can reopen.", ephemeral=True)
        if ticket["status"] != "closed":
            return await interaction.response.send_message("Ticket is already open.", ephemeral=True)
        ticket["status"] = "open"
        save(data)
        await rename_ticket_channel(_bot, interaction.guild_id, ticket, closed=False)
        await interaction.response.send_message(
            embed=discord.Embed(description=f"# 🔓 Ticket Reopened\nReopened by {interaction.user.mention}.", color=SUCCESS))
        await self._refresh_panel(interaction, ticket, cat)

    @discord.ui.button(label="Transcript", style=discord.ButtonStyle.primary, emoji=_pe("transcript") or "📄", custom_id="mangoli_transcript", row=1)
    async def transcript(self, interaction, button):
        data, g, ticket = await self._ticket(interaction)
        if not ticket:
            return await interaction.response.send_message("Not a ticket channel.", ephemeral=True)
        await interaction.response.defer(ephemeral=True)
        try:
            transcript = await build_html_transcript(interaction.channel, ticket)
            file = discord.File(io.StringIO(transcript), filename=f"transcript-{ticket['number']}.html")
            await interaction.followup.send(
                embed=discord.Embed(description=f"# 📄 Transcript Ready\nTicket #{ticket['number']}", color=SUCCESS),
                file=file,
            )
        except Exception as e:
            await interaction.followup.send(f"❌ Could not generate transcript: {e}", ephemeral=True)

    @discord.ui.button(label="Add", style=discord.ButtonStyle.secondary, emoji=_pe("add") or "➕", custom_id="mangoli_add", row=1)
    async def add(self, interaction, button):
        data, g, ticket = await self._ticket(interaction)
        if not ticket:
            return await interaction.response.send_message("Not a ticket channel.", ephemeral=True)
        cat = await self._cat(g, ticket)
        if not is_staff(interaction.user, g, cat):
            return await interaction.response.send_message("Only staff can add users.", ephemeral=True)
        if len(ticket.get("added_users", [])) >= 5:
            return await interaction.response.send_message("Max 5 added users reached.", ephemeral=True)
        view = discord.ui.View(timeout=180)
        view.add_item(AddUserSelect(self))
        await interaction.response.send_message("👥 Select a user to add:", view=view, ephemeral=True)

    async def on_add_select(self, interaction, member):
        data, g, ticket = await self._ticket(interaction)
        if not ticket:
            return
        cat = await self._cat(g, ticket)
        if not is_staff(interaction.user, g, cat):
            return await interaction.response.send_message("Only staff can add users.", ephemeral=True)
        if str(member.id) == ticket["user_id"]:
            return await interaction.response.send_message("The ticket owner is already in the ticket.", ephemeral=True)
        if any(a["user_id"] == str(member.id) for a in ticket.get("added_users", [])):
            return await interaction.response.send_message("User already added.", ephemeral=True)
        if len(ticket.get("added_users", [])) >= 5:
            return await interaction.response.send_message("Max 5 added users reached.", ephemeral=True)
        ticket.setdefault("added_users", []).append({"user_id": str(member.id), "added_by": str(interaction.user.id)})
        save(data)
        await interaction.channel.set_permissions(member, view_channel=True, send_messages=True, read_message_history=True)
        await interaction.response.send_message(
            embed=discord.Embed(description=f"# ➕ User Added\n{member.mention} now has access to this ticket.", color=SUCCESS))

    @discord.ui.button(label="Remove", style=discord.ButtonStyle.secondary, emoji=_pe("remove") or "➖", custom_id="mangoli_remove", row=1)
    async def remove(self, interaction, button):
        data, g, ticket = await self._ticket(interaction)
        if not ticket:
            return await interaction.response.send_message("Not a ticket channel.", ephemeral=True)
        cat = await self._cat(g, ticket)
        if not is_staff(interaction.user, g, cat):
            return await interaction.response.send_message("Only staff can remove users.", ephemeral=True)
        view = discord.ui.View(timeout=180)
        view.add_item(RemoveUserSelect(self))
        await interaction.response.send_message("👥 Select a user to remove:", view=view, ephemeral=True)

    async def on_remove_select(self, interaction, member):
        data, g, ticket = await self._ticket(interaction)
        if not ticket:
            return
        cat = await self._cat(g, ticket)
        if not is_staff(interaction.user, g, cat):
            return await interaction.response.send_message("Only staff can remove users.", ephemeral=True)
        ticket["added_users"] = [a for a in ticket.get("added_users", []) if a["user_id"] != str(member.id)]
        ticket.setdefault("removed_users", []).append({"user_id": str(member.id), "removed_by": str(interaction.user.id)})
        save(data)
        await interaction.channel.set_permissions(member, overwrite=None)
        await interaction.response.send_message(
            embed=discord.Embed(description=f"# ➖ User Removed\n{member.mention} no longer has access.", color=SUCCESS))

    @discord.ui.button(label="Ping Staff", style=discord.ButtonStyle.primary, emoji=_pe("ping") or "🔔", custom_id="mangoli_ping", row=2)
    async def ping_staff(self, interaction, button):
        data, g, ticket = await self._ticket(interaction)
        if not ticket:
            return await interaction.response.send_message("Not a ticket channel.", ephemeral=True)
        cat = await self._cat(g, ticket)
        support = cat.get("support_roles", []) if cat else []
        roles_ping = " ".join(f"<@&{r}>" for r in support)
        await interaction.response.send_message(
            f"🔔 **Ticket #{ticket.get('number','?')}** needs attention! {roles_ping}"
            if roles_ping else
            f"🔔 **Ticket #{ticket.get('number','?')}** needs attention! Staff roles are not configured.",
            allowed_mentions=discord.AllowedMentions(roles=True),
        )

    @discord.ui.button(label="Delete", style=discord.ButtonStyle.danger, emoji=_pe("delete") or "🗑️", custom_id="mangoli_delete", row=2)
    async def delete(self, interaction, button):
        data, g, ticket = await self._ticket(interaction)
        if not ticket:
            return await interaction.response.send_message("Not a ticket channel.", ephemeral=True)
        cat = await self._cat(g, ticket)
        if not is_staff(interaction.user, g, cat):
            return await interaction.response.send_message("Only staff can delete.", ephemeral=True)

        # Confirmation
        class Confirm(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=60)

            @discord.ui.button(label="Confirm Delete", style=discord.ButtonStyle.danger, emoji="🗑️")
            async def yes(self, i: discord.Interaction, b):
                data, g = guild_conf(i.guild_id)
                tk = next((t for t in g["tickets"].values() if t["channel_id"] == str(i.channel_id)), None)
                if tk:
                    g["tickets"].pop(tk["ticket_id"], None)
                    save(data)
                await i.response.send_message("🗑️ Deleting ticket channel…")
                await delete_ticket_channel(_bot, i.guild_id, tk if tk else {})

            @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
            async def no(self, i: discord.Interaction, b):
                await i.response.send_message("❌ Delete cancelled.", ephemeral=True)

        await interaction.response.send_message(
            embed=discord.Embed(description="# ⚠️ Confirm Delete\nThis will **permanently delete** this ticket channel.\nThis cannot be undone!", color=ERROR),
            view=Confirm(),
            ephemeral=True,
        )


async def _do_close(interaction, reason):
    """Close flow: transcript + rating + DM + log."""
    await interaction.response.defer()
    data, g = guild_conf(interaction.guild_id)
    ticket = next((t for t in g["tickets"].values() if t["channel_id"] == str(interaction.channel_id)), None)
    if not ticket or ticket["status"] != "open":
        await interaction.followup.send("Ticket is not open.", ephemeral=True)
        return

    ticket["status"] = "closed"
    ticket["closed_by"] = str(interaction.user.id)
    ticket["closed_at"] = _now_iso()
    ticket["close_reason"] = reason
    save(data)

    channel = interaction.channel
    panel = g.get("panel_data")
    cat = panel["categories"].get(ticket["category_id"]) if panel else None

    # HTML transcript
    transcript = await build_html_transcript(channel, ticket)
    transcript_file = discord.File(
        io.StringIO(transcript), filename=f"transcript-{ticket['number']}.html"
    ) if transcript else None

    # Log channel
    log_ch = interaction.guild.get_channel(int(panel["logs"]["close"])) if panel and panel["logs"].get("close") else None
    if log_ch:
        try:
            embed = discord.Embed(
                description=(
                    f"# 🔒 Ticket Closed\n"
                    f"**User:** <@{ticket['user_id']}>\n"
                    f"**Closed by:** <@{ticket['closed_by']}>\n"
                    f"**Category:** `{cat['name'] if cat else '?'}`\n"
                    + (f"**Reason:** {reason}\n" if reason else "")
                ),
                color=GOLD,
            )
            files = [transcript_file] if transcript_file else []
            await log_ch.send(embed=embed, files=files)
        except Exception as e:
            print(f"[Tickets] close log error: {e}")

    # DM user — full receipt with ALL ticket details
    if cat and cat.get("settings", {}).get("dm_user_on_close", True):
        try:
            user = interaction.guild.get_member(int(ticket["user_id"])) or await interaction.guild.fetch_member(int(ticket["user_id"]))
            if user:
                closer = interaction.guild.get_member(int(ticket["closed_by"])) if ticket.get("closed_by") and ticket.get("closed_by") != "dashboard" else None
                embed = discord.Embed(
                    title="🔒 Ticket Closed",
                    description="Here's a summary of your ticket. Thank you for reaching out! 💜",
                    color=GOLD,
                )
                embed.add_field(name="🎫 Ticket", value=f"`#{ticket['number']}`", inline=True)
                embed.add_field(name="📂 Category", value=f"{cat['emoji']} {cat['name']}", inline=True)
                embed.add_field(name="🙋 Closed By", value=closer.mention if closer else "Staff", inline=True)
                if reason:
                    embed.add_field(name="📝 Reason", value=reason, inline=False)
                if ticket.get("claimed_by") and ticket.get("claimed_by") != str(ticket.get("closed_by", "")):
                    claimer = interaction.guild.get_member(int(ticket["claimed_by"]))
                    if claimer:
                        embed.add_field(name="👤 Handled By", value=claimer.mention, inline=True)
                if ticket.get("answers"):
                    ans = "\n".join(f"**{a['question']}:** {a['answer']}" for a in ticket["answers"])
                    embed.add_field(name="📋 Your Answers", value=ans[:1024], inline=False)
                embed.add_field(name="⭐ Rate Us", value="You'll get a rating prompt to share your experience!", inline=False)
                embed.set_author(name=interaction.guild.name, icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
                embed.set_footer(text=BRAND, icon_url=ICON)
                await user.send(embed=embed)
        except Exception as e:
            print(f"[Tickets] DM close error: {e}")

    # Rating prompt
    rating_view = RatingView(ticket["ticket_id"])
    await channel.send(
        embed=discord.Embed(
            description="# ⭐ Rate Your Experience\nTap a star rating below!",
            color=GOLD,
        ),
        view=rating_view,
    )

    # Lock channel (deny send for the opener + added users)
    try:
        user = interaction.guild.get_member(int(ticket["user_id"]))
        if user:
            await channel.set_permissions(user, send_messages=False)
    except Exception:
        pass
    for au in ticket.get("added_users", []):
        try:
            m = interaction.guild.get_member(int(au["user_id"]))
            if m:
                await channel.set_permissions(m, send_messages=False)
        except Exception:
            pass

    # Rename channel to show it's closed
    await rename_ticket_channel(_bot, interaction.guild_id, ticket, closed=True)

    await interaction.followup.send(
        f"{E['close']} Ticket closed by {interaction.user.mention}."
        + ("" if transcript_file else "\n⚠️ Transcript unavailable.")
    )

    # Refresh the pinned control panel to show closed status
    try:
        msg_id = ticket.get("control_message_id")
        if msg_id:
            msg = await channel.fetch_message(int(msg_id))
            if msg:
                embed = discord.Embed(
                    description=(
                        f"# 🎫 Ticket #{ticket['number']}\n"
                        f"### 🔴 Closed\n\n"
                        f"**Closed by:** {interaction.user.mention}\n"
                        + (f"**Reason:** {reason}\n" if reason else "")
                    ),
                    color=GOLD,
                )
                embed.set_footer(text=FOOTER, icon_url=ICON)
                await msg.edit(embed=embed)
    except Exception as e:
        print(f"[Tickets] close panel refresh error: {e}")


class RatingView(discord.ui.View):
    def __init__(self, ticket_id):
        super().__init__(timeout=7 * 24 * 3600)  # non-persistent (7 days)
        self.ticket_id = ticket_id
        for stars in range(1, 6):
            btn = discord.ui.Button(
                label=str(stars), emoji="⭐", style=discord.ButtonStyle.secondary,
                custom_id=f"mangoli_rate_{ticket_id}_{stars}",
            )
            btn.callback = self._make(stars)
            self.add_item(btn)

    def _make(self, stars):
        async def cb(interaction: discord.Interaction):
            modal = FeedbackModal(stars, on_submit=self._rate)
            await interaction.response.send_modal(modal)
        return cb

    async def _rate(self, interaction, stars, feedback):
        data, g = guild_conf(interaction.guild_id)
        ticket = g["tickets"].get(self.ticket_id)
        if ticket:
            ticket["rating"] = {"stars": stars, "feedback": feedback, "rated_at": _now_iso()}
            save(data)
        panel = g.get("panel_data")
        cat = panel["categories"].get(ticket["category_id"]) if panel and ticket.get("category_id") else None
        log_ch = interaction.guild.get_channel(int(panel["logs"]["rating"])) if panel and panel["logs"].get("rating") else None
        if log_ch:
            try:
                await log_ch.send(embed=discord.Embed(
                    description=(
                        f"# ⭐ Ticket Rated\n"
                        f"**Rating:** {'⭐' * stars}{'☆' * (5 - stars)} ({stars}/5)\n"
                        f"**User:** <@{ticket['user_id'] if ticket else '?'}>\n"
                        + (f"**Feedback:** {feedback}\n" if feedback else "")
                    ),
                    color=GOLD,
                ))
            except Exception:
                pass

        # DM the ticket owner a full receipt of their rating + ticket details
        if ticket:
            try:
                owner = interaction.guild.get_member(int(ticket["user_id"])) or await interaction.guild.fetch_member(int(ticket["user_id"]))
                if owner:
                    dm = discord.Embed(
                        title="⭐ Thanks for rating!",
                        description=(
                            f"**Ticket #{ticket.get('number')}**\n"
                            + (f"**Category:** {cat['emoji']} {cat['name']}\n" if cat else "")
                            + f"**Rating:** {'⭐' * stars}{'☆' * (5 - stars)} ({stars}/5)\n"
                            + (f"**Feedback:** {feedback}\n" if feedback else "")
                            + (f"**Closed by:** <@{ticket['closed_by']}>\n" if ticket.get("closed_by") and ticket.get("closed_by") != "dashboard" else "")
                            + (f"**Close reason:** {ticket.get('close_reason')}\n" if ticket.get("close_reason") else "")
                        ),
                        color=GOLD,
                    )
                    dm.set_author(name=interaction.guild.name, icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
                    dm.set_footer(text=BRAND, icon_url=ICON)
                    await owner.send(embed=dm)
            except Exception as e:
                print(f"[Tickets] rating DM error: {e}")

        await interaction.response.send_message("✅ Thanks for your feedback!", ephemeral=True)


async def build_html_transcript(channel, ticket):
    """Generate a simple HTML transcript of the ticket channel."""
    lines = []
    try:
        async for msg in channel.history(limit=500, oldest_first=True):
            author = html_escape(str(msg.author))
            ts = msg.created_at.strftime("%Y-%m-%d %H:%M:%S")
            content = msg.content or (msg.embeds[0].description if msg.embeds else "")
            lines.append(f'<div class="msg"><span class="ts">{ts}</span> <b>{author}:</b> {html_escape(content)}</div>')
    except Exception as e:
        lines.append(f"<p>Error: {html_escape(str(e))}</p>")

    body = "\n".join(lines)
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Transcript #{ticket['number']}</title>
<style>
body {{ font-family: sans-serif; background:#1e1e2e; color:#e0e0e0; padding:20px; }}
h1 {{ color:#8b5cf6; }}
.msg {{ border-bottom:1px solid #333; padding:6px 0; }}
.ts {{ color:#888; font-size:12px; }}
</style></head><body>
<h1>Ticket #{ticket['number']} — Transcript</h1>
<p>Generated {_now_iso()}</p>
{body}
</body></html>"""


# ── Auto-close loop ────────────────────────────────────────────────────────────

async def autoclose_loop(bot):
    await bot.wait_until_ready()
    while True:
        try:
            data = load()
            changed = False
            for g in data.get("guilds", {}).values():
                for ticket in g.get("tickets", {}).values():
                    if ticket.get("status") != "open":
                        continue
                    last = ticket.get("last_activity", time.time())
                    if time.time() - last > AUTOCLOSE_HOURS * 3600:
                        guild = bot.get_guild(int(ticket["guild_id"]))
                        if guild:
                            channel = guild.get_channel(int(ticket["channel_id"]))
                            if channel:
                                ticket["status"] = "closed"
                                ticket["closed_by"] = "auto"
                                ticket["closed_at"] = _now_iso()
                                ticket["close_reason"] = f"Auto-closed after {AUTOCLOSE_HOURS}h inactivity"
                                changed = True
                                try:
                                    await channel.send(embed=discord.Embed(
                                        description=f"# ⏰ Auto-Closed\nThis ticket was closed after {AUTOCLOSE_HOURS}h of inactivity.",
                                        color=WARNING,
                                    ))
                                except Exception:
                                    pass
            if changed:
                save(data)
        except Exception as e:
            print(f"[Tickets] autoclose error: {e}")
        await asyncio.sleep(300)  # every 5 min


# ── Commands ───────────────────────────────────────────────────────────────────

def register(bot):
    """Register ticket commands + views + listeners."""
    _set_bot(bot)
    # Fixed persistent views (buttons only, no per-guild data)
    bot.add_view(TicketControlView())

    # Re-register every existing panel's view so panels survive restarts
    data = load()
    for g in data.get("guilds", {}).values():
        panel = g.get("panel_data")
        if panel and panel.get("message_id"):
            if panel.get("display_type") == "buttons":
                bot.add_view(PanelButtonsView(panel))
            else:
                bot.add_view(PanelView(panel))

    @bot.listen("on_message")
    async def track_ticket_activity(message):
        if message.guild is None or message.author.bot:
            return
        data = load()
        g = data.get("guilds", {}).get(str(message.guild.id))
        if not g:
            return
        for ticket in g.get("tickets", {}).values():
            if ticket.get("channel_id") == str(message.channel.id) and ticket.get("status") == "open":
                ticket["last_activity"] = time.time()
                save(data)
                return

    @bot.tree.command(name="panel", description="🎫 Create & deploy the ticket panel")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.describe(
        display="Display mode for the panel",
        send_here="Post the panel in this channel",
    )
    @app_commands.choices(display=[
        app_commands.Choice(name="Dropdown Menu", value="select"),
        app_commands.Choice(name="Buttons", value="buttons"),
    ])
    async def panel_command(interaction: discord.Interaction, display: str = "select", send_here: bool = True):
        data, g = guild_conf(interaction.guild_id)
        if g.get("panel_data") is None:
            g["panel_data"] = _default_panel(interaction.guild_id)
        g["panel_data"]["display_type"] = display
        g["panel_data"]["channel_id"] = str(interaction.channel_id)
        save(data)

        if not send_here:
            await interaction.response.send_message(
                f"✅ Panel configured ({display} mode). Run `/panel send_here:True` to post it.",
                ephemeral=True,
            )
            return

        panel = g["panel_data"]
        msg = panel["panel_message"]
        embed = discord.Embed(
            description=f"# {msg['title']}\n### {msg['description']}",
            color=PRIMARY,
        )
        embed.set_author(name=BRAND, icon_url=ICON)
        embed.set_footer(text=FOOTER, icon_url=ICON)

        if display == "buttons":
            view = PanelButtonsView(panel)
        else:
            view = PanelView(panel)

        sent = await interaction.channel.send(embed=embed, view=view)
        panel["message_id"] = str(sent.id)
        save(data)
        await interaction.response.send_message("✅ Ticket panel posted!", ephemeral=True)

    @bot.tree.command(name="settings", description="⚙️ Configure ticket settings")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.describe(
        staff_role="Add/remove a staff role",
        transcript_channel="Channel for closed-ticket transcripts",
    )
    async def settings_command(interaction: discord.Interaction, staff_role: discord.Role = None, transcript_channel: discord.TextChannel = None):
        data, g = guild_conf(interaction.guild_id)
        if staff_role:
            if str(staff_role.id) in g["staff_roles"]:
                g["staff_roles"].remove(str(staff_role.id))
                role_status = f"removed {staff_role.mention}"
            else:
                g["staff_roles"].append(str(staff_role.id))
                role_status = f"added {staff_role.mention}"
        else:
            role_status = "unchanged"
        if transcript_channel and g.get("panel_data"):
            g["panel_data"]["logs"]["close"] = str(transcript_channel.id)
        save(data)

        embed = discord.Embed(
            description=(
                f"# ⚙️ Ticket Settings\n"
                f"**Staff roles:** {', '.join(f'<@&{r}>' for r in g['staff_roles']) or 'None'}\n"
                f"**Transcript channel:** <#{g['panel_data']['logs']['close']}>" if g.get("panel_data") and g["panel_data"]["logs"].get("close") else "Not set"
            ),
            color=PRIMARY,
        )
        embed.set_footer(text=FOOTER, icon_url=ICON)
        await interaction.response.send_message(embed=embed)

    @bot.tree.command(name="blacklist", description="🚫 Blacklist a user from opening tickets")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.describe(action="add, remove, or list", user="User to blacklist/unblacklist")
    @app_commands.choices(action=[
        app_commands.Choice(name="Add", value="add"),
        app_commands.Choice(name="Remove", value="remove"),
        app_commands.Choice(name="List", value="list"),
    ])
    async def blacklist_command(interaction: discord.Interaction, action: str, user: discord.User = None):
        data, g = guild_conf(interaction.guild_id)
        if action == "list":
            if not g["blacklist"]:
                await interaction.response.send_message("🚫 Blacklist is empty.", ephemeral=True)
                return
            lines = "\n".join(f"• <@{b['user_id']}>" + (f" — {b.get('reason')}" if b.get("reason") else "") for b in g["blacklist"])
            await interaction.response.send_message(embed=discord.Embed(
                description=f"# 🚫 Blacklist\n{lines}", color=ERROR))
            return
        if user is None:
            await interaction.response.send_message("❌ Provide a user.", ephemeral=True)
            return
        uid = str(user.id)
        if action == "add":
            if not is_blacklisted(g, user.id):
                g["blacklist"].append({"user_id": uid, "reason": None, "by": str(interaction.user.id)})
                save(data)
                await interaction.response.send_message(f"🚫 Blacklisted {user.mention}.")
            else:
                await interaction.response.send_message("Already blacklisted.", ephemeral=True)
        else:
            g["blacklist"] = [b for b in g["blacklist"] if b["user_id"] != uid]
            save(data)
            await interaction.response.send_message(f"✅ Unblacklisted {user.mention}.")

    @bot.tree.command(name="claim", description="🙋 Claim this ticket")
    async def claim_command(interaction: discord.Interaction):
        data, g = guild_conf(interaction.guild_id)
        ticket = next((t for t in g["tickets"].values() if t["channel_id"] == str(interaction.channel_id)), None)
        if not ticket or ticket["status"] != "open":
            await interaction.response.send_message("Not an open ticket.", ephemeral=True)
            return
        cat = g["panel_data"]["categories"].get(ticket["category_id"]) if g.get("panel_data") else None
        if not is_staff(interaction.user, g, cat):
            await interaction.response.send_message("Only staff can claim.", ephemeral=True)
            return
        if ticket.get("claimed_by"):
            await interaction.response.send_message(f"Already claimed by <@{ticket['claimed_by']}>.", ephemeral=True)
            return
        ticket["claimed_by"] = str(interaction.user.id)
        ticket["claimed_at"] = _now_iso()
        save(data)
        await interaction.response.send_message(f"{E['claim']} {interaction.user.mention} claimed this ticket.")

    @bot.tree.command(name="unclaim", description="🔓 Unclaim this ticket")
    async def unclaim_command(interaction: discord.Interaction):
        data, g = guild_conf(interaction.guild_id)
        ticket = next((t for t in g["tickets"].values() if t["channel_id"] == str(interaction.channel_id)), None)
        if not ticket:
            await interaction.response.send_message("Not a ticket channel.", ephemeral=True)
            return
        ticket["claimed_by"] = None
        save(data)
        await interaction.response.send_message(f"{E['unlock']} Ticket unclaimed.")

    @bot.tree.command(name="close", description="🔒 Close this ticket")
    @app_commands.describe(reason="Reason for closing")
    async def close_command(interaction: discord.Interaction, reason: str = None):
        data, g = guild_conf(interaction.guild_id)
        ticket = next((t for t in g["tickets"].values() if t["channel_id"] == str(interaction.channel_id)), None)
        if not ticket or ticket["status"] != "open":
            await interaction.response.send_message("Not an open ticket.", ephemeral=True)
            return
        cat = g["panel_data"]["categories"].get(ticket["category_id"]) if g.get("panel_data") else None
        can_close = is_staff(interaction.user, g, cat) or (
            cat and cat["settings"].get("user_can_close", True) and str(interaction.user.id) == ticket["user_id"]
        )
        if not can_close:
            await interaction.response.send_message("You can't close this ticket.", ephemeral=True)
            return
        await _do_close(interaction, reason)

    @bot.tree.command(name="reopen", description="🔓 Reopen a closed ticket")
    async def reopen_command(interaction: discord.Interaction):
        data, g = guild_conf(interaction.guild_id)
        ticket = next((t for t in g["tickets"].values() if t["channel_id"] == str(interaction.channel_id)), None)
        if not ticket:
            await interaction.response.send_message("Not a ticket channel.", ephemeral=True)
            return
        cat = g["panel_data"]["categories"].get(ticket["category_id"]) if g.get("panel_data") else None
        if not is_staff(interaction.user, g, cat):
            await interaction.response.send_message("Only staff can reopen.", ephemeral=True)
            return
        ticket["status"] = "open"
        save(data)
        await rename_ticket_channel(_bot, interaction.guild_id, ticket, closed=False)
        await interaction.response.send_message(f"{E['reopen']} Ticket reopened.")

    @bot.tree.command(name="ticketdelete", description="🗑️ Delete this ticket channel")
    async def delete_command(interaction: discord.Interaction):
        data, g = guild_conf(interaction.guild_id)
        ticket = next((t for t in g["tickets"].values() if t["channel_id"] == str(interaction.channel_id)), None)
        if not ticket:
            await interaction.response.send_message("Not a ticket channel.", ephemeral=True)
            return
        cat = g["panel_data"]["categories"].get(ticket["category_id"]) if g.get("panel_data") else None
        if not is_staff(interaction.user, g, cat):
            await interaction.response.send_message("Only staff can delete.", ephemeral=True)
            return
        await interaction.response.send_message("🗑️ Deleting…")
        g["tickets"].pop(ticket["ticket_id"], None)
        save(data)
        await delete_ticket_channel(bot, interaction.guild_id, ticket)

    @bot.tree.command(name="ticketadd", description="➕ Add a user to this ticket")
    @app_commands.describe(user="User to add")
    async def add_command(interaction: discord.Interaction, user: discord.Member):
        data, g = guild_conf(interaction.guild_id)
        ticket = next((t for t in g["tickets"].values() if t["channel_id"] == str(interaction.channel_id)), None)
        if not ticket:
            await interaction.response.send_message("Not a ticket channel.", ephemeral=True)
            return
        cat = g["panel_data"]["categories"].get(ticket["category_id"]) if g.get("panel_data") else None
        if not is_staff(interaction.user, g, cat):
            await interaction.response.send_message("Only staff can add users.", ephemeral=True)
            return
        if len(ticket.get("added_users", [])) >= 5:
            await interaction.response.send_message("Max 5 added users.", ephemeral=True)
            return
        ticket.setdefault("added_users", []).append({"user_id": str(user.id), "added_by": str(interaction.user.id)})
        save(data)
        await interaction.channel.set_permissions(user, view_channel=True, send_messages=True, read_message_history=True)
        await interaction.response.send_message(f"{E['add']} Added {user.mention}.")

    @bot.tree.command(name="ticketremove", description="➖ Remove a user from this ticket")
    @app_commands.describe(user="User to remove")
    async def remove_command(interaction: discord.Interaction, user: discord.Member):
        data, g = guild_conf(interaction.guild_id)
        ticket = next((t for t in g["tickets"].values() if t["channel_id"] == str(interaction.channel_id)), None)
        if not ticket:
            await interaction.response.send_message("Not a ticket channel.", ephemeral=True)
            return
        cat = g["panel_data"]["categories"].get(ticket["category_id"]) if g.get("panel_data") else None
        if not is_staff(interaction.user, g, cat):
            await interaction.response.send_message("Only staff can remove users.", ephemeral=True)
            return
        ticket["added_users"] = [a for a in ticket.get("added_users", []) if a["user_id"] != str(user.id)]
        ticket.setdefault("removed_users", []).append({"user_id": str(user.id), "removed_by": str(interaction.user.id)})
        save(data)
        await interaction.channel.set_permissions(user, overwrite=None)
        await interaction.response.send_message(f"{E['remove']} Removed {user.mention}.")

    @bot.tree.command(name="transcript", description="📄 Generate an HTML transcript of this ticket")
    async def transcript_command(interaction: discord.Interaction):
        data, g = guild_conf(interaction.guild_id)
        ticket = next((t for t in g["tickets"].values() if t["channel_id"] == str(interaction.channel_id)), None)
        if not ticket:
            await interaction.response.send_message("Not a ticket channel.", ephemeral=True)
            return
        await interaction.response.defer()
        transcript = await build_html_transcript(interaction.channel, ticket)
        file = discord.File(io.StringIO(transcript), filename=f"transcript-{ticket['number']}.html")
        await interaction.followup.send(
            embed=discord.Embed(description=f"# 📄 Transcript Ready\nTicket #{ticket['number']}", color=SUCCESS),
            file=file,
        )

    # Start the auto-close loop (deferred to setup_hook via start_tasks)
    print("[Tickets] Ticket system loaded")


async def start_tasks(bot):
    """Start background tasks (called from setup_hook)."""
    if not getattr(bot, "_ticket_autoclose_started", False):
        bot._ticket_autoclose_started = True
        bot.loop.create_task(autoclose_loop(bot))
        print("[Tickets] Auto-close loop started")


# ═══════════════════════════════════════════════════════════════════════════════
# DASHBOARD API HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def build_panel_embed(panel):
    """Build the panel embed (reused for the real panel + dashboard preview)."""
    msg = panel.get("panel_message", {})
    embed = discord.Embed(
        title=msg.get('title', 'Open a Ticket'),
        description=msg.get('description', 'Select a category below to create a ticket'),
        color=PRIMARY,
    )
    embed.set_author(name=panel.get("name", BRAND), icon_url=ICON)
    # list categories
    cats = [c for c in panel["categories"].values() if c.get("active", True)]
    cat_text = "\n".join(f"{c['emoji']} **{c['name']}** — {c.get('desc','')}" for c in cats)
    if cat_text:
        embed.add_field(name="📂 Categories", value=cat_text[:1024], inline=False)
    embed.set_footer(text=FOOTER, icon_url=ICON)
    return embed


def get_dashboard_config(guild_id):
    """Full ticket config for the dashboard (panel + staff + blacklist + stats)."""
    data, g = guild_conf(guild_id, create=False)
    if g is None:
        return {"configured": False}
    panel = g.get("panel_data")
    tickets = g.get("tickets", {})
    open_count = sum(1 for t in tickets.values() if t.get("status") == "open")
    closed_count = sum(1 for t in tickets.values() if t.get("status") == "closed")
    # merge server-wide staff roles into the panel dict so the frontend can read them together
    if panel is not None:
        panel = dict(panel)
        panel["staff_roles"] = g.get("staff_roles", [])
    return {
        "configured": panel is not None,
        "panel": panel,
        "staff_roles": g.get("staff_roles", []),
        "blacklist": g.get("blacklist", []),
        "stats": {
            "total": len(tickets),
            "open": open_count,
            "closed": closed_count,
        },
    }


def set_dashboard_config(guild_id, config):
    """Update panel config from the dashboard. Returns the updated config."""
    data, g = guild_conf(guild_id, create=True)
    if g.get("panel_data") is None:
        g["panel_data"] = _default_panel(guild_id)
    panel = g["panel_data"]

    # Panel-level fields
    for key in ["name", "display_type", "placeholder", "welcome_message", "channel_id"]:
        if key in config:
            panel[key] = config[key]

    # panel_message
    if "panel_message" in config and isinstance(config["panel_message"], dict):
        for k in ["title", "description"]:
            if k in config["panel_message"]:
                panel["panel_message"][k] = config["panel_message"][k]

    # log channels
    if "logs" in config and isinstance(config["logs"], dict):
        for k in ["create", "close", "rating"]:
            if k in config["logs"]:
                panel["logs"][k] = config["logs"][k]

    # categories — full per-category config
    if "categories" in config and isinstance(config["categories"], dict):
        for cid, cdata in config["categories"].items():
            if cid not in panel["categories"]:
                # allow adding a new category from the dashboard
                panel["categories"][cid] = {
                    "id": cid, "name": cdata.get("name", cid), "emoji": "🎫", "desc": "",
                    "support_roles": [], "ticket_category_id": None,
                    "naming_format": "ticket-{username}",
                    "settings": dict(DEFAULT_SETTINGS), "questions": [], "active": True,
                }
            cat = panel["categories"][cid]
            for k in ["name", "emoji", "desc", "active", "naming_format", "ticket_category_id", "support_roles"]:
                if k in cdata:
                    cat[k] = cdata[k]
            # nested settings
            if "settings" in cdata and isinstance(cdata["settings"], dict):
                for k, v in cdata["settings"].items():
                    if k in cat["settings"]:
                        cat["settings"][k] = v
            # questions
            if "questions" in cdata:
                cat["questions"] = cdata["questions"]

    # categories to delete
    if "remove_categories" in config and isinstance(config["remove_categories"], list):
        for cid in config["remove_categories"]:
            panel["categories"].pop(cid, None)

    # staff roles (server-wide)
    if "staff_roles" in config:
        g["staff_roles"] = [str(r) for r in config["staff_roles"]]

    save(data)
    return get_dashboard_config(guild_id)


def get_dashboard_tickets(guild_id, bot=None):
    """List all tickets with member/channel info for the dashboard."""
    data, g = guild_conf(guild_id, create=False)
    if g is None:
        return []
    out = []
    for ticket in g.get("tickets", {}).values():
        item = dict(ticket)
        # resolve names if bot available
        if bot:
            guild = bot.get_guild(int(guild_id))
            if guild:
                user = guild.get_member(int(ticket["user_id"]))
                item["user_name"] = user.display_name if user else f"User {ticket['user_id']}"
                item["user_avatar"] = str(user.display_avatar.url) if user and user.display_avatar else None
                ch = guild.get_channel(int(ticket["channel_id"])) if ticket.get("channel_id") else None
                item["channel_name"] = ch.name if ch else None
                if ticket.get("claimed_by"):
                    claimer = guild.get_member(int(ticket["claimed_by"]))
                    item["claimed_name"] = claimer.display_name if claimer else None
                panel = g.get("panel_data")
                cat = panel["categories"].get(ticket["category_id"]) if panel else None
                item["category_name"] = cat["name"] if cat else ticket["category_id"]
                item["category_emoji"] = cat["emoji"] if cat else "🎫"
        out.append(item)
    # sort: open first, then newest
    out.sort(key=lambda t: (t.get("status") != "open", -t.get("number", 0)))
    return out


def ticket_action(guild_id, ticket_id, action, bot=None):
    """Close / reopen / delete a ticket from the dashboard. Returns (ok, msg)."""
    data, g = guild_conf(guild_id, create=False)
    if g is None:
        return False, "Guild not configured"
    ticket = g.get("tickets", {}).get(ticket_id)
    if not ticket:
        return False, "Ticket not found"

    if action == "close" and ticket["status"] == "open":
        ticket["status"] = "closed"
        ticket["closed_by"] = "dashboard"
        ticket["closed_at"] = _now_iso()
        ticket["close_reason"] = "Closed from dashboard"
        save(data)
        # lock channel + rename if bot available
        if bot:
            guild = bot.get_guild(int(guild_id))
            if guild and ticket.get("channel_id"):
                ch = guild.get_channel(int(ticket["channel_id"]))
                if ch:
                    try:
                        user = guild.get_member(int(ticket["user_id"]))
                        if user:
                            bot.loop.create_task(ch.set_permissions(user, send_messages=False))
                    except Exception:
                        pass
            bot.loop.create_task(rename_ticket_channel(bot, guild_id, ticket, closed=True))
        return True, f"Ticket #{ticket.get('number')} closed"

    if action == "reopen" and ticket["status"] == "closed":
        ticket["status"] = "open"
        ticket["closed_by"] = None
        ticket["close_reason"] = None
        save(data)
        if bot:
            bot.loop.create_task(rename_ticket_channel(bot, guild_id, ticket, closed=False))
        return True, f"Ticket #{ticket.get('number')} reopened"

    if action == "delete":
        g["tickets"].pop(ticket_id, None)
        save(data)
        if bot:
            bot.loop.create_task(delete_ticket_channel(bot, guild_id, ticket))
        return True, f"Ticket #{ticket.get('number')} deleted"

    return False, f"Invalid action '{action}' for ticket status '{ticket['status']}'"


def preview_ticket_message(panel_config, category_id=None):
    """Return a dict describing how the ticket welcome embed will look."""
    panel = panel_config or _default_panel("preview")
    cat = panel["categories"].get(category_id) if category_id else next(iter(panel["categories"].values()))
    return {
        "title": f"🎫 Ticket #1",
        "category": f"{cat['emoji']} {cat['name']}",
        "welcome": cat["settings"].get("welcome_message") or "Please describe your issue and staff will assist shortly.",
        "panel_title": panel["panel_message"].get("title", "Open a Ticket"),
        "panel_description": panel["panel_message"].get("description", ""),
        "categories": [
            {"emoji": c["emoji"], "name": c["name"], "desc": c.get("desc", "")}
            for c in panel["categories"].values() if c.get("active", True)
        ],
    }
