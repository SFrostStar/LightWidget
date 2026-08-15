import os
import sys
import time
import signal
import threading
import urllib.request
from core.config import ConfigManager
from core.storage import StorageManager
from core.api_server import APIServer, get_local_ip
from core.telegram_service import TelegramService

def start_keep_alive(app_url):
    def pinger():
        print(f"[KeepAlive] Self-pinger active for: {app_url}")
        while True:
            time.sleep(8 * 60)  # Ping every 8 minutes (Render sleeps after 15 min of inactivity)
            try:
                target = f"{app_url.rstrip('/')}/api/health"
                req = urllib.request.Request(target, headers={"User-Agent": "LightWidget-KeepAlive/1.0"})
                with urllib.request.urlopen(req, timeout=20) as resp:
                    print(f"[KeepAlive] Ping {target} -> Status {resp.status}")
            except Exception as e:
                print(f"[KeepAlive] Ping note: {e}")

    t = threading.Thread(target=pinger, daemon=True)
    t.start()

def main():
    print("=" * 50)
    print("⚡ LightWidget Headless Server (24/7 Mode)")
    print("=" * 50)

    config_mgr = ConfigManager()
    storage_mgr = StorageManager()

    # Handlers for background services
    def on_state_updated(state):
        print(f"[Server] State updated: {state.get('status')} | Address: {state.get('address')}")

    def on_tg_status(status, message):
        print(f"[Telegram] Status: {status} | {message}")

    # Initialize Telegram Service
    tg_service = TelegramService(
        config_manager=config_mgr,
        storage_manager=storage_mgr,
        on_state_updated=on_state_updated,
        on_status_change=on_tg_status
    )

    # Start Telegram service if credentials exist
    if config_mgr.get("telegram", {}).get("api_id") and config_mgr.get("telegram", {}).get("api_hash"):
        print("[Telegram] Starting Telegram service...")
        tg_service.start()
    else:
        print("[Telegram] Warning: API ID / Hash not found in config. Please configure config.json.")

    # Initialize and Start HTTP API Server
    api_port = int(os.environ.get("PORT", config_mgr.get("server", {}).get("port", 8088)))
    api_server = APIServer(
        host="0.0.0.0",
        port=api_port,
        storage=storage_mgr,
        on_message=on_state_updated
    )
    api_server.start()

    # Start KeepAlive Self-Pinger for Render / Cloud (to prevent sleep mode)
    external_url = os.environ.get("RENDER_EXTERNAL_URL") or "https://lightwidget.onrender.com"
    if external_url:
        start_keep_alive(external_url)

    local_ip = get_local_ip()
    print(f"[API Server] Listening on http://0.0.0.0:{api_port}")
    print(f"[API Server] Local endpoint: http://{local_ip}:{api_port}/api/status")
    print("=" * 50)
    print("Server is running 24/7. Press Ctrl+C to stop.")

    # Handle graceful shutdown
    def shutdown(sig, frame):
        print("\nShutting down server...")
        api_server.stop()
        tg_service.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    # Keep main thread alive
    while True:
        time.sleep(1)

if __name__ == "__main__":
    main()
