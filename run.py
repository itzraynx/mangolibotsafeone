# ═══════════════════════════════════════════════════════════════════════════════
# NOVAGEN BOT - Main Runner
# Use this file to start the bot on Python hosting
# ═══════════════════════════════════════════════════════════════════════════════

import threading
import time

# Import and run the bot
from bot import bot, TOKEN

def start_dashboard():
    """Start the dashboard API server in a separate thread."""
    try:
        from dashboard_api import start_dashboard_server
        start_dashboard_server(port=5000, debug=False)
    except Exception as e:
        print(f"[Dashboard] Failed to start: {e}")
        print("[Dashboard] The dashboard will not be available.")

if __name__ == "__main__":
    print("")
    print("═" * 60)
    print("  🎮 NOVAGEN BOT")
    print("  ⚡ by Nokiatis Community")
    print("═" * 60)
    print("")
    
    # Start dashboard server first
    print("[Startup] Starting dashboard server...")
    dashboard_thread = threading.Thread(target=start_dashboard, daemon=True)
    dashboard_thread.start()
    time.sleep(1)  # Give dashboard time to start
    
    # Then start the bot
    print("[Startup] Starting Discord bot...")
    print("")
    bot.run(TOKEN)
