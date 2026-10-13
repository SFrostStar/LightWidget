import hashlib
import json
import plistlib
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "ui" / "wallpapers"
DESKTOP = Path("/System/Library/Desktop Pictures")
EXTENSIONS = Path("/System/Library/ExtensionKit/Extensions")


def convert(source, target, size):
    target.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([
        "sips", "-s", "format", "jpeg", "-s", "formatOptions", "75",
        "-Z", str(size), str(source), "--out", str(target)
    ], check=True, capture_output=True)


def build_catalog():
    records = []
    assets_path = Path("/System/Library/AssetsV2/com_apple_MobileAsset_DesktopPicture/com_apple_MobileAsset_DesktopPicture.xml")
    assets = plistlib.loads(assets_path.read_bytes())["Assets"]
    downloads = {asset["DesktopPictureID"]: asset for asset in assets}

    def add(name, preview, local=None, download=None, category="Обои macOS", builtin=False, key=None):
        identifier = hashlib.sha256((category + ":" + (key or name)).encode()).hexdigest()[:24]
        if preview and preview.is_file():
            convert(preview, OUTPUT / "previews" / (identifier + ".jpg"), 280)
            preview_url = "wallpapers/previews/" + identifier + ".jpg"
        elif download and download.get("kind") == "image":
            preview_url = download["url"]
        else:
            return
        record = {"id": identifier, "name": name, "category": category,
                  "preview": preview_url}
        if local:
            record["local"] = str(local)
        if download:
            record.update(download)
        if builtin:
            convert(local or preview, OUTPUT / "images" / (identifier + ".jpg"), 1600)
            record["builtin"] = "images/" + identifier + ".jpg"
        records.append(record)

    for source in sorted(DESKTOP.iterdir()):
        if source.suffix == ".madesktop":
            data = plistlib.loads(source.read_bytes())
            asset = downloads.get(data.get("mobileAssetID"))
            download = None
            if asset:
                download = {"url": asset["__BaseURL"] + asset["__RelativePath"], "kind": "zip",
                            "bytes": asset["_DownloadSize"], "asset_id": data["mobileAssetID"],
                            "sha1": asset["_Measurement"].hex()}
            add(source.stem, Path(data["thumbnailPath"]), download=download)
        elif source.suffix.lower() in {".heic", ".jpg", ".png"}:
            add(source.stem, source, local=source, builtin=True)

    for extension, name, files in [
        ("NeptuneOneWallpaper", "Tahoe", ["TahoeLight.heic", "TahoeDark.heic"]),
        ("WallpaperSequoiaExtension", "Sequoia", ["thumbnail light.heic", "thumbnail dark.heic"])
    ]:
        for index, filename in enumerate(files):
            source = EXTENSIONS / (extension + ".appex") / "Contents/Resources" / filename
            add(name + (" Light" if index == 0 else " Dark"), source, local=source, builtin=True)

    for source in sorted((DESKTOP / "Solid Colors").glob("*.png")):
        add(source.stem, source, local=source, builtin=True, category="Цвета")

    resources = EXTENSIONS / "WallpaperAerialsExtension.appex/Contents/Resources"
    strings_path = resources / "TVIdleScreenStrings.bundle/Contents/Resources/Localizable.nocache.loctable"
    strings = plistlib.loads(strings_path.read_bytes()).get("ru", {})
    user_aerials = Path.home() / "Library/Application Support/com.apple.wallpaper/aerials"
    manifest = user_aerials / "manifest/entries.json"
    catalog = json.loads((manifest if manifest.exists() else resources / "entries.json").read_text())
    for asset in catalog["assets"]:
        preview = resources / (asset["id"] + ".png")
        if not preview.is_file():
            preview = user_aerials / "thumbnails" / (asset["id"] + ".png")
        name = strings.get(asset.get("localizedNameKey")) or asset.get("accessibilityLabel") or asset.get("localizedNameKey", asset["id"])
        variant = asset.get("variant", {})
        if variant:
            name += " · " + {"light": "Светлые", "dark": "Тёмные"}.get(variant.get("appearance"), "")
            if variant.get("orientation") == "portrait":
                name += " · Вертикальные"
        add(name, preview,
            download={"url": asset["previewImage"], "kind": "image", "aerial_id": asset["id"], "video_url": asset["url-4K-SDR-240FPS"]},
            category="Пейзажи", key=asset["id"])
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "catalog.json").write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n")
    keep = {record["id"] + ".jpg" for record in records}
    for folder in [OUTPUT / "previews", OUTPUT / "images"]:
        for image in folder.glob("*.jpg"):
            if image.name not in keep:
                image.unlink()
    print(f"Обои: {len(records)}; размер каталога: {sum(p.stat().st_size for p in OUTPUT.rglob('*') if p.is_file()) / 1048576:.1f} МБ")


if __name__ == "__main__":
    build_catalog()
