import os
import sys
import json
import webview
from core.config import ConfigManager
from core.storage import StorageManager
from core.parser import parse_message
from core.api_server import APIServer, get_local_ip
from core.telegram_service import TelegramService
from core.notifier import send_macos_notification

UI_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ui")
INDEX_PATH = os.path.join(UI_DIR, "index.html")
IOS_SCRIPT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ios", "widget_ios.js")

class ApiBridge:
    def __init__(self, config_mgr, storage_mgr, tg_service, window=None):
        self.config_mgr = config_mgr
        self.storage_mgr = storage_mgr
        self.tg_service = tg_service
        self.window = window

    def set_window(self, window):
        self.window = window

    def get_state(self):
        st = self.storage_mgr.get_state()
        if isinstance(st, dict):
            st = st.copy()
            st["account_number"] = self.config_mgr.get("account_number", "")
        return st

    def parse_and_apply(self, text):
        parsed = parse_message(text)
        if parsed:
            self.storage_mgr.save_state(parsed)
            self.storage_mgr.add_history(parsed)

            # Trigger native notification
            if parsed["status"] == "OFF":
                send_macos_notification(
                    "⚡ Внимание: Отключение света!",
                    f"Ориентировочно до {parsed['end_time_str'] or 'неизвестно'}",
                    f"{parsed['address']} ({parsed['reason']})",
                    sound="Basso"
                )
            else:
                send_macos_notification(
                    "💡 Свет включен!",
                    parsed['address'],
                    "Электросеть работает в штатном режиме.",
                    sound="Glass"
                )

            self.broadcast_state(parsed)
            return parsed
        return None

    def get_config(self):
        return self.config_mgr.config

    def save_config(self, cfg):
        for k, v in cfg.items():
            self.config_mgr.config[k] = v
        self.config_mgr.save()
        return True

    def get_account_number(self):
        val = self.config_mgr.get("account_number", "")
        print(f"[ApiBridge] get_account_number -> '{val}'")
        return val

    def save_account_number(self, val):
        val_str = str(val).strip()
        print(f"[ApiBridge] save_account_number -> '{val_str}'")
        self.config_mgr.set("account_number", val_str)
        return True

    def get_history(self):
        return self.storage_mgr.get_history()

    def clear_history(self):
        return self.storage_mgr.clear_history()

    def get_iphone_info(self):
        local_ip = get_local_ip()
        port = self.config_mgr.get("server", {}).get("port", 8088)
        endpoint = f"http://{local_ip}:{port}/api/status"
        
        script_content = ""
        if os.path.exists(IOS_SCRIPT_PATH):
            with open(IOS_SCRIPT_PATH, "r", encoding="utf-8") as f:
                script_content = f.read()
                # Substitute the actual local IP
                script_content = script_content.replace(
                    'const SERVER_URL = "http://localhost:8088/api/status";',
                    f'const SERVER_URL = "{endpoint}";'
                )

        return {
            "local_ip": local_ip,
            "port": port,
            "endpoint": endpoint,
            "scriptable_code": script_content
        }

    def connect_telegram(self):
        self.tg_service.start()
        return {"status": "started"}

    def disconnect_telegram(self):
        self.tg_service.stop()
        return {"status": "stopped"}

    def submit_tg_code(self, code):
        return self.tg_service.submit_code(code)

    def submit_tg_password(self, password):
        return self.tg_service.submit_password(password)

    def sync_history(self):
        if self.tg_service:
            self.tg_service.sync_now()
        return self.storage_mgr.get_state()

    def set_widget_mode(self, enabled: bool):
        if not self.window:
            return {"success": False}
        
        try:
            import Cocoa
            import Quartz

            def apply_cocoa_window_mode():
                try:
                    app = Cocoa.NSApplication.sharedApplication()
                    for w in app.windows():
                        if w.title() == "LightWidget":
                            w.setOpaque_(False)
                            w.setBackgroundColor_(Cocoa.NSColor.clearColor())
                            w.setHasShadow_(True)
                            if enabled:
                                behavior = (
                                    Cocoa.NSWindowCollectionBehaviorCanJoinAllSpaces |
                                    Cocoa.NSWindowCollectionBehaviorStationary |
                                    Cocoa.NSWindowCollectionBehaviorIgnoresCycle
                                )
                                w.setCollectionBehavior_(behavior)
                                w.setLevel_(Quartz.kCGDesktopIconWindowLevel + 1)
                            else:
                                w.setLevel_(Cocoa.NSNormalWindowLevel)
                                w.setCollectionBehavior_(Cocoa.NSWindowCollectionBehaviorDefault)
                except Exception as e:
                    print(f"[DesktopMode MainThread] {e}")

            if enabled:
                self.window.resize(165, 165)
            else:
                self.window.resize(840, 560)

            # Safely perform on macOS Main AppKit thread
            Cocoa.NSOperationQueue.mainQueue().addOperationWithBlock_(apply_cocoa_window_mode)
            return {"success": True, "mode": "widget" if enabled else "normal"}
        except Exception as ex:
            print(f"[ApiBridge] Error setting widget mode: {ex}")
            if enabled:
                self.window.resize(165, 165)
            else:
                self.window.resize(840, 560)
            return {"success": True}

    def minimize(self):
        if self.window:
            self.window.minimize()

    def close(self):
        if self.tg_service:
            self.tg_service.stop()
        if self.window:
            self.window.destroy()
        os._exit(0)

    def broadcast_state(self, state):
        if self.window:
            try:
                state_json = json.dumps(state, ensure_ascii=False)
                self.window.evaluate_js(f"window.onStateUpdatedFromPython({state_json});")
            except Exception as e:
                print(f"[Bridge] Error evaluating JS broadcast: {e}")

    def broadcast_tg_status(self, status, message):
        if self.window:
            try:
                msg_json = json.dumps(message, ensure_ascii=False)
                self.window.evaluate_js(f"window.onTelegramStatusChange('{status}', {msg_json});")
            except Exception as e:
                print(f"[Bridge] Error evaluating TG status JS: {e}")

def main():
    config_mgr = ConfigManager()
    storage_mgr = StorageManager()

    bridge = ApiBridge(config_mgr, storage_mgr, None)

    # Handlers for background services
    def on_state_updated(state):
        bridge.broadcast_state(state)

    def on_tg_status(status, message):
        bridge.broadcast_tg_status(status, message)

    # Initialize Telegram Service
    tg_service = TelegramService(
        config_manager=config_mgr,
        storage_manager=storage_mgr,
        on_state_updated=on_state_updated,
        on_status_change=on_tg_status
    )
    bridge.tg_service = tg_service

    # Auto-connect if credentials already exist
    if config_mgr.get("telegram", {}).get("api_id") and config_mgr.get("telegram", {}).get("api_hash"):
        tg_service.start()

    # Initialize and Start HTTP API Server for iPhone / Scriptable
    api_port = config_mgr.get("server", {}).get("port", 8088)
    api_server = APIServer(
        host="0.0.0.0",
        port=api_port,
        storage=storage_mgr,
        on_message=on_state_updated
    )
    api_server.start()

    # Create Pywebview Window
    window = webview.create_window(
        title="LightWidget",
        url=INDEX_PATH,
        js_api=bridge,
        width=860,
        height=590,
        resizable=True,
        frameless=True,
        easy_drag=True,
        transparent=True,
        background_color="#141518"
    )
    bridge.set_window(window)
    window.events.closed += lambda: os._exit(0)

    # After page loads, inject account number directly into the DOM
    def on_window_loaded():
        acc = config_mgr.get("account_number", "")
        print(f"[Window] Loaded. Injecting account_number='{acc}'")
        if acc and window:
            escaped = acc.replace("'", "\\'")
            window.evaluate_js(f"""
                (function() {{
                    var el = document.getElementById('inputAccountNumber');
                    if (el) {{
                        el.value = '{escaped}';
                        var len = Math.max(8, '{escaped}'.length);
                        el.style.width = (len + 2) + 'ch';
                        console.log('[Python inject] set account to: {escaped}');
                    }}
                }})();
            """)

    window.events.loaded += on_window_loaded

    # Start Pywebview GUI Loop
    try:
        webview.start(debug=False)
    finally:
        api_server.stop()
        tg_service.stop()
        os._exit(0)

if __name__ == "__main__":
    main()
