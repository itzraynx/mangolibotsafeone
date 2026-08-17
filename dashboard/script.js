/* ═══════════════════════════════════════════════════════════════════
   NOVAGEN BOT DASHBOARD — front-end logic
   by Nokiatis Community
   ═══════════════════════════════════════════════════════════════════ */

const API_BASE = '';
let currentPage = 'overview';
let guildsCache = [];

/* ── helpers ───────────────────────────────────────────────────── */
async function api(path, opts = {}) {
    try {
        const res = await fetch(`${API_BASE}${path}`, {
            headers: { 'Content-Type': 'application/json' },
            ...opts,
        });
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

    document.getElementById('hero-name').textContent = s.bot_name || 'Novagen';
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

/* ── system ────────────────────────────────────────────────────── */
async function loadSystemInfo() {
    const s = await api('/api/system');
    const rows = Object.entries(s).map(([k, v]) => `<div class="sys-row"><span class="sys-key">${k}</span><span class="sys-val">${v}</span></div>`).join('');
    document.getElementById('sys-info').innerHTML = rows || '<div class="empty">No info.</div>';
}

/* ── wiring ────────────────────────────────────────────────────── */
document.getElementById('join-guild').addEventListener('change', updateChannels);
document.getElementById('join-btn').addEventListener('click', joinVoice);
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
loadStatus();
console.log('%c  NOVAGEN BOT DASHBOARD', 'color:#8b5cf6;font-weight:bold');
console.log('%c  Made with ❤️ by Nokiatis Community', 'color:#10b981');
