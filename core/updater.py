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

    def get_local_commit(self) -> dict:
        try:
            cmd = ["git", "rev-parse", "HEAD"]
            res = subprocess.run(cmd, cwd=self.base_dir, capture_output=True, text=True, check=True)
            sha = res.stdout.strip()

            msg_cmd = ["git", "log", "-1", "--pretty=%B"]
            msg_res = subprocess.run(msg_cmd, cwd=self.base_dir, capture_output=True, text=True)
            msg = msg_res.stdout.strip() if msg_res.returncode == 0 else ""

            date_cmd = ["git", "log", "-1", "--pretty=%cd", "--date=iso"]
            date_res = subprocess.run(date_cmd, cwd=self.base_dir, capture_output=True, text=True)
            date_str = date_res.stdout.strip() if date_res.returncode == 0 else ""

            return {
                "sha": sha,
                "short_sha": sha[:7] if sha else "unknown",
                "message": msg,
                "date": date_str
            }
        except Exception:
            return {
                "sha": "local",
                "short_sha": "local",
                "message": "Локальная сборка",
                "date": datetime.now().isoformat()
            }

    def check_updates(self) -> dict:
        local_info = self.get_local_commit()
        local_sha = local_info.get("sha", "")

        # 1. Primary check via git ls-remote (works with private/public and SSH/HTTPS credentials)
        remote_sha = ""
        try:
            res = subprocess.run(["git", "ls-remote", "origin", "main"], cwd=self.base_dir, capture_output=True, text=True, timeout=6)
            if res.returncode == 0 and res.stdout.strip():
                remote_sha = res.stdout.strip().split()[0]
        except Exception:
            pass

        # 2. If git ls-remote didn't return or we want rich commit metadata, query GitHub API
        headers = {
            "User-Agent": "LightWidget-AutoUpdater/1.0",
            "Accept": "application/vnd.github.v3+json"
        }

        try:
            ctx = ssl.create_default_context()
        except Exception:
            ctx = ssl._create_unverified_context()

        remote_data = None
        if self.repo_name:
            url = f"https://api.github.com/repos/{self.repo_name}/commits/main"
            try:
                req = urllib.request.Request(url, headers=headers)
                try:
                    with urllib.request.urlopen(req, context=ctx, timeout=5) as response:
                        if response.status == 200:
                            remote_data = json.loads(response.read().decode('utf-8'))
                except Exception:
                    uctx = ssl._create_unverified_context()
                    with urllib.request.urlopen(req, context=uctx, timeout=5) as response:
                        if response.status == 200:
                            remote_data = json.loads(response.read().decode('utf-8'))
            except Exception:
                pass

        if remote_data and "sha" in remote_data:
            remote_sha = remote_data.get("sha", "")
            commit_obj = remote_data.get("commit", {})
            message = commit_obj.get("message", "").strip()
            author_name = commit_obj.get("author", {}).get("name", "Разработчик")
            commit_date = commit_obj.get("author", {}).get("date", "")
            html_url = remote_data.get("html_url", "")
        else:
            message = f"Новые обновления в ветке main ({remote_sha[:7]})" if remote_sha else ""
            author_name = "GitHub"
            commit_date = ""
            html_url = f"https://github.com/{self.repo_name}"

        if not remote_sha:
            return {
                "success": False,
                "error": "Не удалось связаться с удаленным репозиторием (проверьте интернет)",
                "local": local_info,
                "has_update": False
            }

        has_update = bool(local_sha and remote_sha and local_sha != remote_sha and local_sha != "local")

        return {
            "success": True,
            "has_update": has_update,
            "local": local_info,
            "remote": {
                "sha": remote_sha,
                "short_sha": remote_sha[:7] if remote_sha else "unknown",
                "message": message,
                "author": author_name,
                "date": commit_date,
                "url": html_url
            }
        }

    def pull_update(self) -> dict:
        try:
            # 1. Fetch
            fetch_cmd = ["git", "fetch", "--all"]
            subprocess.run(fetch_cmd, cwd=self.base_dir, capture_output=True, text=True, check=True)

            # 2. Pull
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

    def restart_application(self):
        try:
            python = sys.executable
            if sys.platform == "darwin":
                script = f'do shell script "{python} \\"{os.path.join(self.base_dir, "app.py")}\\" > /dev/null 2>&1 &"'
                subprocess.Popen(["osascript", "-e", script])
                os._exit(0)
            else:
                subprocess.Popen([python, os.path.join(self.base_dir, "app.py")], cwd=self.base_dir)
                os._exit(0)
        except Exception as e:
            print(f"[Updater] Restart error: {e}")
            os._exit(0)
