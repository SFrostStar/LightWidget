import sys
import subprocess
import os

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_HELPER_APP_BIN = os.path.join(_BASE_DIR, "core", "notifier_bundle", "LightWidgetNotifier.app", "Contents", "MacOS", "notifier_bin")

def _setup_macos_notifications():
    pass

def send_notification(title: str, subtitle: str, message: str, sound: str = "Submarine"):
    if sys.platform == "darwin":
        if os.path.exists(_HELPER_APP_BIN) and os.access(_HELPER_APP_BIN, os.X_OK):
            try:
                cmd = [_HELPER_APP_BIN, str(title), str(subtitle or ""), str(message or ""), str(sound or "")]
                subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return
            except Exception:
                pass

        try:
            from Cocoa import NSApplication, NSImage, NSObject
            from Foundation import NSUserNotification, NSUserNotificationCenter
            
            app = NSApplication.sharedApplication()
            for name in ["ui/flat_app_icon.png", "ui/AppIcon.icns"]:
                p = os.path.join(_BASE_DIR, name)
                if os.path.exists(p):
                    img = NSImage.alloc().initWithContentsOfFile_(p)
                    if img:
                        app.setApplicationIconImage_(img)
                        break

            notification = NSUserNotification.alloc().init()
            notification.setTitle_(str(title))
            if subtitle:
                notification.setSubtitle_(str(subtitle))
            notification.setInformativeText_(str(message))
            if sound:
                notification.setSoundName_(str(sound))
            center = NSUserNotificationCenter.defaultUserNotificationCenter()
            center.deliverNotification_(notification)
            return
        except Exception:
            pass

        try:
            clean_title = str(title).replace('"', '\\"')
            clean_sub = str(subtitle).replace('"', '\\"')
            clean_msg = str(message).replace('"', '\\"')
            snd_clause = f' sound name "{sound}"' if sound else ''
            script = f'display notification "{clean_msg}" with title "{clean_title}" subtitle "{clean_sub}"{snd_clause}'
            cmd = ["osascript", "-e", script]
            subprocess.run(cmd, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            print(f"[Notifier] macOS error: {e}")
    elif sys.platform == "win32":
        try:
            ps_script = f'''
            [void] [System.Reflection.Assembly]::LoadWithPartialName("System.Windows.Forms");
            $obj = New-Object System.Windows.Forms.NotifyIcon;
            $obj.Icon = [System.Drawing.SystemIcons]::Information;
            $obj.BalloonTipTitle = "{title}";
            $obj.BalloonTipText = "{subtitle}`n{message}";
            $obj.Visible = $True;
            $obj.ShowBalloonTip(5000);
            '''
            cmd = ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_script]
            subprocess.run(cmd, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            print(f"[Notifier] Windows error: {e}")

send_macos_notification = send_notification

