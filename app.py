import os
import sys
import json
import threading
import webview
from core.config import ConfigManager
from core.storage import StorageManager
from core.parser import parse_message
from core.api_server import APIServer, get_local_ip
from core.telegram_service import TelegramService
from core.notifier import send_macos_notification
from core.updater import UpdateManager

def get_resource_path(relative_path):
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), relative_path)

UI_DIR = get_resource_path("ui")
INDEX_PATH = os.path.join(UI_DIR, "index.html")
IOS_SCRIPT_PATH = get_resource_path(os.path.join("ios", "widget_ios.js"))

class ApiBridge:
    def __init__(self, config_mgr: ConfigManager, storage_mgr: StorageManager, tg_service: TelegramService, window=None):
        self.config_mgr = config_mgr
        self.storage_mgr = storage_mgr
        self.tg_service = tg_service
        self.window = window
        self.update_mgr = UpdateManager()

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

            notif = self.config_mgr.get("notifications", {})
            enable_banner = notif.get("banner", True) and notif.get("macos_banner", True)
            enable_sound = notif.get("sound", True) and notif.get("macos_sound", True)

            if enable_banner:
                if parsed["status"] == "OFF":
                    snd = "Basso" if enable_sound else ""
                    send_macos_notification(
                        "⚡ Внимание: Отключение света!",
                        f"Ориентировочно до {parsed['end_time_str'] or 'неизвестно'}",
                        f"{parsed['address']} ({parsed['reason']})",
                        sound=snd
                    )
                else:
                    snd = "Glass" if enable_sound else ""
                    send_macos_notification(
                        "💡 Свет включен!",
                        parsed['address'],
                        "Электросеть работает в штатном режиме.",
                        sound=snd
                    )

            self.broadcast_state(parsed)
            return parsed
        return None

    def get_config(self):
        return self.config_mgr.config

    def save_config(self, cfg):
        if isinstance(cfg, dict):
            self.config_mgr.update(cfg)
        return True

    def get_account_number(self):
        val = self.config_mgr.get("account_number", "")
        return val

    def save_account_number(self, val):
        val_str = str(val).strip()
        self.config_mgr.set("account_number", val_str)
        return True

    def get_history(self):
        return self.storage_mgr.get_history(limit=500)

    def get_daily_stats(self):
        return self.storage_mgr.load_daily_stats()

    def clear_history(self):
        return self.storage_mgr.clear_history()

    def check_for_updates(self):
        return self.update_mgr.check_updates()

    def perform_update(self):
        return self.update_mgr.pull_update()

    def restart_app(self):
        self.update_mgr.restart_application()
        return True

    def get_iphone_info(self):
        local_ip = get_local_ip()
        port = self.config_mgr.get("server", {}).get("port", 8088)
        endpoint = f"http://{local_ip}:{port}/api/status"
        
        script_content = ""
        if os.path.exists(IOS_SCRIPT_PATH):
            with open(IOS_SCRIPT_PATH, "r", encoding="utf-8") as f:
                script_content = f.read()
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

        def _sync_render():
            try:
                import urllib.request, ssl
                ctx = ssl._create_unverified_context()
                raw_text = state.get("raw_text", "")
                if not raw_text:
                    if state.get("status") == "OFF":
                        raw_text = f"❗️ За адресою {state.get('address')} зафіксовано відключення.\nПричина: {state.get('reason')}.\n🕦 Час початку: {state.get('start_time_str')}.\n🕦 Орієнтовний час відновлення електроенергії: {state.get('end_time_str')}."
                    else:
                        raw_text = f"✅ За адресою {state.get('address')} електропостачання відновлено!"

                payload = json.dumps({"text": raw_text}, ensure_ascii=False).encode("utf-8")
                req = urllib.request.Request(
                    "https://lightwidget.onrender.com/api/message",
                    data=payload,
                    headers={"Content-Type": "application/json; charset=utf-8"},
                    method="POST"
                )
                with urllib.request.urlopen(req, context=ctx, timeout=6) as resp:
                    print(f"[CloudSync] Synced status '{state.get('status')}' to Render ({resp.status})")
            except Exception as ex:
                print(f"[CloudSync] Render sync note: {ex}")

        threading.Thread(target=_sync_render, daemon=True).start()

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

    def on_state_updated(state):
        bridge.broadcast_state(state)

    def on_tg_status(status, message):
        bridge.broadcast_tg_status(status, message)

    tg_service = TelegramService(
        config_manager=config_mgr,
        storage_manager=storage_mgr,
        on_state_updated=on_state_updated,
        on_status_change=on_tg_status
    )
    bridge.tg_service = tg_service

    if config_mgr.get("telegram", {}).get("api_id") and config_mgr.get("telegram", {}).get("api_hash"):
        tg_service.start()

    api_port = config_mgr.get("server", {}).get("port", 8088)
    api_server = APIServer(
        host="0.0.0.0",
        port=api_port,
        storage=storage_mgr,
        on_message=on_state_updated
    )
    api_server.start()

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

    def on_window_loaded():
        acc = config_mgr.get("account_number", "")
        appr = config_mgr.get("appearance", {})
        notif = config_mgr.get("notifications", {})
        theme = appr.get("theme", "midnight")
        accent = appr.get("accent", "blue")
        show_sec = "true" if appr.get("show_seconds", True) else "false"
        show_pls = "true" if appr.get("show_pulse", True) else "false"
        show_stats = "true" if appr.get("show_stats", True) else "false"
        show_hmap = "true" if appr.get("show_heatmap", True) else "false"
        sound = "true" if notif.get("sound", True) else "false"
        banner = "true" if notif.get("banner", True) else "false"

        if window:
            escaped_acc = acc.replace("'", "\\'")
            window.evaluate_js(f"""
                (function() {{
                    try {{
                        if (window.applyTheme) window.applyTheme('{theme}', false);
                        if (window.applyAccent) window.applyAccent('{accent}', false);
                        if (window.appSettings) {{
                            window.appSettings.showSeconds = {show_sec};
                            window.appSettings.showPulse = {show_pls};
                            window.appSettings.showStats = {show_stats};
                            window.appSettings.showHeatmap = {show_hmap};
                            window.appSettings.sound = {sound};
                            window.appSettings.banner = {banner};
                        }}
                        if (window.applySettingsState) window.applySettingsState();

                        var el = document.getElementById('inputAccountNumber');
                        if (el) {{
                            el.value = '{escaped_acc}';
                            var len = Math.max(8, '{escaped_acc}'.length);
                            el.style.width = (len + 2) + 'ch';
                        }}
                    }} catch(e) {{
                        console.error('[Python inject error]', e);
                    }}
                }})();
            """)

    window.events.loaded += on_window_loaded

    try:
        webview.start(debug=False)
    finally:
        api_server.stop()
        tg_service.stop()
        os._exit(0)

if __name__ == "__main__":
    main()
