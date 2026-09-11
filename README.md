<div align="center">

# 🎮 Mangoli Bot

**The Ultimate All-In-One Discord Bot**

<img src="https://img.shields.io/badge/Language-Python-3776AB?style=for-the-badge&logo=python&logoColor=white" />
<img src="https://img.shields.io/badge/Framework-discord.py-5865F2?style=for-the-badge&logo=discord&logoColor=white" />
<img src="https://img.shields.io/badge/Music-Lavalink-FF6F00?style=for-the-badge" />
<img src="https://img.shields.io/badge/Dashboard-Flask-000000?style=for-the-badge&logo=flask&logoColor=white" />

> ⚡ Built by **NOKIATIS COMMUNITY**

</div>

---

## 🎯 Overview

**Mangoli Bot** is a feature-rich Discord bot with a live web control panel. It combines leveling, a full coin economy, support tickets, moderation, music playback, and mini-games — all in one bot.

---

## ✨ Features

| System | Highlights |
|--------|-----------|
| 🏆 **Leveling** | XP for chat/voice/invites, ranks, leaderboards, weekly seasons, daily streaks, 12 achievements |
| 💰 **Economy** | Coins, `/give`, coinflip, slots, shop with XP boosters & lucky charms, rich leaderboard |
| 🎫 **Tickets** | Panel (dropdown/buttons), claim/close/reopen, transcripts, star ratings, blacklist, auto-close |
| 🎵 **Music** | Lavalink — YouTube, YouTube Music, SoundCloud, Spotify, playlists, queue, filters, lyrics |
| 🛡️ **Moderation** | `/purgeuser` (server-wide or last N hours), `/purge` |
| 🎮 **Mini-Games** | Rock-paper-scissors, guess the number, 8-ball |
| 🔊 **Voice** | Join voice, Moroccan meme sounds, custom MyInstants links |
| 📊 **Dashboard** | Live web control panel — status, voice, logs, servers, commands, levels, settings |

---

## 📥 Installation

```bash
git clone <your-repo-url>
cd mangoli-bot-main
pip install -r requirements.txt
```

### Configuration

Edit `bot.py`:
- `TOKEN` — your Discord bot token
- `MIMO_API_KEY` — your MiMo AI key (for the AI chat)

Edit `music.py`:
- `LAVALINK_URI` + `LAVALINK_PASSWORD` — your Lavalink server (or use a free public node)

### Run

```bash
python run.py
```

This starts **both** the Discord bot and the web dashboard (default `http://localhost:5000`).

---

## 📋 Commands

| Category | Commands |
|----------|----------|
| Leveling | `/rank` `/leaderboard` `/weekly` `/achievements` `/invites` `/daily` |
| Economy | `/balance` `/give` `/coinflip` `/slots` `/shop` `/buy` `/rich` |
| Tickets | `/panel` `/settings` `/blacklist` `/claim` `/unclaim` `/close` `/reopen` `/ticketdelete` `/ticketadd` `/ticketremove` `/transcript` |
| Music | `/join` `/play` `/pause` `/resume` `/skip` `/stop` `/nowplaying` `/queue` `/volume` `/loop` `/shuffle` `/seek` `/autoplay` `/lyrics` `/leave` |
| Moderation | `/purgeuser` `/purge` |
| Games | `/rps` `/guess` `/8ball` |
| Voice | `/voicejoin` `/voicestop` `/voiceplay` `/voiceleave` `/voicestatus` `/playsoundlink` |
| General | `/help` `/stats` `/serverstats` `/profile` `/personality` `/poll` |

---

## 📊 Dashboard

The web dashboard lets you control the bot from a browser:
- **Overview** — bot status, latency, uptime, servers
- **Voice** — join/pause/resume/leave voice channels
- **Logs** — live log feed with export
- **Servers / Commands** — guild list + command usage
- **Levels** — full XP/coins leaderboard
- **Presence** — change status & activity
- **AI Brain** — personality, channel, custom persona
- **Broadcast** — send messages as the bot
- **System** — info + restart/shutdown

---

## ⚙️ Requirements

- Python 3.10+
- A running **Lavalink** server (for music) — or use a free public node
- `ffmpeg` installed on the host (for voice audio)

---

## 🤝 Credits

> ⚡ Built by **NOKIATIS COMMUNITY**

