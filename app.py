# ═══════════════════════════════════════════════════════════════════════════════
# MANGOLI BOT - app.py (Pterodactyl Entry Point)
# This file is the main entry point for Pterodactyl hosting
# ═══════════════════════════════════════════════════════════════════════════════

# Import everything from bot.py and run
from bot import bot, TOKEN, logger

if __name__ == "__main__":
    logger.info("Starting Mangoli Bot via app.py...")
    logger.info("=" * 60)
    bot.run(TOKEN)
