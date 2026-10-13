import base64
import hashlib
import io
import json
import os
import subprocess
import sys
import tempfile
import threading
import urllib.request
import zipfile
from pathlib import Path

from core.crypto import DATA_DIR


class WallpaperManager:
    def __init__(self, resources):
        self.resources = Path(resources) / "wallpapers"
        self.cache = Path(DATA_DIR) / "wallpapers"
        self.records = json.loads((self.resources / "catalog.json").read_text(encoding="utf-8"))
        self.by_id = {record["id"]: record for record in self.records}
        self.lock = threading.Lock()
        self.installed = {}
        if sys.platform == "darwin":
            self._find_installed()

    def _find_installed(self):
        root = Path("/System/Library/AssetsV2/com_apple_MobileAsset_DesktopPicture")
        images = list(root.glob("*.asset/AssetData/**/*.heic"))
        roots = [Path.home() / "Library/Application Support/com.apple.wallpaper/aerials/videos",
                 Path("/Library/Application Support/com.apple.idleassetsd/Customer")]
        videos = {p.name: p for root in roots for p in root.glob("**/*.mov") if p.is_file()}
        for record in self.records:
            if record.get("local") and Path(record["local"]).is_file():
                self.installed[record["id"]] = Path(record["local"])
            elif record.get("asset_id"):
                source = next((p for p in images if p.stem == record["asset_id"]), None)
                if source:
                    self.installed[record["id"]] = source
            elif record.get("aerial_id"):
                name = record["aerial_id"] + ".mov"
                source = videos.get(name)
                if source:
                    self.installed[record["id"]] = source

    def _cached(self, identifier):
        return self.cache / (identifier + "-4k.jpg")

    def _source(self, record):
        cached = self._cached(record["id"])
        if cached.is_file():
            return cached
        builtin = self.resources / record["builtin"] if record.get("builtin") else None
        return self.installed.get(record["id"]) or (builtin if builtin and builtin.is_file() else None)

    def catalog(self):
        items = [{key: record[key] for key in ("id", "name", "category", "preview")} |
                 {"installed": bool(self._source(record)), "bytes": record.get("bytes", 0)}
                 for record in self.records]
        return sorted(items, key=lambda item: (item["category"], item["name"].casefold()))

    def _download(self, record):
        if sys.platform == "darwin":
            with tempfile.TemporaryDirectory() as folder:
                downloaded = Path(folder) / "download"
                subprocess.run([
                    "/usr/bin/curl", "--fail", "--location", "--silent", "--show-error",
                    "--proto", "=https", "--proto-redir", "=https", "--connect-timeout", "15",
                    "--max-time", "60", "--max-filesize", str(256 * 1024 * 1024),
                    "--user-agent", "LightWidget", "--output", str(downloaded), record["url"]
                ], check=True, capture_output=True, timeout=65)
                if downloaded.stat().st_size > 256 * 1024 * 1024:
                    raise ValueError("Файл обоев слишком большой")
                content = downloaded.read_bytes()
        else:
            request = urllib.request.Request(record["url"], headers={"User-Agent": "LightWidget"})
            content = bytearray()
            with urllib.request.urlopen(request, timeout=30) as response:
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    content.extend(chunk)
                    if len(content) > 256 * 1024 * 1024:
                        raise ValueError("Файл обоев слишком большой")
        if record.get("kind") == "zip":
            if record.get("sha1") and hashlib.sha1(content).hexdigest() != record["sha1"]:
                raise ValueError("Не удалось проверить загруженные обои")
            with zipfile.ZipFile(io.BytesIO(content)) as archive:
                images = [item for item in archive.infolist() if Path(item.filename).suffix.lower() in {".heic", ".jpg", ".jpeg", ".png"} and not item.filename.startswith("__MACOSX/")]
                if not images:
                    raise ValueError("В архиве нет изображения")
                selected = max(images, key=lambda item: item.file_size)
                if selected.file_size > 256 * 1024 * 1024:
                    raise ValueError("Файл обоев слишком большой")
                return archive.read(selected), Path(selected.filename).suffix
        return bytes(content), ".png"

    def _video_frame(self, source, target):
        remote = str(source).startswith("https://")
        if sys.platform == "darwin":
            import AVFoundation
            import Cocoa
            import CoreMedia
            import Quartz
            url = Cocoa.NSURL.URLWithString_(source) if remote else Cocoa.NSURL.fileURLWithPath_(str(source))
            asset = AVFoundation.AVURLAsset.URLAssetWithURL_options_(url, None)
            generator = AVFoundation.AVAssetImageGenerator.alloc().initWithAsset_(asset)
            generator.setAppliesPreferredTrackTransform_(True)
            generator.setMaximumSize_(Cocoa.NSMakeSize(3840, 3840))
            completed = threading.Event()
            result = {}

            def receive(frame, actual_time, error):
                try:
                    if frame is None or Quartz.CGImageGetWidth(frame) == 0:
                        raise ValueError("Не удалось получить кадр обоев")
                    bitmap = Cocoa.NSBitmapImageRep.alloc().initWithCGImage_(frame)
                    data = bitmap.representationUsingType_properties_(Cocoa.NSBitmapImageFileTypeJPEG, {Cocoa.NSImageCompressionFactor: 0.92})
                    if not data:
                        raise ValueError("Не удалось сохранить кадр обоев")
                    result["image"] = bytes(data)
                except Exception as failure:
                    result["error"] = failure
                finally:
                    completed.set()

            generator.generateCGImageAsynchronouslyForTime_completionHandler_(CoreMedia.CMTimeMake(0, 600), receive)
            if not completed.wait(60):
                generator.cancelAllCGImageGeneration()
                raise TimeoutError("Не удалось загрузить оригинал обоев за 60 секунд")
            if result.get("error"):
                raise result["error"]
            target.write_bytes(result["image"])
        else:
            import imageio_ffmpeg
            arguments = [imageio_ffmpeg.get_ffmpeg_exe(), "-hide_banner", "-loglevel", "error"]
            if remote:
                original = Path(target).parent / "original.mov"
                curl = Path(os.environ.get("SystemRoot", "C:/Windows")) / "System32/curl.exe"
                if curl.is_file():
                    subprocess.run([
                        str(curl), "--fail", "--location", "--silent", "--show-error",
                        "--proto", "=https", "--proto-redir", "=https", "--connect-timeout", "15",
                        "--max-time", "180", "--max-filesize", str(2 * 1024 * 1024 * 1024),
                        "--output", str(original), str(source)
                    ], check=True, capture_output=True, timeout=185, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
                else:
                    size = 0
                    with urllib.request.urlopen(source, timeout=30) as response, original.open("wb") as file:
                        while True:
                            chunk = response.read(1024 * 1024)
                            if not chunk:
                                break
                            size += len(chunk)
                            if size > 2 * 1024 * 1024 * 1024:
                                raise ValueError("Оригинал обоев слишком большой")
                            file.write(chunk)
                source = original
            arguments += ["-i", str(source), "-map", "0:v:0", "-frames:v", "1", "-vf", "scale=w='min(3840,iw)':h='min(3840,ih)':force_original_aspect_ratio=decrease", "-q:v", "2", "-an", "-y", str(target)]
            subprocess.run(arguments, check=True, capture_output=True, timeout=65, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))

    def _convert(self, source, target):
        if str(source).startswith("https://") or source.suffix.lower() == ".mov":
            self._video_frame(source, target)
        elif sys.platform == "darwin":
            subprocess.run(["sips", "-s", "format", "jpeg", "-s", "formatOptions", "92", "-Z", "3840", str(source), "--out", str(target)], check=True, capture_output=True, timeout=60)
        else:
            from PIL import Image, ImageOps
            if source.suffix.lower() == ".heic":
                import pillow_heif
                pillow_heif.register_heif_opener()
            with Image.open(source) as image:
                image = ImageOps.exif_transpose(image).convert("RGB")
                image.thumbnail((3840, 3840))
                image.save(target, "JPEG", quality=92)

    def image(self, identifier):
        record = self.by_id.get(str(identifier))
        if not record:
            return {"success": False, "error": "Обои не найдены"}
        try:
            with self.lock:
                source = self._source(record)
                cached = self._cached(record["id"])
                if source != cached:
                    self.cache.mkdir(parents=True, exist_ok=True)
                    with tempfile.TemporaryDirectory(dir=self.cache) as folder:
                        folder = Path(folder)
                        if not source and record.get("video_url"):
                            source = record["video_url"]
                        elif not source:
                            data, suffix = self._download(record)
                            source = folder / ("original" + suffix)
                            source.write_bytes(data)
                        result = folder / "image.jpg"
                        try:
                            self._convert(source, result)
                        except Exception:
                            if not isinstance(source, Path) or source.suffix.lower() != ".mov" or not record.get("video_url"):
                                raise
                            self._convert(record["video_url"], result)
                        if not result.is_file() or result.stat().st_size == 0:
                            raise ValueError("Не удалось подготовить изображение")
                        result.replace(cached)
                    source = cached
                if not source:
                    raise ValueError("Обои недоступны")
                encoded = base64.b64encode(source.read_bytes()).decode("ascii")
            return {"success": True, "image": "data:image/jpeg;base64," + encoded, "id": record["id"]}
        except Exception as error:
            print(f"[Wallpapers] {record['name']}: {type(error).__name__}: {error}")
            return {"success": False, "error": "Не удалось загрузить обои. Проверьте подключение и попробуйте ещё раз."}
