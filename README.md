<div align="center">

<img src="https://capsule-render.vercel.app/api?type=waving&color=gradient&customColorList=13,2,4&height=200&section=header&text=MANGOLI%20BOT&fontSize=48&fontColor=fff&animation=twinkling&fontAlignY=35&desc=Premium%20Multi-Service%20Checker%20Bot&descSize=20&descAlignY=55" width="100%" />

<br />

<img src="https://img.shields.io/badge/Version-2.0.0-e74c3c?style=for-the-badge&logo=appveyor&logoColor=white" />
<img src="https://img.shields.io/badge/Status-Active-brightgreen?style=for-the-badge&logo=power-off" />
<img src="https://img.shields.io/badge/Language-Python-3776AB?style=for-the-badge&logo=python&logoColor=white" />
<img src="https://img.shields.io/badge/Framework-discord.py-5865F2?style=for-the-badge&logo=discord&logoColor=white" />
<img src="https://img.shields.io/badge/AI-Groq%20%2B%20MiMo-FF6F00?style=for-the-badge&logo=openai&logoColor=white" />

<br /><br />

<img src="https://komarev.com/ghpvc/?username=itzraynx&repo=mangoli-bot&style=for-the-badge&color=e74c3c" />
<a href="https://github.com/itzraynx/mangoli-bot"><img src="https://img.shields.io/github/last-commit/itzraynx/mangoli-bot?style=for-the-badge&color=2ecc71" /></a>
<a href="https://github.com/itzraynx/mangoli-bot"><img src="https://img.shields.io/github/repo-size/itzraynx/mangoli-bot?style=for-the-badge&color=9b59b6" /></a>

<br /><br />

### ⚡ The Ultimate All-In-One Premium Checker Bot

<div align="center">
  <img src="https://skillicons.dev/icons?i=python,discord,flask,githubactions&theme=dark" alt="Tech Stack" />
</div>

</div>

---

## 🎯 Overview

**Mangoli Bot** is a production-grade Discord bot built for high-performance account checking across multiple platforms. Featuring async processing, beautiful embeds, AI-powered responses, a real-time web dashboard, and robust queue management.

> ⚡ Built by **NOKIATIS COMMUNITY** — NOVAGEN CLOUD SERVICES

---

## ✨ Features

<details>
<summary><h3>🔍 Account Checkers</h3></summary>

| Service | Status | Speed | Features |
|:-------:|:------:|:-----:|:--------:|
| 🎮 **Minecraft** | ✅ | Fast | Full Access / Semi / Migration |
| 🎮 **Steam** | ✅ | Fast | RSA Encrypted Login |
| 🎬 **Netflix** | ✅ | Fast | Plan Detection |
| 🏰 **Disney+** | ✅ | Fast | Subscription Info |
| 🍜 **Crunchyroll** | ✅ | Fast | Premium Detection |
| 🎵 **Spotify** | ✅ | Fast | Plan & Country |
| 🎮 **Mojang** | ✅ | Fast | Account Migration |

</details>

<details>
<summary><h3>🤖 AI Integration</h3></summary>

- **MiMo AI** — Smart conversational responses
- **Groq AI** — Lightning-fast AI completions
- Context-aware replies & natural conversations

</details>

<details>
<summary><h3>📊 Live Dashboard</h3></summary>

- Real-time statistics tracking
- Web-based control panel
- Live check results & history
- REST API for integrations

</details>

<details>
<summary><h3>🛡️ Bot Features</h3></summary>

- 🚀 **Async Processing** — ThreadPoolExecutor for parallel checks
- 📋 **Queue System** — Batch processing with progress tracking
- 🎨 **Beautiful Embeds** — Color-coded status with rich formatting
- ⚡ **Slash Commands** — Modern Discord app commands
- 🔒 **Rate Limiting** — Smart request throttling
- 🌐 **Proxy Support** — Configurable proxy rotation
- 📢 **Announcements** — Built-in announcement system

</details>

---

## 🛠️ Tech Stack

| Technology | Purpose |
|:----------|:--------|
| `Python 3.10+` | Core Language |
| `discord.py 2.0+` | Discord Bot Framework |
| `aiohttp` | Async HTTP Requests |
| `Flask` | Dashboard API Server |
| `PyCryptodome` | RSA Encryption (Steam) |
| `Groq SDK` | AI Integration |
| `PyNaCl` | Voice Channel Support |

---

## 📁 Project Structure

```
mangoli-bot/
├── 🤖 bot.py                    # Main bot entry point
├── 🚀 app.py                    # Flask dashboard server
├── 🎮 checker_module.py          # Minecraft checker engine
├── 🎮 steam_checker_enhanced.py  # Steam account checker
├── 🎬 netflix_checker.py         # Netflix checker
├── 🏰 disney_checker.py          # Disney+ checker
├── 🍜 crunchyroll_checker.py     # Crunchyroll checker
├── 🎵 spotify_checker.py         # Spotify checker
├── 🤖 mimo_ai.py                 # MiMo AI integration
├── 🧠 groq_ai.py                 # Groq AI integration
├── 📊 dashboard_api.py           # Dashboard REST API
├── 📈 dashboard_stats_tracker.py # Real-time stats engine
├── 📁 dashboard/                 # Web dashboard frontend
│   ├── index.html
│   ├── script.js
│   └── style.css
├── 📋 extra_checkers_commands.py # Additional commands
├── 🔧 fuzz_power.py             # Fuzzing utilities
├── 🔗 find_button.py            # Button interaction handler
├── 📄 requirements.txt           # Dependencies
└── 🚀 run.py                     # Launcher script
```

---

## ⚡ Quick Start

### Prerequisites

- Python 3.10+
- Discord Bot Token
- Groq API Key (for AI features)

### Installation

```bash
# Clone the repository
git clone https://github.com/itzraynx/mangoli-bot.git

# Navigate to project
cd mangoli-bot

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Configure your tokens in .env
cp .env.example .env

# Run the bot
python run.py
```

---

## 🎮 Commands

| Command | Description |
|:--------|:-----------|
| `/check` | Check Minecraft accounts |
| `/steam` | Check Steam accounts |
| `/netflix` | Check Netflix accounts |
| `/disney` | Check Disney+ accounts |
| `/crunchyroll` | Check Crunchyroll accounts |
| `/spotify` | Check Spotify accounts |
| `/ai` | Chat with AI assistant |
| `/queue` | View current queue status |
| `/stats` | View bot statistics |
| `/announce` | Send announcements |

---

## 📊 Dashboard

Access the live web dashboard at `http://localhost:5000` when the bot is running.

- 📈 Real-time check statistics
- 🎨 Beautiful responsive UI
- 📋 Live queue monitoring
- 🕐 Historical data tracking

---

## 📜 License

This project is proprietary software by **NOKIATIS COMMUNITY**.

---

<div align="center">

<img src="https://capsule-render.vercel.app/api?type=waving&color=gradient&customColorList=13,2,4&height=120&section=footer" width="100%" />

<br />
<b>Made with 💜 by</b> <a href="https://github.com/itzraynx"><b>itzraynx</b></a>

<br /><br />

<a href="https://github.com/itzraynx">
  <img src="https://img.shields.io/badge/GitHub-itzraynx-181717?style=for-the-badge&logo=github" />
</a>
<a href="https://discord.gg/">
  <img src="https://img.shields.io/badge/Discord-Join-5865F2?style=for-the-badge&logo=discord" />
</a>

</div>
