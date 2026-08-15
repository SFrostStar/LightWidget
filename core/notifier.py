import subprocess
import shlex

def send_macos_notification(title: str, subtitle: str, message: str, sound: str = "Submarine"):
    """
    Sends a native macOS desktop notification using AppleScript.
    """
    try:
        script = f'display notification "{message}" with title "{title}" subtitle "{subtitle}"'
        if sound:
            script += f' sound name "{sound}"'
        
        cmd = ["osascript", "-e", script]
        subprocess.run(cmd, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        print(f"[Notifier] Error sending notification: {e}")
