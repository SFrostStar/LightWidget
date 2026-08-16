import sys
import subprocess
import os

def send_notification(title: str, subtitle: str, message: str, sound: str = "Submarine"):
    if sys.platform == "darwin":
        try:
            script = f'display notification "{message}" with title "{title}" subtitle "{subtitle}"'
            if sound:
                script += f' sound name "{sound}"'
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
