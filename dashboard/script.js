/* ═══════════════════════════════════════════════════════════════════
   MANGOLI BOT DASHBOARD — front-end logic
   by Nokiatis Community
   ═══════════════════════════════════════════════════════════════════ */

const API_BASE = '';
let currentPage = 'overview';
let guildsCache = [];
let csrfToken = '';

/* ── helpers ───────────────────────────────────────────────────── */
async function fetchCsrf() {
    try {
        const res = await fetch(`${API_BASE}/api/csrf`);
        const data = await res.json();
        if (data.csrf_token) csrfToken = data.csrf_token;
    } catch (e) { /* ignore */ }
}

async function api(path, opts = {}) {
    try {
        const headers = { 'Content-Type': 'application/json' };
        // attach CSRF token for state-changing requests
        const method = (opts.method || 'GET').toUpperCase();
        if (['POST', 'PUT', 'DELETE', 'PATCH'].includes(method) && csrfToken) {
            headers['X-CSRF-Token'] = csrfToken;
        }
        const res = await fetch(`${API_BASE}${path}`, {
            headers,
            ...opts,
        });
        // session expired / not logged in → redirect to login
        if (res.status === 401) {
            window.location.href = '/login';
            return { ok: false, error: 'unauthorized' };
        }
        if (res.status === 403) {
            // stale CSRF — refresh the token once and retry
            await fetchCsrf();
            return { ok: false, error: 'CSRF error — please retry' };
        }
        return await res.json();
    } catch (e) {
        return { ok: false, error: 'API unreachable' };
    }
}

function toast(msg, type = 'ok') {
    const box = document.getElementById('toasts');
    const el = document.createElement('div');
    el.className = `toast ${type}`;
    el.textContent = msg;
    box.appendChild(el);
    setTimeout(() => el.remove(), 3000);
}

function fmtUptime(s) {
    if (!s || s <= 0) return '—';
    const d = Math.floor(s / 86400);
    const h = Math.floor((s % 86400) / 3600);
    const m = Math.floor((s % 3600) / 60);
    if (d > 0) return `${d}d ${h}h`;
    if (h > 0) return `${h}h ${m}m`;
    return `${m}m`;
}

function fmtTime(iso) { try { return new Date(iso).toLocaleTimeString(); } catch { return ''; } }

/* ── navigation ────────────────────────────────────────────────── */
const TITLES = {
    overview: ['Overview', 'Bot status at a glance'],
    voice: ['Voice', 'Control the bot in voice channels'],
    presence: ['Presence', 'Change status and activity'],
    ai: ['AI Brain', 'Personality & auto-reply settings'],
    broadcast: ['Broadcast', 'Send messages as the bot'],
    commands: ['Commands', 'Registered slash commands'],
    levels: ['Levels', 'XP leaderboard & activity'],
    economy: ['Economy', 'Manage coins & the shop'],
    music: ['Music', 'Control music playback'],
    moderation: ['Moderation', 'Manage members & warnings'],
    giveaways: ['Giveaways', 'Create & manage giveaways'],
    announcements: ['Announcements', 'Schedule messages'],
    stats: ['Stats', 'Server activity & graphs'],
    autorespond: ['Auto-Responder', 'Keyword replies'],
    backup: ['Backup', 'Backup & restore data'],
    webhooks: ['Webhooks', 'Manage Discord webhooks'],
    tickets: ['Tickets', 'Manage & configure the ticket system'],
    logs: ['Logs', 'Live bot activity'],
    servers: ['Servers', 'Guilds the bot is in'],
    system: ['System', 'Info & dangerous actions'],
};

function navigate(page) {
    if (page === currentPage) return;
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    const target = document.getElementById(`page-${page}`);
    if (target) target.classList.add('active');
    document.querySelectorAll('.nav-item').forEach(n => n.classList.toggle('active', n.dataset.page === page));
    currentPage = page;

    const [t, s] = TITLES[page] || TITLES.overview;
    document.getElementById('page-title').textContent = t;
    document.getElementById('page-subtitle').textContent = s;

    if (page === 'voice') { loadVoice(); loadGuilds(); loadSounds(); }
    if (page === 'presence') loadPresence();
    if (page === 'ai') loadAI();
    if (page === 'broadcast') loadBroadcastGuilds();
    if (page === 'logs') loadLogs();
    if (page === 'servers') loadServers();
    if (page === 'commands') loadCommands();
    if (page === 'levels') loadLevels();
    if (page === 'economy') loadEconomy();
    if (page === 'music') loadMusic();
    if (page === 'moderation') loadModeration();
    if (page === 'giveaways') loadGiveaways();
    if (page === 'announcements') loadAnnouncements();
    if (page === 'stats') loadStats();
    if (page === 'autorespond') loadAutorespond();
    if (page === 'backup') loadBackup();
    if (page === 'webhooks') loadWebhooks();
    if (page === 'tickets') loadTickets();
    if (page === 'system') loadSystemInfo();
}

document.querySelectorAll('.nav-item').forEach(n => n.addEventListener('click', () => navigate(n.dataset.page)));
document.querySelectorAll('[data-nav]').forEach(b => b.addEventListener('click', () => navigate(b.dataset.nav)));
document.getElementById('menu-btn').addEventListener('click', () => document.getElementById('sidebar').classList.toggle('open'));

/* ── overview ──────────────────────────────────────────────────── */
async function loadStatus() {
    const s = await api('/api/status');
    const connected = !!s.connected;

    document.getElementById('conn-dot').className = 'conn-dot ' + (connected ? 'on' : 'off');
    document.getElementById('conn-text').textContent = connected ? 'Bot online' : (s.reason || 'Bot offline');

    document.getElementById('hero-name').textContent = s.bot_name || 'Mangoli';
    document.getElementById('hero-badge').textContent = connected ? 'Online' : 'Offline';
    document.getElementById('hero-badge').className = 'badge ' + (connected ? 'on' : 'off');

    const avatar = document.getElementById('hero-avatar');
    if (s.avatar_url) avatar.innerHTML = `<img src="${s.avatar_url}" alt="">`; else avatar.textContent = '◆';

    document.getElementById('hero-latency').textContent = connected ? `Latency: ${s.latency_ms}ms` : 'Latency: —';
    document.getElementById('hero-guilds').textContent = `${s.guild_count || 0} servers`;
    document.getElementById('hero-uptime').textContent = `Uptime: ${fmtUptime(s.uptime_seconds)}`;

    const p = s.presence || {};
    const presEl = document.getElementById('hero-presence');
    if (connected && p.activity_name) {
        presEl.textContent = `${p.activity_type || ''}: "${p.activity_name}" (${p.status || ''})`;
    } else {
        presEl.textContent = connected ? '' : '';
    }

    document.getElementById('stat-servers').textContent = s.guild_count || 0;
    document.getElementById('stat-uptime').textContent = fmtUptime(s.uptime_seconds);
    document.getElementById('stat-latency').textContent = connected ? `${s.latency_ms}ms` : '—';
    document.getElementById('stat-commands').textContent = s.command_count || 0;
    document.getElementById('stat-disabled').textContent = (s.disabled_commands || []).length;

    const vs = await api('/api/voice');
    document.getElementById('stat-voice').textContent = (vs.connections || []).length;

    const cfg = await api('/api/settings');
    document.getElementById('stat-personality').textContent = cfg.settings?.ai_personality || '—';
    document.getElementById('stat-ai').textContent = cfg.settings?.ai_enabled ? 'On' : 'Off';
}

/* ── voice ─────────────────────────────────────────────────────── */
async function loadVoice() {
    const data = await api('/api/voice');
    const list = document.getElementById('voice-list');
    const conns = data.connections || [];
    if (!conns.length) { list.innerHTML = '<div class="empty">No active voice connections.</div>'; return; }

    list.innerHTML = conns.map(c => {
        let pill = 'idle', pillTxt = 'Idle';
        if (c.paused) { pill = 'paused'; pillTxt = 'Paused'; }
        else if (c.playing) { pill = 'playing'; pillTxt = 'Playing'; }
        return `
        <div class="voice-card">
            <div class="v-icon">♪</div>
            <div class="v-info"><div class="v-guild">${c.guild_name}</div><div class="v-channel"># ${c.channel_name}</div></div>
            <span class="status-pill ${pill}">${pillTxt}</span>
            <div class="v-actions">
                ${c.paused
                    ? `<button class="btn small accent" onclick="resumeVoice('${c.guild_id}')">▶ Resume</button>`
                    : `<button class="btn small" onclick="pauseVoice('${c.guild_id}')">⏸ Pause</button>`}
                <button class="btn small" onclick="stopVoice('${c.guild_id}')">⏹ Stop</button>
                <button class="btn small danger" onclick="leaveVoice('${c.guild_id}')">Leave</button>
                <input type="text" class="sound-input" id="sound-${c.guild_id}" placeholder="Sound URL…">
                <button class="btn small" onclick="playSound('${c.guild_id}')">Play</button>
            </div>
        </div>`;
    }).join('');
}

async function loadGuilds() {
    const data = await api('/api/guilds');
    guildsCache = data.guilds || [];
    const sel = document.getElementById('join-guild');
    const prev = sel.value;
    sel.innerHTML = '<option value="">Select server…</option>' +
        guildsCache.map(g => `<option value="${g.id}">${g.name}</option>`).join('');
    if (prev) sel.value = prev;
    updateChannels();
    // also populate the TTS server selector
    const ttsSel = document.getElementById('tts-guild');
    ttsSel.innerHTML = '<option value="">Select server…</option>' +
        guildsCache.map(g => `<option value="${g.id}">${g.name}</option>`).join('');
}

async function speakTTS() {
    const text = document.getElementById('tts-text').value.trim();
    const guild_id = document.getElementById('tts-guild').value;
    const lang = document.getElementById('tts-lang').value;
    if (!text) { toast('Write some text first', 'err'); return; }
    if (!guild_id) { toast('Pick a server first', 'err'); return; }
    const r = await api('/api/voice/tts', { method: 'POST', body: JSON.stringify({ guild_id, text, lang }) });
    r.ok ? toast('Speaking 🗣️') : toast(r.error || 'Failed to speak', 'err');
}

function updateChannels() {
    const gid = document.getElementById('join-guild').value;
    const sel = document.getElementById('join-channel');
    const guild = guildsCache.find(g => g.id === gid);
    if (!guild) { sel.innerHTML = '<option value="">Select channel…</option>'; return; }
    const vcs = guild.voice_channels || [];
    sel.innerHTML = vcs.length ? vcs.map(c => `<option value="${c.id}">${c.name}</option>`).join('') : '<option value="">No voice channels</option>';
}

async function loadSounds() {
    const data = await api('/api/sounds');
    const sounds = data.sounds || [];
    const lib = document.getElementById('sound-lib');
    if (!sounds.length) { lib.innerHTML = '<div class="empty">Sound library is empty.</div>'; return; }
    lib.innerHTML = sounds.map(s => `<span class="sound-chip" data-url="${s.url}"><span class="cat">[${s.category}]</span>${s.name}</span>`).join('');
    lib.querySelectorAll('.sound-chip').forEach(chip =>
        chip.addEventListener('click', async () => {
            const gid = document.getElementById('join-guild').value;
            if (!gid) { toast('Join a voice channel first', 'err'); return; }
            const r = await api('/api/voice/play', { method: 'POST', body: JSON.stringify({ guild_id: gid, url: chip.dataset.url }) });
            r.ok ? toast('Playing sound') : toast(r.error || 'Failed', 'err');
        }));
}

async function joinVoice() {
    const guild_id = document.getElementById('join-guild').value;
    const channel_id = document.getElementById('join-channel').value;
    if (!guild_id || !channel_id) { toast('Pick a server and channel', 'err'); return; }
    const r = await api('/api/voice/join', { method: 'POST', body: JSON.stringify({ guild_id, channel_id }) });
    if (r.ok) { toast(`Joined voice in ${r.guild}`); loadVoice(); }
    else toast(r.error || 'Failed to join', 'err');
}
async function leaveVoice(gid) { await simpleVoice('/api/voice/leave', gid); }
async function pauseVoice(gid) { await simpleVoice('/api/voice/pause', gid); }
async function resumeVoice(gid) { await simpleVoice('/api/voice/resume', gid); }
async function stopVoice(gid) { await simpleVoice('/api/voice/stop', gid); }
async function simpleVoice(path, gid) {
    const r = await api(path, { method: 'POST', body: JSON.stringify({ guild_id: gid }) });
    r.ok ? loadVoice() : toast(r.error || 'Failed', 'err');
}
async function playSound(gid) {
    const url = document.getElementById(`sound-${gid}`).value;
    if (!url) { toast('Enter a sound URL', 'err'); return; }
    const r = await api('/api/voice/play', { method: 'POST', body: JSON.stringify({ guild_id: gid, url }) });
    r.ok ? toast('Playing sound') : toast(r.error || 'Failed', 'err');
}

/* ── presence ──────────────────────────────────────────────────── */
async function loadPresence() {
    const cfg = await api('/api/settings');
    const s = cfg.settings || {};
    document.getElementById('pres-status').value = s.presence_status || 'online';
    document.getElementById('pres-type').value = s.presence_activity_type || 'streaming';
    document.getElementById('pres-text').value = s.presence_text || '';
    document.getElementById('pres-url').value = s.presence_stream_url || '';
}

async function applyPresence() {
    const body = {
        status: document.getElementById('pres-status').value,
        activity_type: document.getElementById('pres-type').value,
        text: document.getElementById('pres-text').value,
        stream_url: document.getElementById('pres-url').value,
    };
    const r = await api('/api/presence', { method: 'POST', body: JSON.stringify(body) });
    const el = document.getElementById('pres-status-msg');
    if (r.ok) { el.textContent = '✓ Applied'; toast('Presence updated'); }
    else { el.textContent = '✗ Failed'; toast(r.error || 'Failed', 'err'); }
}

/* ── AI ────────────────────────────────────────────────────────── */
async function loadAI() {
    const data = await api('/api/settings');
    const s = data.settings || {};
    const personalities = data.personalities || ['default'];
    const sel = document.getElementById('ai-personality');
    sel.innerHTML = personalities.map(p => `<option value="${p}">${p}</option>`).join('');
    if (s.ai_personality) sel.value = s.ai_personality;
    document.getElementById('ai-enabled').checked = s.ai_enabled !== false;
    document.getElementById('ai-channel').value = s.ai_channel_id || '';
    document.getElementById('ai-persona').value = s.ai_custom_persona || '';
}

async function saveAI() {
    const body = {
        ai_enabled: document.getElementById('ai-enabled').checked,
        ai_personality: document.getElementById('ai-personality').value,
        ai_channel_id: document.getElementById('ai-channel').value.trim(),
        ai_custom_persona: document.getElementById('ai-persona').value,
    };
    const r = await api('/api/settings', { method: 'POST', body: JSON.stringify(body) });
    const el = document.getElementById('ai-status');
    if (r.ok) { el.textContent = '✓ Saved'; toast('AI settings saved'); }
    else { el.textContent = '✗ Failed'; toast('Failed to save', 'err'); }
}

/* ── broadcast ─────────────────────────────────────────────────── */
async function loadBroadcastGuilds() {
    const data = await api('/api/guilds');
    guildsCache = data.guilds || [];
    const sel = document.getElementById('bc-guild');
    sel.innerHTML = '<option value="">Select server…</option>' +
        guildsCache.map(g => `<option value="${g.id}">${g.name}</option>`).join('');
    updateBroadcastChannels();
}
function updateBroadcastChannels() {
    const gid = document.getElementById('bc-guild').value;
    const sel = document.getElementById('bc-channel');
    const guild = guildsCache.find(g => g.id === gid);
    if (!guild) { sel.innerHTML = '<option value="">Select channel…</option>'; return; }
    const tcs = guild.text_channels || [];
    sel.innerHTML = tcs.length ? tcs.map(c => `<option value="${c.id}">${c.name}</option>`).join('') : '<option value="">No text channels</option>';
}
async function sendBroadcast() {
    const guild_id = document.getElementById('bc-guild').value;
    const channel_id = document.getElementById('bc-channel').value;
    const text = document.getElementById('bc-text').value;
    if (!guild_id || !channel_id || !text) { toast('Fill all fields', 'err'); return; }
    const r = await api('/api/broadcast', { method: 'POST', body: JSON.stringify({ guild_id, channel_id, text }) });
    const el = document.getElementById('bc-status');
    if (r.ok) { el.textContent = '✓ Sent'; toast('Message sent'); document.getElementById('bc-text').value = ''; }
    else { el.textContent = '✗ Failed'; toast(r.error || 'Failed', 'err'); }
}

/* ── commands ──────────────────────────────────────────────────── */
async function loadCommands() {
    const data = await api('/api/commands');
    const cmds = data.commands || [];
    const list = document.getElementById('cmd-list');
    if (!cmds.length) { list.innerHTML = '<div class="empty">No commands loaded.</div>'; return; }
    list.innerHTML = cmds.map(c => `
        <div class="cmd-row">
            <span class="cmd-name">/${c.name}</span>
            <span class="cmd-desc">${c.description || ''}</span>
            <span class="cmd-uses">${c.uses} uses</span>
            <label class="switch">
                <input type="checkbox" ${c.enabled ? 'checked' : ''} onchange="toggleCommand('${c.name}', this.checked)">
                <span class="slider"></span>
            </label>
        </div>`).join('');
}
async function toggleCommand(name, enabled) {
    const r = await api('/api/commands/toggle', { method: 'POST', body: JSON.stringify({ name, enabled }) });
    if (r.ok) toast(enabled ? `Enabled /${name}` : `Disabled /${name}`);
    else { toast(r.error || 'Failed', 'err'); loadCommands(); }
}

/* ── logs ──────────────────────────────────────────────────────── */
async function loadLogs() {
    const level = document.getElementById('log-level').value;
    const data = await api(`/api/logs?level=${level}&limit=200`);
    const logs = Array.isArray(data) ? data : [];
    const list = document.getElementById('log-list');
    if (!logs.length) { list.innerHTML = '<div class="empty">No logs yet.</div>'; return; }
    const rev = logs.slice().reverse();
    list.innerHTML = rev.map(l => `
        <div class="log-row">
            <span class="log-time">${fmtTime(l.time)}</span>
            <span class="log-level ${(l.level || 'info').toLowerCase()}">${l.level}</span>
            <span class="log-msg"></span>
        </div>`).join('');
    list.querySelectorAll('.log-row').forEach((row, i) => {
        row.querySelector('.log-msg').textContent = rev[i].message;
    });
}

/* ── servers ───────────────────────────────────────────────────── */
async function loadServers() {
    const data = await api('/api/guilds');
    const guilds = data.guilds || [];
    const grid = document.getElementById('servers-grid');
    if (!guilds.length) { grid.innerHTML = '<div class="empty">The bot is not in any servers yet.</div>'; return; }
    grid.innerHTML = guilds.map(g => `
        <div class="server-card">
            <div class="server-icon">${g.icon_url ? `<img src="${g.icon_url}" alt="">` : '◈'}</div>
            <div class="server-name">${g.name}</div>
            <div class="server-meta">${g.member_count} members • ${g.text_channels?.length || 0} text • ${g.voice_channels?.length || 0} voice</div>
        </div>`).join('');
}

/* ── levels ────────────────────────────────────────────────────── */
let levelsGuildId = null;

async function loadLevels() {
    const q = levelsGuildId ? `?guild_id=${levelsGuildId}` : '';
    const data = await api(`/api/levels${q}`);
    const members = data.members || [];

    // guild selector
    const sel = document.getElementById('levels-guild');
    if (sel.options.length === 0) {
        const guilds = await api('/api/guilds');
        const list = guilds.guilds || [];
        sel.innerHTML = list.map(g =>
            `<option value="${g.id}">${g.name}</option>`).join('');
        if (data.guild) sel.value = data.guild.id;
    }

    // summary cards
    const tracked = members.filter(m => m.xp > 0).length;
    const totalXp = members.reduce((a, m) => a + m.xp, 0);
    const totalInvites = members.reduce((a, m) => a + m.invites, 0);
    const totalCoins = members.reduce((a, m) => a + (m.coins || 0), 0);
    document.getElementById('lv-tracked').textContent = tracked;
    document.getElementById('lv-total-xp').textContent = totalXp.toLocaleString();
    document.getElementById('lv-total-invites').textContent = totalInvites;
    document.getElementById('lv-top').textContent = members[0] ? members[0].name : '—';
    document.getElementById('lv-total-coins').textContent = totalCoins.toLocaleString();

    // leaderboard
    const lb = document.getElementById('leaderboard');
    if (!members.length) {
        lb.innerHTML = '<div class="empty">No members found.</div>';
        return;
    }
    lb.innerHTML = members.map(m => {
        const rankClass = m.rank === 1 ? 'top1' : m.rank === 2 ? 'top2' : m.rank === 3 ? 'top3' : '';
        const rankLabel = m.rank <= 3 ? ['🥇', '🥈', '🥉'][m.rank - 1] : `#${m.rank}`;
        const avatar = m.avatar_url ? `<img src="${m.avatar_url}" alt="">` : (m.name || '?').charAt(0).toUpperCase();
        const pct = Math.max(0, Math.min(100, m.progress || 0));
        return `
        <div class="lb-row">
            <div class="lb-rank ${rankClass}">${rankLabel}</div>
            <div class="lb-avatar">${avatar}</div>
            <div class="lb-info">
                <div class="lb-name">${m.name}<span class="lb-level">Lv ${m.level}</span></div>
                <div class="lb-sub">💬 ${m.messages} · 🎙️ ${m.voice_minutes}m · 📨 ${m.invites}${m.streak ? ` · 🔥 ${m.streak}d` : ''}</div>
                <div class="lb-bar"><div class="lb-bar-fill" style="width:${pct}%"></div></div>
            </div>
            <div class="lb-side">
                <div class="lb-xp">${m.xp.toLocaleString()} XP</div>
                <div class="lb-sub">💰 ${(m.coins || 0).toLocaleString()} · ${pct}%</div>
            </div>
        </div>`;
    }).join('');
}

/* ── economy ───────────────────────────────────────────────────── */
let economyGuildId = null;

async function loadEconomy() {
    const sel = document.getElementById('economy-guild');
    const gs = await api('/api/guilds');
    const guilds = gs.guilds || [];
    sel.innerHTML = guilds.map(g => `<option value="${g.id}">${g.name}</option>`).join('');
    if (!economyGuildId && guilds[0]) economyGuildId = guilds[0].id;
    sel.value = economyGuildId;

    const q = economyGuildId ? `?guild_id=${economyGuildId}` : '';
    const data = await api(`/api/economy${q}`);
    const members = data.members || [];
    const shop = data.shop || {};

    // members list
    const list = document.getElementById('eco-list');
    if (!members.length) {
        list.innerHTML = '<div class="empty">No members found (bot not connected to this guild).</div>';
    } else {
        list.innerHTML = members.map(m => `
            <div class="eco-row">
                <div class="eco-avatar">${m.avatar_url ? `<img src="${m.avatar_url}">` : (m.name || '?').charAt(0).toUpperCase()}</div>
                <div class="eco-name">${m.name}</div>
                <div class="eco-balance">💰 ${(m.balance || 0).toLocaleString()}</div>
                <div class="eco-actions">
                    <input type="number" id="eco-amt-${m.user_id}" value="100" min="1">
                    <button class="btn small accent" onclick="ecoAction('${m.user_id}','add')">➕ Add</button>
                    <button class="btn small" onclick="ecoAction('${m.user_id}','remove')">➖ Remove</button>
                    <button class="btn small" onclick="ecoSet('${m.user_id}')">Set</button>
                </div>
            </div>`).join('');
    }

    // shop
    const shopBox = document.getElementById('eco-shop');
    if (!Object.keys(shop).length) {
        shopBox.innerHTML = '<div class="empty">No shop items.</div>';
    } else {
        shopBox.innerHTML = Object.entries(shop).map(([id, item]) => `
            <div class="eco-shop-item">
                <div class="si-name">${item.emoji || ''} ${item.name}</div>
                <div class="si-desc">${item.description || ''}</div>
                <div class="si-cost">💰 ${(item.cost || 0).toLocaleString()}</div>
            </div>`).join('');
    }
}

async function ecoAction(userId, action) {
    const amt = document.getElementById(`eco-amt-${userId}`).value;
    const r = await api('/api/economy/action', {
        method: 'POST',
        body: JSON.stringify({ guild_id: economyGuildId, action, user_id: userId, amount: parseInt(amt) || 0 }),
    });
    toast(r.ok ? `Balance updated: 💰 ${r.balance.toLocaleString()}` : (r.error || 'Failed'), r.ok ? 'ok' : 'err');
    if (r.ok) loadEconomy();
}

async function ecoSet(userId) {
    const amt = document.getElementById(`eco-amt-${userId}`).value;
    const r = await api('/api/economy/action', {
        method: 'POST',
        body: JSON.stringify({ guild_id: economyGuildId, action: 'set', user_id: userId, amount: parseInt(amt) || 0 }),
    });
    toast(r.ok ? `Balance set: 💰 ${r.balance.toLocaleString()}` : (r.error || 'Failed'), r.ok ? 'ok' : 'err');
    if (r.ok) loadEconomy();
}

/* ── music ─────────────────────────────────────────────────────── */
let musicGuildId = null;

function fmtDur(ms) {
    if (!ms) return '0:00';
    const s = Math.floor(ms / 1000);
    return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`;
}

async function loadMusic() {
    // populate guild selector
    const sel = document.getElementById('music-guild');
    const gs = await api('/api/guilds');
    const guilds = gs.guilds || [];
    sel.innerHTML = guilds.map(g => `<option value="${g.id}">${g.name}</option>`).join('');
    if (!musicGuildId && guilds[0]) musicGuildId = guilds[0].id;
    sel.value = musicGuildId;

    const data = await api('/api/music');
    const players = data.players || [];
    const list = document.getElementById('music-list');

    if (!data.available) {
        list.innerHTML = '<div class="empty">🎵 Music system not connected (Lavalink offline).</div>';
        return;
    }
    if (!players.length) {
        list.innerHTML = '<div class="empty">No music playing. Use /play in Discord to start a track.</div>';
        return;
    }

    list.innerHTML = players.map(p => {
        const cur = p.current;
        const pct = cur && cur.length ? Math.min(100, (cur.position / cur.length) * 100) : 0;
        return `
        <div class="music-card">
            <div class="music-art">${cur && cur.artwork ? `<img src="${cur.artwork}">` : '🎵'}</div>
            <div class="music-info">
                <div class="music-title">${cur ? cur.title : '—'} ${p.paused ? '⏸️' : p.playing ? '▶️' : '⏹️'}</div>
                <div class="music-sub">${cur ? cur.author : ''} · vol ${p.volume}% · loop ${p.loop}</div>
                ${cur ? `<div class="music-bar"><div class="music-bar-fill" style="width:${pct}%"></div></div>
                <div class="music-sub">${fmtDur(cur.position)} / ${fmtDur(cur.length)} · ${p.queue_count} in queue</div>` : ''}
            </div>
            <div class="music-actions">
                ${p.paused ? `<button class="btn small accent" onclick="musicCtl('${p.guild_id}','resume')">▶️</button>` : `<button class="btn small" onclick="musicCtl('${p.guild_id}','pause')">⏸️</button>`}
                <button class="btn small" onclick="musicCtl('${p.guild_id}','skip')">⏭️</button>
                <button class="btn small danger" onclick="musicCtl('${p.guild_id}','stop')">⏹️</button>
                <button class="btn small" onclick="musicCtl('${p.guild_id}','shuffle')">🔀</button>
                <button class="btn small" onclick="musicCtl('${p.guild_id}','loop')">🔁</button>
                <input type="number" class="music-vol" id="vol-${p.guild_id}" value="${p.volume}" min="0" max="200">
                <button class="btn small" onclick="musicVol('${p.guild_id}')">Set</button>
            </div>
        </div>`;
    }).join('');
}

async function musicCtl(guildId, action) {
    const r = await api('/api/music/control', { method: 'POST', body: JSON.stringify({ guild_id: guildId, action }) });
    toast(r.ok ? `Music: ${action}` : (r.error || 'Failed'), r.ok ? 'ok' : 'err');
    loadMusic();
}

async function musicVol(guildId) {
    const v = document.getElementById(`vol-${guildId}`).value;
    const r = await api('/api/music/control', { method: 'POST', body: JSON.stringify({ guild_id: guildId, action: 'volume', value: parseInt(v) }) });
    toast(r.ok ? `Volume set` : (r.error || 'Failed'), r.ok ? 'ok' : 'err');
    loadMusic();
}

async function musicPlay() {
    const guild_id = document.getElementById('music-guild').value || musicGuildId;
    const query = document.getElementById('music-query').value.trim();
    if (!guild_id) { toast('Pick a server', 'err'); return; }
    if (!query) { toast('Enter a song name or URL', 'err'); return; }
    const r = await api('/api/music/control', { method: 'POST', body: JSON.stringify({ guild_id, action: 'play', value: query }) });
    toast(r.ok ? '▶️ Playing' : (r.error || 'Failed'), r.ok ? 'ok' : 'err');
    loadMusic();
}

/* ── moderation ───────────────────────────────────────────────── */
let modGuildId = null;

async function loadModeration() {
    const sel = document.getElementById('mod-guild');
    const gs = await api('/api/guilds');
    const guilds = gs.guilds || [];
    sel.innerHTML = guilds.map(g => `<option value="${g.id}">${g.name}</option>`).join('');
    if (!modGuildId && guilds[0]) modGuildId = guilds[0].id;
    sel.value = modGuildId;

    const q = modGuildId ? `?guild_id=${modGuildId}` : '';
    const data = await api(`/api/members${q}`);
    const members = data.members || [];
    const search = (document.getElementById('mod-search').value || '').toLowerCase();

    const list = document.getElementById('mod-list');
    if (!members.length) {
        list.innerHTML = '<div class="empty">No members found.</div>';
        return;
    }

    const filtered = members.filter(m =>
        !search || m.name.toLowerCase().includes(search) || m.username.toLowerCase().includes(search)
    );

    list.innerHTML = filtered.map(m => `
        <div class="mod-row">
            <div class="mod-avatar">${m.avatar_url ? `<img src="${m.avatar_url}">` : (m.name || '?').charAt(0).toUpperCase()}</div>
            <div class="mod-info">
                <div class="mod-name">${m.name} ${m.is_bot ? '🤖' : ''}</div>
                <div class="mod-sub">${m.top_role || ''} · ${m.warnings ? `<span class="mod-warns">⚠️ ${m.warnings} warn</span>` : ''}</div>
            </div>
            <div class="mod-actions">
                <button class="btn small" onclick="modAct('${m.user_id}','warn')">⚠️ Warn</button>
                <button class="btn small" onclick="modAct('${m.user_id}','clear_warns')">Clear</button>
                <button class="btn small" onclick="modAct('${m.user_id}','kick')">👢 Kick</button>
                <button class="btn small danger" onclick="modAct('${m.user_id}','ban')">🔨 Ban</button>
            </div>
        </div>`).join('');

    // populate the role-management selects
    const rolesData = await api(`/api/roles?guild_id=${modGuildId}`);
    const roles = rolesData.roles || [];
    document.getElementById('role-select').innerHTML = roles.map(r => `<option value="${r.id}">@ ${r.name}</option>`).join('');
    document.getElementById('role-user').innerHTML = members.filter(m => !m.is_bot).map(m => `<option value="${m.user_id}">${m.name}</option>`).join('');
}

async function roleAction(action) {
    const user_id = document.getElementById('role-user').value;
    const role_id = document.getElementById('role-select').value;
    if (!user_id || !role_id) { toast('Pick a member and role', 'err'); return; }
    const r = await api('/api/role', {
        method: 'POST',
        body: JSON.stringify({ guild_id: modGuildId, user_id, role_id, action }),
    });
    toast(r.ok ? r.message : (r.error || 'Failed'), r.ok ? 'ok' : 'err');
}

async function modAct(userId, action) {
    if (action === 'ban' && !confirm('Ban this member permanently?')) return;
    if (action === 'kick' && !confirm('Kick this member?')) return;
    const reason = prompt('Reason (optional):') || '';
    const r = await api('/api/moderate', {
        method: 'POST',
        body: JSON.stringify({ guild_id: modGuildId, action, user_id: userId, reason }),
    });
    toast(r.ok ? r.message : (r.error || 'Failed'), r.ok ? 'ok' : 'err');
    if (r.ok) loadModeration();
}

/* ── giveaways ────────────────────────────────────────────────── */
async function loadGiveaways() {
    const data = await api('/api/giveaways');
    const gws = data.giveaways || [];
    const list = document.getElementById('gw-list');
    if (!gws.length) {
        list.innerHTML = '<div class="empty">No giveaways yet.</div>';
        return;
    }
    list.innerHTML = gws.map(g => {
        const remain = Math.max(0, Math.round((g.ends_at - Date.now() / 1000) / 60));
        return `
        <div class="gw-row">
            <div class="gw-info">
                <div class="gw-prize">🎁 ${g.prize}</div>
                <div class="gw-sub">${g.entry_count} entries · ${g.winners} winner(s) · ${g.ended ? 'Ended' : remain + 'm left'}</div>
            </div>
            <div class="gw-actions">
                <button class="btn small accent" onclick="gwEnd('${g.giveaway_id}')">🏆 End & Pick</button>
                <button class="btn small danger" onclick="gwDelete('${g.giveaway_id}')">🗑️ Delete</button>
            </div>
        </div>`;
    }).join('');
}

async function gwCreate() {
    const prize = document.getElementById('gw-prize').value.trim();
    const winners = document.getElementById('gw-winners').value;
    const duration = document.getElementById('gw-duration').value;
    if (!prize) { toast('Enter a prize', 'err'); return; }
    const r = await api('/api/giveaways/create', {
        method: 'POST',
        body: JSON.stringify({ prize, winners: parseInt(winners), duration_minutes: parseInt(duration) }),
    });
    toast(r.ok ? 'Giveaway created 🎉' : (r.error || 'Failed'), r.ok ? 'ok' : 'err');
    if (r.ok) { document.getElementById('gw-prize').value = ''; loadGiveaways(); }
}

async function gwEnd(gwId) {
    const r = await api(`/api/giveaways/${gwId}/end`, { method: 'POST', body: '{}' });
    if (r.ok) {
        toast(`🏆 Winners: ${r.winners.join(', ')} (${r.prize})`);
    } else {
        toast(r.error || 'Failed', 'err');
    }
    loadGiveaways();
}

async function gwDelete(gwId) {
    const r = await api(`/api/giveaways/${gwId}/delete`, { method: 'POST', body: '{}' });
    toast(r.ok ? 'Deleted' : (r.error || 'Failed'), r.ok ? 'ok' : 'err');
    loadGiveaways();
}

/* ── announcements ────────────────────────────────────────────── */
let annGuildId = null;
let annGuildsCache = [];

async function loadAnnouncements() {
    // populate servers + channels
    const gs = await api('/api/guilds');
    annGuildsCache = gs.guilds || [];
    const sel = document.getElementById('ann-guild');
    sel.innerHTML = annGuildsCache.map(g => `<option value="${g.id}">${g.name}</option>`).join('');
    if (!annGuildId && annGuildsCache[0]) annGuildId = annGuildsCache[0].id;
    updateAnnChannels();

    // list scheduled
    const data = await api('/api/announcements');
    const anns = data.announcements || [];
    const list = document.getElementById('ann-list');
    if (!anns.length) {
        list.innerHTML = '<div class="empty">No scheduled announcements.</div>';
        return;
    }
    list.innerHTML = anns.map(a => {
        const remain = Math.max(0, Math.round(a.send_at - Date.now() / 1000));
        const mins = Math.round(remain / 60);
        return `
        <div class="ann-row">
            <div class="ann-info">
                <div class="ann-msg">📢 ${a.message.length > 60 ? a.message.slice(0, 60) + '…' : a.message}</div>
                <div class="ann-sub">→ #${a.channel_name || a.channel_id} · ${a.sent ? '✅ Sent' : 'in ~' + mins + 'm'}</div>
            </div>
            <div class="ann-actions">
                <button class="btn small danger" onclick="annDelete('${a.announcement_id}')">🗑️ Cancel</button>
            </div>
        </div>`;
    }).join('');
}

function updateAnnChannels() {
    const gid = document.getElementById('ann-guild').value || annGuildId;
    const guild = annGuildsCache.find(g => g.id === gid);
    const sel = document.getElementById('ann-channel');
    if (!guild) { sel.innerHTML = '<option value="">Select channel…</option>'; return; }
    const tcs = guild.text_channels || [];
    sel.innerHTML = tcs.map(c => `<option value="${c.id}"># ${c.name}</option>`).join('');
}

async function annCreate() {
    const guild_id = document.getElementById('ann-guild').value || annGuildId;
    const channel_id = document.getElementById('ann-channel').value;
    const message = document.getElementById('ann-message').value.trim();
    const delay = parseInt(document.getElementById('ann-delay').value) || 30;
    if (!guild_id || !channel_id) { toast('Pick server + channel', 'err'); return; }
    if (!message) { toast('Write a message', 'err'); return; }
    const channel_name = document.getElementById('ann-channel').selectedOptions[0]?.text.replace('# ', '') || '';
    const r = await api('/api/announcements/create', {
        method: 'POST',
        body: JSON.stringify({ guild_id, channel_id, channel_name, message, send_at: Date.now() / 1000 + delay * 60 }),
    });
    toast(r.ok ? 'Scheduled 📢' : (r.error || 'Failed'), r.ok ? 'ok' : 'err');
    if (r.ok) { document.getElementById('ann-message').value = ''; loadAnnouncements(); }
}

async function annDelete(id) {
    const r = await api(`/api/announcements/${id}/delete`, { method: 'POST', body: '{}' });
    toast(r.ok ? 'Cancelled' : 'Failed', r.ok ? 'ok' : 'err');
    loadAnnouncements();
}

/* ── stats ────────────────────────────────────────────────────── */
let statsGuildId = null;

async function loadStats() {
    const sel = document.getElementById('stats-guild');
    const gs = await api('/api/guilds');
    const guilds = gs.guilds || [];
    sel.innerHTML = guilds.map(g => `<option value="${g.id}">${g.name}</option>`).join('');
    if (!statsGuildId && guilds[0]) statsGuildId = guilds[0].id;
    sel.value = statsGuildId;

    const q = statsGuildId ? `?guild_id=${statsGuildId}` : '';
    const data = await api(`/api/stats/activity${q}`);
    const totals = data.totals || {};
    const top = data.top || [];

    // totals cards
    document.getElementById('stats-totals').innerHTML = `
        <div class="card"><div class="card-label">Total XP</div><div class="card-value">${(totals.xp || 0).toLocaleString()}</div></div>
        <div class="card"><div class="card-label">Messages</div><div class="card-value">${(totals.messages || 0).toLocaleString()}</div></div>
        <div class="card"><div class="card-label">Voice (min)</div><div class="card-value">${(totals.voice_minutes || 0).toLocaleString()}</div></div>
        <div class="card"><div class="card-label">Invites</div><div class="card-value">${(totals.invites || 0).toLocaleString()}</div></div>
        <div class="card"><div class="card-label">Tracked Members</div><div class="card-value">${totals.tracked_members || 0}</div></div>`;

    // chart (XP bars)
    const chart = document.getElementById('stats-chart');
    if (!top.length) {
        chart.innerHTML = '<div class="empty">No activity yet.</div>';
        return;
    }
    const maxXp = Math.max(...top.map(t => t.xp), 1);
    chart.innerHTML = top.map(t => `
        <div class="stat-bar-row">
            <div class="stat-bar-label">${t.name} (Lv ${t.level})</div>
            <div class="stat-bar-track"><div class="stat-bar-fill" style="width:${(t.xp / maxXp * 100).toFixed(1)}%"></div></div>
            <div class="stat-bar-val">${t.xp.toLocaleString()} XP</div>
        </div>`).join('');
}

/* ── autorespond ──────────────────────────────────────────────── */
let arGuildId = null;

async function loadAutorespond() {
    const sel = document.getElementById('ar-guild');
    const gs = await api('/api/guilds');
    const guilds = gs.guilds || [];
    sel.innerHTML = guilds.map(g => `<option value="${g.id}">${g.name}</option>`).join('');
    if (!arGuildId && guilds[0]) arGuildId = guilds[0].id;
    sel.value = arGuildId;

    const q = arGuildId ? `?guild_id=${arGuildId}` : '';
    const data = await api(`/api/autoresponders${q}`);
    const ars = data.autoresponders || {};
    const list = document.getElementById('ar-list');
    const entries = Object.entries(ars);
    if (!entries.length) {
        list.innerHTML = '<div class="empty">No auto-responders yet.</div>';
        return;
    }
    list.innerHTML = entries.map(([trigger, response]) => `
        <div class="ann-row">
            <div class="ann-info">
                <div class="ann-msg">🔑 "${trigger}" → ${response.length > 50 ? response.slice(0, 50) + '…' : response}</div>
            </div>
            <button class="btn small danger" onclick="arRemove('${trigger}')">🗑️</button>
        </div>`).join('');
}

async function arAdd() {
    const guild_id = document.getElementById('ar-guild').value || arGuildId;
    const trigger = document.getElementById('ar-trigger').value.trim();
    const response = document.getElementById('ar-response').value.trim();
    if (!guild_id || !trigger || !response) { toast('Fill all fields', 'err'); return; }
    const r = await api('/api/autoresponders/add', {
        method: 'POST',
        body: JSON.stringify({ guild_id, trigger, response }),
    });
    toast(r.ok ? 'Added' : (r.error || 'Failed'), r.ok ? 'ok' : 'err');
    if (r.ok) { document.getElementById('ar-trigger').value = ''; document.getElementById('ar-response').value = ''; loadAutorespond(); }
}

async function arRemove(trigger) {
    const r = await api('/api/autoresponders/remove', {
        method: 'POST',
        body: JSON.stringify({ guild_id: arGuildId, trigger }),
    });
    toast(r.ok ? 'Removed' : (r.error || 'Failed'), r.ok ? 'ok' : 'err');
    loadAutorespond();
}

/* ── backup ───────────────────────────────────────────────────── */
async function loadBackup() {
    const data = await api('/api/backup/status');
    const files = data.files || [];
    const box = document.getElementById('backup-files');
    if (!files.length) {
        box.innerHTML = '<div class="empty">No data files yet.</div>';
        return;
    }
    box.innerHTML = files.map(f => `
        <div class="ann-row">
            <div class="ann-info">
                <div class="ann-msg">📄 ${f.name}</div>
                <div class="ann-sub">${(f.size / 1024).toFixed(1)} KB</div>
            </div>
        </div>`).join('');
}

async function backupRestore() {
    const raw = document.getElementById('backup-json').value.trim();
    if (!raw) { toast('Paste backup JSON first', 'err'); return; }
    let bundle;
    try { bundle = JSON.parse(raw); }
    catch { toast('Invalid JSON', 'err'); return; }
    const r = await api('/api/backup/restore', { method: 'POST', body: JSON.stringify({ bundle }) });
    toast(r.ok ? `Restored: ${r.restored.join(', ')}` : (r.error || 'Failed'), r.ok ? 'ok' : 'err');
    if (r.ok) loadBackup();
}

/* ── webhooks ─────────────────────────────────────────────────── */
let whGuildId = null;

async function loadWebhooks() {
    const sel = document.getElementById('wh-guild');
    const gs = await api('/api/guilds');
    const guilds = gs.guilds || [];
    sel.innerHTML = guilds.map(g => `<option value="${g.id}">${g.name}</option>`).join('');
    if (!whGuildId && guilds[0]) whGuildId = guilds[0].id;
    sel.value = whGuildId;

    const q = whGuildId ? `?guild_id=${whGuildId}` : '';
    const data = await api(`/api/webhooks${q}`);
    const webhooks = data.webhooks || [];
    const channels = data.channels || [];

    document.getElementById('wh-channel').innerHTML = channels.map(c => `<option value="${c.id}"># ${c.name}</option>`).join('');

    const list = document.getElementById('wh-list');
    if (!webhooks.length) {
        list.innerHTML = '<div class="empty">No webhooks found.</div>';
        return;
    }
    if (webhooks[0] && webhooks[0].error) {
        list.innerHTML = `<div class="empty">⚠️ ${webhooks[0].error}</div>`;
        return;
    }
    list.innerHTML = webhooks.map(w => `
        <div class="ann-row">
            <div class="ann-info">
                <div class="ann-msg">🔗 ${w.name}</div>
                <div class="ann-sub">→ #${w.channel_name || w.channel_id}</div>
            </div>
            <button class="btn small danger" onclick="whDelete('${w.id}')">🗑️ Delete</button>
        </div>`).join('');
}

async function whCreate() {
    const channel_id = document.getElementById('wh-channel').value;
    const name = document.getElementById('wh-name').value.trim() || 'Mangoli Webhook';
    if (!channel_id) { toast('Pick a channel', 'err'); return; }
    const r = await api('/api/webhooks/create', {
        method: 'POST',
        body: JSON.stringify({ guild_id: whGuildId, channel_id, name }),
    });
    toast(r.ok ? 'Webhook created' : (r.error || 'Failed'), r.ok ? 'ok' : 'err');
    if (r.ok) loadWebhooks();
}

async function whDelete(id) {
    if (!confirm('Delete this webhook?')) return;
    const r = await api('/api/webhooks/delete', {
        method: 'POST',
        body: JSON.stringify({ guild_id: whGuildId, webhook_id: id }),
    });
    toast(r.ok ? 'Deleted' : (r.error || 'Failed'), r.ok ? 'ok' : 'err');
    loadWebhooks();
}

/* ── tickets ───────────────────────────────────────────────────── */
let ticketsGuildId = null;
let ticketConfig = null;
let ticketGuildData = null;   // {channels, categories, roles, text_channels}
let catSeq = 0;               // for generating new category ids

async function loadTickets() {
    // populate guild selector
    const sel = document.getElementById('tickets-guild');
    const gs = await api('/api/guilds');
    const guilds = gs.guilds || [];
    allGuilds = guilds;
    sel.innerHTML = guilds.map(g => `<option value="${g.id}">${g.name}</option>`).join('');
    if (!ticketsGuildId && guilds[0]) ticketsGuildId = guilds[0].id;
    sel.value = ticketsGuildId;

    // load full guild data (channels/categories/roles) for the config UI
    const gcfg = await api(`/api/tickets/config?guild_id=${ticketsGuildId}`);
    ticketGuildData = gcfg;

    const q = ticketsGuildId ? `?guild_id=${ticketsGuildId}` : '';
    const data = await api(`/api/tickets${q}`);
    const tickets = data.tickets || [];
    const cfg = data.config || {};

    // stats
    const st = cfg.stats || { total: 0, open: 0, closed: 0 };
    document.getElementById('ticket-stats').innerHTML = `
        <div class="card"><div class="card-label">Open</div><div class="card-value">${st.open}</div></div>
        <div class="card"><div class="card-label">Closed</div><div class="card-value">${st.closed}</div></div>
        <div class="card"><div class="card-label">Total</div><div class="card-value">${st.total}</div></div>
        <div class="card"><div class="card-label">Configured</div><div class="card-value small">${cfg.configured ? '✅ Yes' : '❌ No'}</div></div>`;

    // list
    const list = document.getElementById('ticket-list');
    if (!tickets.length) {
        list.innerHTML = '<div class="empty">No tickets yet.</div>';
    } else {
        list.innerHTML = tickets.map(t => `
            <div class="ticket-item">
                <div class="t-ico">${t.category_emoji || '🎫'}</div>
                <div class="t-info">
                    <div class="t-title">#${t.number} — ${t.user_name || 'User'} ${t.status === 'open' ? '🟢' : '🔴'}</div>
                    <div class="t-sub">${t.category_name || ''} · ${t.channel_name || 'deleted'}${t.claimed_name ? ' · claimed by ' + t.claimed_name : ''}</div>
                </div>
                <div class="t-actions">
                    ${t.status === 'open' ? `<button class="btn small danger" onclick="ticketAction('${t.ticket_id}','close')">🔒 Close</button>` : `<button class="btn small" onclick="ticketAction('${t.ticket_id}','reopen')">🔓 Reopen</button>`}
                    <button class="btn small" onclick="ticketAction('${t.ticket_id}','delete')">🗑️ Delete</button>
                </div>
            </div>`).join('');
    }

    // load config into setup form — ALWAYS render, with defaults if unconfigured
    ticketConfig = cfg.panel || null;
    if (!ticketConfig) {
        // no panel yet — build a default so the whole UI is usable
        ticketConfig = {
            name: 'Mangoli Tickets',
            display_type: 'select',
            placeholder: '🎫 Choose a category…',
            panel_message: { title: 'Open a Ticket', description: 'Select a category below to create a ticket' },
            staff_roles: [],
            logs: { create: null, close: null, rating: null },
            categories: {
                support: { emoji: '💬', name: 'Support', desc: 'General help', active: true, support_roles: [], ticket_category_id: null, naming_format: 'ticket-{username}', settings: { max_tickets_per_user: 1, ping_user: true, ping_role: false, user_can_close: true, dm_user_on_open: true, dm_user_on_close: true, welcome_message: '' } },
                order: { emoji: '🛒', name: 'Order / Purchase', desc: 'Billing & orders', active: true, support_roles: [], ticket_category_id: null, naming_format: 'ticket-{username}', settings: { max_tickets_per_user: 1, ping_user: true, ping_role: false, user_can_close: true, dm_user_on_open: true, dm_user_on_close: true, welcome_message: '' } },
            },
        };
    }
    document.getElementById('tk-title').value = ticketConfig.panel_message?.title || 'Open a Ticket';
    document.getElementById('tk-desc').value = ticketConfig.panel_message?.description || '';
    document.getElementById('tk-name').value = ticketConfig.name || 'Mangoli Tickets';
    document.getElementById('tk-display').value = ticketConfig.display_type || 'select';
    document.getElementById('tk-placeholder').value = ticketConfig.placeholder || '';
    renderTicketCategories(ticketConfig.categories || {});
    renderStaffAndLogs();
    renderSendChannel();
    renderPreview();
}

/* Build a channel/category/role <option> list helper */
function channelOptions(selectedId, placeholder) {
    const channels = ticketGuildData?.channels || [];
    let html = `<option value="">${placeholder || '— none —'}</option>`;
    channels.forEach(c => html += `<option value="${c.id}" ${String(c.id) === String(selectedId) ? 'selected' : ''}># ${c.name}</option>`);
    return html;
}
function categoryOptions(selectedId) {
    const cats = ticketGuildData?.categories_channels || [];
    let html = `<option value="">— no category —</option>`;
    cats.forEach(c => html += `<option value="${c.id}" ${String(c.id) === String(selectedId) ? 'selected' : ''}>📁 ${c.name}</option>`);
    return html;
}
function roleOptions(selectedIds, multi) {
    const roles = ticketGuildData?.roles || [];
    const selected = selectedIds || [];
    return roles.map(r => `<option value="${r.id}" ${selected.includes(String(r.id)) ? 'selected' : ''}>@ ${r.name}</option>`).join('');
}

function renderStaffAndLogs() {
    // staff roles (multi-select)
    const staffSel = document.getElementById('tk-staff-roles');
    staffSel.innerHTML = roleOptions(ticketConfig?.staff_roles || []);
    // log channels
    const logs = ticketConfig?.logs || {};
    document.getElementById('tk-log-create').innerHTML = channelOptions(logs.create, '— no log —');
    document.getElementById('tk-log-close').innerHTML = channelOptions(logs.close, '— no transcript —');
    document.getElementById('tk-log-rating').innerHTML = channelOptions(logs.rating, '— no rating log —');
}

let allGuilds = [];

function renderSendChannel() {
    // server selector
    const serverSel = document.getElementById('tk-server');
    serverSel.innerHTML = `<option value="">— choose a server —</option>` +
        (allGuilds || []).map(g => `<option value="${g.id}" ${String(g.id) === String(ticketsGuildId) ? 'selected' : ''}>${g.name}</option>`).join('');
    // channel selector (depends on chosen server)
    const chSel = document.getElementById('tk-send-channel');
    if (ticketGuildData && ticketGuildData.channels) {
        chSel.innerHTML = channelOptions(ticketConfig?.channel_id, '— choose a channel —');
    } else {
        chSel.innerHTML = '<option value="">— choose a server first —</option>';
    }
}

async function onServerChange() {
    const serverSel = document.getElementById('tk-server');
    ticketsGuildId = serverSel.value;
    if (!ticketsGuildId) return;
    // reload config for the chosen server (to get its channels/roles)
    ticketGuildData = await api(`/api/tickets/config?guild_id=${ticketsGuildId}`);
    renderStaffAndLogs();
    renderSendChannel();
}

function renderTicketCategories(cats) {
    const box = document.getElementById('tk-categories');
    if (!cats || !Object.keys(cats).length) {
        box.innerHTML = '<div class="empty">No categories. Click "➕ Add Category".</div>';
        return;
    }
    box.innerHTML = Object.entries(cats).map(([cid, c]) => {
        const s = c.settings || {};
        return `
        <div class="tk-cat" data-cid="${cid}">
            <div class="tk-cat-head">
                <input type="text" class="tk-emoji" value="${c.emoji || ''}" placeholder="🎫" title="Emoji">
                <input type="text" class="tk-name" value="${c.name || ''}" placeholder="Category name">
                <label class="switch" title="Active"><input type="checkbox" class="tk-active" ${c.active !== false ? 'checked' : ''}><span class="slider"></span></label>
                <button class="btn small danger tk-del" onclick="removeCategory('${cid}')">🗑️</button>
            </div>
            <input type="text" class="tk-desc" value="${c.desc || ''}" placeholder="Description">
            <div class="tk-cat-grid">
                <div class="field"><label>Support Roles</label><select class="tk-roles" multiple size="2">${roleOptions(c.support_roles || [])}</select></div>
                <div class="field"><label>Ticket Channel Category</label><select class="tk-tcat">${categoryOptions(c.ticket_category_id)}</select></div>
                <div class="field"><label>Channel Naming Format</label><input type="text" class="tk-naming" value="${c.naming_format || 'ticket-{username}'}"></div>
                <div class="field"><label>Max Tickets / User</label><input type="number" class="tk-max" min="1" max="10" value="${s.max_tickets_per_user ?? 1}"></div>
            </div>
            <div class="tk-toggles">
                <label class="tk-toggle"><input type="checkbox" class="tk-ping-user" ${s.ping_user !== false ? 'checked' : ''}> Ping User</label>
                <label class="tk-toggle"><input type="checkbox" class="tk-ping-role" ${s.ping_role ? 'checked' : ''}> Ping Role</label>
                <label class="tk-toggle"><input type="checkbox" class="tk-user-close" ${s.user_can_close !== false ? 'checked' : ''}> User Can Close</label>
                <label class="tk-toggle"><input type="checkbox" class="tk-dm-open" ${s.dm_user_on_open !== false ? 'checked' : ''}> DM on Open</label>
                <label class="tk-toggle"><input type="checkbox" class="tk-dm-close" ${s.dm_user_on_close !== false ? 'checked' : ''}> DM on Close</label>
            </div>
            <div class="field block"><label>Welcome Message (when ticket opens)</label><textarea class="tk-welcome" rows="2">${s.welcome_message || ''}</textarea></div>
        </div>`;
    }).join('');
}

function collectTicketConfig() {
    const cats = {};
    document.querySelectorAll('#tk-categories .tk-cat').forEach(row => {
        const cid = row.dataset.cid;
        const sel = (el) => Array.from(row.querySelectorAll(el + ' option:checked')).map(o => o.value);
        cats[cid] = {
            emoji: row.querySelector('.tk-emoji').value,
            name: row.querySelector('.tk-name').value,
            desc: row.querySelector('.tk-desc').value,
            active: row.querySelector('.tk-active').checked,
            support_roles: sel('.tk-roles'),
            ticket_category_id: row.querySelector('.tk-tcat').value || null,
            naming_format: row.querySelector('.tk-naming').value,
            settings: {
                max_tickets_per_user: parseInt(row.querySelector('.tk-max').value) || 1,
                ping_user: row.querySelector('.tk-ping-user').checked,
                ping_role: row.querySelector('.tk-ping-role').checked,
                user_can_close: row.querySelector('.tk-user-close').checked,
                dm_user_on_open: row.querySelector('.tk-dm-open').checked,
                dm_user_on_close: row.querySelector('.tk-dm-close').checked,
                welcome_message: row.querySelector('.tk-welcome').value,
            },
        };
    });
    const staffRoles = Array.from(document.getElementById('tk-staff-roles').selectedOptions).map(o => o.value);
    return {
        name: document.getElementById('tk-name').value,
        display_type: document.getElementById('tk-display').value,
        placeholder: document.getElementById('tk-placeholder').value,
        channel_id: document.getElementById('tk-send-channel').value || null,
        panel_message: {
            title: document.getElementById('tk-title').value,
            description: document.getElementById('tk-desc').value,
        },
        logs: {
            create: document.getElementById('tk-log-create').value || null,
            close: document.getElementById('tk-log-close').value || null,
            rating: document.getElementById('tk-log-rating').value || null,
        },
        staff_roles: staffRoles,
        categories: cats,
    };
}

function addCategory() {
    if (!ticketConfig) ticketConfig = { categories: {} };
    if (!ticketConfig.categories) ticketConfig.categories = {};
    const cid = `cat_${Date.now()}_${catSeq++}`;
    ticketConfig.categories[cid] = {
        emoji: '🎫', name: 'New Category', desc: '', active: true,
        support_roles: [], ticket_category_id: null, naming_format: 'ticket-{username}',
        settings: { max_tickets_per_user: 1, ping_user: true, ping_role: false, user_can_close: true, dm_user_on_open: true, dm_user_on_close: true, welcome_message: '' },
    };
    renderTicketCategories(ticketConfig.categories);
}

function removeCategory(cid) {
    if (!ticketConfig?.categories) return;
    delete ticketConfig.categories[cid];
    renderTicketCategories(ticketConfig.categories);
}

async function saveTicketConfig() {
    const body = collectTicketConfig();
    body.guild_id = ticketsGuildId;
    const r = await api('/api/tickets/config', { method: 'POST', body: JSON.stringify(body) });
    const el = document.getElementById('tk-save-status');
    if (r.ok) {
        el.textContent = '✓ Saved';
        toast('Ticket settings saved');
        ticketConfig = r.config.panel;
    } else {
        el.textContent = '✗ Failed';
        toast(r.error || 'Failed to save', 'err');
    }
}

function renderPreview() {
    const cfg = collectTicketConfig();
    const cats = Object.values(cfg.categories || {}).filter(c => c.active !== false);
    const displayType = cfg.display_type || 'select';
    const panelName = cfg.name || 'Mangoli Bot';

    // 1. Discord-style embed
    document.getElementById('pv-author').textContent = panelName;
    document.getElementById('pv-title').textContent = cfg.panel_message.title || 'Open a Ticket';
    document.getElementById('pv-desc').textContent = cfg.panel_message.description || '';
    document.getElementById('pv-cats').innerHTML = cats.map(c => `${c.emoji} <b>${c.name}</b> — ${c.desc}`).join('<br>');

    // 2. Interactive controls (buttons OR dropdown)
    const controls = document.getElementById('pv-controls');
    if (displayType === 'buttons') {
        controls.innerHTML = cats.map(c =>
            `<button class="pv-btn primary" data-catid="${c.emoji}__${c.name}" onclick="previewOpenTicket('${JSON.stringify(c).replace(/'/g, "&#39;")}')">${c.emoji} ${c.name}</button>`
        ).join('');
    } else {
        controls.innerHTML = `<select class="pv-select" id="pv-select" onchange="previewSelectTicket()">
            <option value="" disabled selected>${cfg.placeholder || '🎫 Choose a category…'}</option>
            ${cats.map(c => `<option value="${encodeURIComponent(JSON.stringify(c))}">${c.emoji} ${c.name}</option>`).join('')}
        </select>`;
    }

    // reset result
    document.getElementById('pv-result').innerHTML = '<div class="empty">Click a button above to see how the ticket looks 👆</div>';
}

// Open a simulated ticket from a button click
function previewOpenTicket(catJson) {
    const cat = JSON.parse(catJson);
    previewShowTicket(cat);
}

function previewSelectTicket() {
    const sel = document.getElementById('pv-select');
    if (!sel.value) return;
    const cat = JSON.parse(decodeURIComponent(sel.value));
    previewShowTicket(cat);
}

function previewShowTicket(cat) {
    const settings = cat.settings || {};
    const welcome = settings.welcome_message || 'Please describe your issue and staff will assist shortly.';
    document.getElementById('pv-result').innerHTML = `
        <div class="sim-msg">
            <div class="sim-avatar">◆</div>
            <div class="sim-body">
                <div class="sim-name">Mangoli Bot</div>
                <div class="sim-embed">
                    <b># 🎫 Ticket #1</b><br>
                    ### ${cat.emoji} ${cat.name}<br><br>
                    Welcome <b>@you</b>!<br>
                    ${welcome}
                </div>
                <div class="sim-btns">
                    <span class="pv-btn primary">🙋 Claim</span>
                    <span class="pv-btn" style="background:#da373c">🔒 Close</span>
                    <span class="pv-btn green">🔓 Reopen</span>
                    <span class="pv-btn">📄 Transcript</span>
                    <span class="pv-btn">➕ Add</span>
                    <span class="pv-btn">🔔 Ping Staff</span>
                </div>
                <div class="de-footer" style="margin-top:8px">⚡ Mangoli Bot • by Nokiatis Community</div>
            </div>
        </div>`;
}

async function ticketAction(ticketId, action) {
    const r = await api(`/api/tickets/${ticketId}/action`, {
        method: 'POST', body: JSON.stringify({ guild_id: ticketsGuildId, action }),
    });
    toast(r.message || (r.ok ? 'Done' : 'Failed'), r.ok ? 'ok' : 'err');
    loadTickets();
}

async function sendTicketPanel() {
    const channel_id = document.getElementById('tk-send-channel').value;
    const server_id = document.getElementById('tk-server').value || ticketsGuildId;
    if (!server_id) { toast('Pick a server first', 'err'); return; }
    if (!channel_id) { toast('Pick a channel', 'err'); return; }
    // Save the current form first (so display_type etc. are applied before sending)
    const body = collectTicketConfig();
    body.guild_id = server_id;
    await api('/api/tickets/config', { method: 'POST', body: JSON.stringify(body) });
    // Now send the panel to the chosen channel
    const r = await api('/api/tickets/panel/send', {
        method: 'POST', body: JSON.stringify({ guild_id: server_id, channel_id }),
    });
    toast(r.ok ? `Panel sent to #${r.channel}` : (r.error || 'Failed'), r.ok ? 'ok' : 'err');
}

/* ── system ────────────────────────────────────────────────────── */
async function loadSystemInfo() {
    const s = await api('/api/system');
    const rows = Object.entries(s).map(([k, v]) => `<div class="sys-row"><span class="sys-key">${k}</span><span class="sys-val">${v}</span></div>`).join('');
    document.getElementById('sys-info').innerHTML = rows || '<div class="empty">No info.</div>';
}

/* ── wiring ────────────────────────────────────────────────────── */
document.getElementById('join-guild').addEventListener('change', updateChannels);
document.getElementById('join-btn').addEventListener('click', joinVoice);
document.getElementById('tts-speak').addEventListener('click', speakTTS);
document.getElementById('tts-text').addEventListener('input', (e) => {
    document.getElementById('tts-count').textContent = `${e.target.value.length} / 190`;
});
document.getElementById('pres-apply').addEventListener('click', applyPresence);
document.getElementById('ai-save').addEventListener('click', saveAI);
document.getElementById('bc-guild').addEventListener('change', updateBroadcastChannels);
document.getElementById('bc-send').addEventListener('click', sendBroadcast);
document.getElementById('cmd-reset').addEventListener('click', async () => {
    await api('/api/commands/stats/reset', { method: 'POST' });
    loadCommands(); toast('Command stats reset');
});
document.getElementById('log-clear').addEventListener('click', async () => {
    await api('/api/logs/clear', { method: 'POST' }); loadLogs();
});
document.getElementById('refresh-btn').addEventListener('click', () => { loadStatus(); toast('Refreshed'); });

document.getElementById('levels-guild').addEventListener('change', (e) => {
    levelsGuildId = e.target.value;
    loadLevels();
});

document.getElementById('sys-clear-logs').addEventListener('click', async () => {
    await api('/api/logs/clear', { method: 'POST' }); loadSystemInfo(); toast('Logs cleared');
});
document.getElementById('sys-reset-stats').addEventListener('click', async () => {
    await api('/api/commands/stats/reset', { method: 'POST' }); toast('Stats reset');
});
document.getElementById('sys-shutdown').addEventListener('click', async () => {
    if (!confirm('Shut down the bot? You will need to restart it manually.')) return;
    await api('/api/bot/shutdown', { method: 'POST' }); toast('Shutdown requested');
});
document.getElementById('sys-restart').addEventListener('click', async () => {
    if (!confirm('Restart the bot process?')) return;
    await api('/api/bot/restart', { method: 'POST' }); toast('Restarting…');
});

/* expose voice handlers globally (inline onclick) */
window.pauseVoice = pauseVoice;
window.resumeVoice = resumeVoice;
window.leaveVoice = leaveVoice;
window.stopVoice = stopVoice;
window.playSound = playSound;
window.toggleCommand = toggleCommand;

/* ── polling ───────────────────────────────────────────────────── */
setInterval(() => {
    if (currentPage === 'overview') loadStatus();
    if (currentPage === 'logs' && document.getElementById('log-auto').checked) loadLogs();
    if (currentPage === 'levels') loadLevels();
}, 3000);

/* ── boot ──────────────────────────────────────────────────────── */
(async () => {
    await fetchCsrf();
    loadStatus();
})();
console.log('%c  MANGOLI BOT DASHBOARD', 'color:#8b5cf6;font-weight:bold');
console.log('%c  Made with ❤️ by Nokiatis Community', 'color:#10b981');

/* ticket tab + wiring */
document.querySelectorAll('.ticket-tab').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('.ticket-tab').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        const tab = btn.dataset.tab;
        ['manage', 'setup', 'preview'].forEach(t => {
            document.getElementById(`tickets-${t}`).style.display = (t === tab) ? '' : 'none';
        });
        if (tab === 'preview') renderPreview();
    });
});
document.getElementById('tickets-guild').addEventListener('change', e => { ticketsGuildId = e.target.value; loadTickets(); });
document.getElementById('tk-save').addEventListener('click', saveTicketConfig);
document.getElementById('tk-send').addEventListener('click', sendTicketPanel);
document.getElementById('tk-add-cat').addEventListener('click', addCategory);
document.getElementById('tk-server').addEventListener('change', onServerChange);
window.ticketAction = ticketAction;
window.removeCategory = removeCategory;

window.previewOpenTicket = previewOpenTicket;
window.previewSelectTicket = previewSelectTicket;

/* economy wiring */
document.getElementById('economy-guild').addEventListener('change', e => { economyGuildId = e.target.value; loadEconomy(); });
window.ecoAction = ecoAction;
window.ecoSet = ecoSet;

/* music wiring */
document.getElementById('music-guild').addEventListener('change', e => { musicGuildId = e.target.value; loadMusic(); });
document.getElementById('music-play').addEventListener('click', musicPlay);
window.musicCtl = musicCtl;
window.musicVol = musicVol;

/* moderation wiring */
document.getElementById('mod-guild').addEventListener('change', e => { modGuildId = e.target.value; loadModeration(); });
document.getElementById('mod-search').addEventListener('input', loadModeration);
window.modAct = modAct;

/* giveaways wiring */
document.getElementById('gw-create').addEventListener('click', gwCreate);
window.gwEnd = gwEnd;
window.gwDelete = gwDelete;

/* announcements wiring */
document.getElementById('ann-guild').addEventListener('change', updateAnnChannels);
document.getElementById('ann-create').addEventListener('click', annCreate);
window.annDelete = annDelete;

/* stats wiring */
document.getElementById('stats-guild').addEventListener('change', e => { statsGuildId = e.target.value; loadStats(); });

/* role management wiring */
document.getElementById('role-add').addEventListener('click', () => roleAction('add'));
document.getElementById('role-remove').addEventListener('click', () => roleAction('remove'));

/* autorespond wiring */
document.getElementById('ar-guild').addEventListener('change', e => { arGuildId = e.target.value; loadAutorespond(); });
document.getElementById('ar-add').addEventListener('click', arAdd);
window.arRemove = arRemove;

/* backup wiring */
document.getElementById('backup-restore').addEventListener('click', backupRestore);

/* webhooks wiring */
document.getElementById('wh-guild').addEventListener('change', e => { whGuildId = e.target.value; loadWebhooks(); });
document.getElementById('wh-create').addEventListener('click', whCreate);
window.whDelete = whDelete;
