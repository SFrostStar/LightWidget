import os
import sys
import json
import ssl
import subprocess
import urllib.request
import urllib.error
from datetime import datetime

class UpdateManager:
    def __init__(self):
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.repo_name = self._detect_repo_name()

    def _detect_repo_name(self) -> str:
        try:
            cmd = ["git", "remote", "get-url", "origin"]
            res = subprocess.run(cmd, cwd=self.base_dir, capture_output=True, text=True)
            if res.returncode == 0 and res.stdout.strip():
                url = res.stdout.strip()
                if "github.com" in url:
                    part = url.split("github.com")[-1].lstrip("/:")
                    if part.endswith(".git"):
                        part = part[:-4]
                    if "/" in part:
                        return part
        except Exception:
            pass
        return "SFrostStar/LightWidget"

    def _parse_version(self, v_str: str) -> tuple:
        if not v_str:
            return (0, 0, 0)
        cleaned = v_str.strip().lower().lstrip("v")
        # Extract digits like 2.3.0 -> (2, 3, 0)
        parts = []
        for p in cleaned.split("."):
            num = ""
            for ch in p:
                if ch.isdigit():
                    num += ch
                else:
                    break
            parts.append(int(num) if num else 0)
        while len(parts) < 3:
            parts.append(0)
        return tuple(parts[:3])

    def get_local_version(self) -> dict:
        v_paths = [
            os.path.join(self.base_dir, "version.json"),
            os.path.join(getattr(sys, '_MEIPASS', self.base_dir), "version.json"),
            os.path.join(os.path.dirname(self.base_dir), "version.json")
        ]
        for vp in v_paths:
            if os.path.exists(vp):
                try:
                    with open(vp, "r", encoding="utf-8") as f:
                        vdata = json.load(f)
                        ver = vdata.get("version", "2.3.0")
                        return {
                            "version": ver,
                            "tag": f"v{ver}" if not ver.startswith("v") else ver,
                            "message": vdata.get("message", "LightWidget Release"),
                            "date": vdata.get("date", "2026-08-17")
                        }
                except Exception:
                    pass

        return {
            "version": "2.3.0",
            "tag": "v2.3.0",
            "message": "LightWidget Release",
            "date": "2026-08-17"
        }

    def check_updates(self) -> dict:
        local_info = self.get_local_version()
        local_tag = local_info.get("tag", "v2.3.0")
        local_v_tuple = self._parse_version(local_tag)

        headers = {
            "User-Agent": "LightWidget-AutoUpdater/1.0",
            "Accept": "application/vnd.github.v3+json"
        }

        try:
            ctx = ssl.create_default_context()
        except Exception:
            ctx = ssl._create_unverified_context()

        releases_list = []
        url = f"https://api.github.com/repos/{self.repo_name}/releases"
        try:
            req = urllib.request.Request(url, headers=headers)
            try:
                with urllib.request.urlopen(req, context=ctx, timeout=7) as response:
                    if response.status == 200:
                        releases_list = json.loads(response.read().decode('utf-8'))
            except Exception:
                uctx = ssl._create_unverified_context()
                with urllib.request.urlopen(req, context=uctx, timeout=7) as response:
                    if response.status == 200:
                        releases_list = json.loads(response.read().decode('utf-8'))
        except Exception as e:
            print(f"[Updater] Releases fetch error: {e}")

        if not releases_list or not isinstance(releases_list, list):
            return {
                "success": False,
                "error": "Не удалось получить список релизов с GitHub",
                "local": local_info,
                "has_update": False
            }

        # Filter out drafts
        valid_releases = [r for r in releases_list if not r.get("draft", False) and r.get("tag_name") != "main"]
        if not valid_releases:
            valid_releases = [r for r in releases_list if not r.get("draft", False)]

        if not valid_releases:
            return {
                "success": True,
                "has_update": False,
                "local": local_info,
                "message": "Релизы не найдены"
            }

        latest_rel = valid_releases[0]
        remote_tag = latest_rel.get("tag_name", "")
        remote_title = latest_rel.get("name", remote_tag)
        remote_body = latest_rel.get("body", "").strip()
        published_date = latest_rel.get("published_at", "")
        html_url = latest_rel.get("html_url", f"https://github.com/{self.repo_name}/releases")

        # Find matching platform asset
        assets = latest_rel.get("assets", [])
        download_url = None
        for a in assets:
            name = a.get("name", "").lower()
            if sys.platform == "win32" and name.endswith(".exe"):
                download_url = a.get("browser_download_url")
                break
            elif sys.platform == "darwin" and (name.endswith(".dmg") or name.endswith(".zip")):
                download_url = a.get("browser_download_url")
                break

        remote_v_tuple = self._parse_version(remote_tag)
        has_update = bool(remote_tag and remote_v_tuple > local_v_tuple)

        return {
            "success": True,
            "has_update": has_update,
            "local": local_info,
            "remote": {
                "tag": remote_tag,
                "title": remote_title,
                "message": remote_body or f"Новый релиз {remote_tag}",
                "date": published_date,
                "url": html_url,
                "download_url": download_url
            }
        }

    def pull_update(self) -> dict:
        is_frozen = getattr(sys, 'frozen', False)
        
        # 1. If running from source (has .git)
        if not is_frozen and os.path.exists(os.path.join(self.base_dir, ".git")):
            try:
                fetch_cmd = ["git", "fetch", "--all"]
                subprocess.run(fetch_cmd, cwd=self.base_dir, capture_output=True, text=True, check=True)

                pull_cmd = ["git", "pull", "--no-rebase", "origin", "main"]
                res = subprocess.run(pull_cmd, cwd=self.base_dir, capture_output=True, text=True, check=True)

                new_local = self.get_local_commit()
                return {
                    "success": True,
                    "output": res.stdout,
                    "new_commit": new_local
                }
            except subprocess.CalledProcessError as e:
                err_msg = e.stderr or e.stdout or str(e)
                return {
                    "success": False,
                    "error": f"Ошибка git pull: {err_msg}"
                }
            except Exception as e:
                return {
                    "success": False,
                    "error": str(e)
                }

        # 2. If running as compiled standalone binary (.exe on Windows / .app on macOS)
        try:
            headers = {"User-Agent": "LightWidget-AutoUpdater/1.0"}
            url = f"https://api.github.com/repos/{self.repo_name}/releases/latest"
            req = urllib.request.Request(url, headers=headers)
            uctx = ssl._create_unverified_context()
            with urllib.request.urlopen(req, context=uctx, timeout=8) as resp:
                rel_data = json.loads(resp.read().decode('utf-8'))
            
            assets = rel_data.get("assets", [])
            download_url = None
            for a in assets:
                name = a.get("name", "").lower()
                if sys.platform == "win32" and name.endswith(".exe"):
                    download_url = a.get("browser_download_url")
                    break
                elif sys.platform == "darwin" and (name.endswith(".dmg") or name.endswith(".zip")):
                    download_url = a.get("browser_download_url")
                    break

            if download_url:
                target_file = os.path.join(self.base_dir, "LightWidget_update" + (".exe" if sys.platform == "win32" else ".dmg"))
                req2 = urllib.request.Request(download_url, headers=headers)
                with urllib.request.urlopen(req2, context=uctx, timeout=30) as r, open(target_file, "wb") as f:
                    f.write(r.read())
                
                return {
                    "success": True,
                    "downloaded_file": target_file,
                    "is_binary": True
                }
        except Exception as be:
            print(f"[Updater] Release asset download note: {be}")

        return {
            "success": True,
            "message": "Обновление готово к применению"
        }

    def restart_application(self):
        try:
            is_frozen = getattr(sys, 'frozen', False)
            if is_frozen:
                exe_path = sys.executable
                if sys.platform == "win32":
                    update_file = os.path.join(self.base_dir, "LightWidget_update.exe")
                    if os.path.exists(update_file):
                        bat_script = f"""@echo off
timeout /t 1 /nobreak > NUL
move /y "{update_file}" "{exe_path}"
start "" "{exe_path}"
del "%~f0"
"""
                        bat_path = os.path.join(self.base_dir, "update_swap.bat")
                        with open(bat_path, "w") as f:
                            f.write(bat_script)
                        creation_flag = getattr(subprocess, 'CREATE_NO_WINDOW', 0x08000000)
                        subprocess.Popen(["cmd.exe", "/c", bat_path], shell=True, creationflags=creation_flag)
                        os._exit(0)
                    else:
                        creation_flag = getattr(subprocess, 'CREATE_NO_WINDOW', 0x08000000)
                        subprocess.Popen([exe_path], creationflags=creation_flag)
                        os._exit(0)
                elif sys.platform == "darwin":
                    if ".app" in exe_path:
                        app_bundle = exe_path.split(".app")[0] + ".app"
                        subprocess.Popen(["open", "-n", app_bundle], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    else:
                        subprocess.Popen(["open", "-n", exe_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    os._exit(0)

            # Check if LightWidget.app exists on Desktop or in Applications
            if sys.platform == "darwin":
                app_candidates = [
                    "/Applications/LightWidget.app",
                    os.path.expanduser("~/Desktop/LightWidget.app"),
                    os.path.join(self.base_dir, "LightWidget.app")
                ]
                for ap in app_candidates:
                    if os.path.exists(ap):
                        subprocess.Popen(["open", "-n", ap], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        os._exit(0)

            # Pure detached silent restart without opening any terminal
            python = sys.executable
            app_py = os.path.join(self.base_dir, "app.py")
            if sys.platform == "win32":
                creation_flag = getattr(subprocess, 'CREATE_NO_WINDOW', 0x08000000)
                subprocess.Popen([python, app_py], cwd=self.base_dir, creationflags=creation_flag)
            else:
                subprocess.Popen(
                    [python, app_py],
                    cwd=self.base_dir,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True
                )
            os._exit(0)
        except Exception as e:
            print(f"[Updater] Restart error: {e}")
            os._exit(0)
