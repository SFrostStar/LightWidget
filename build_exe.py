import sys
import os
import shutil
import subprocess
import PyInstaller.__main__

def build():
    sep = ';' if sys.platform == 'win32' else ':'
    
    params = [
        'app.py',
        '--name=LightWidget',
        '--windowed',
        '--noconfirm',
        '--clean',
        f'--add-data=ui{sep}ui',
        f'--add-data=ios{sep}ios',
        f'--add-data=version.json{sep}.',
        f'--add-data=core/notifier_bundle{sep}core/notifier_bundle',
        '--hidden-import=telethon',
        '--hidden-import=webview',
        '--hidden-import=urllib.request',
    ]
    
    if sys.platform == 'win32':
        if os.path.exists("ui/app_icon.ico"):
            params.append('--icon=ui/app_icon.ico')
        params.extend([
            '--onefile',
            '--hidden-import=webview.platforms.winforms',
            '--hidden-import=webview.platforms.edgechromium',
            '--hidden-import=clr',
            '--hidden-import=pythonnet',
        ])
    else:
        if os.path.exists("ui/AppIcon.icns"):
            params.append('--icon=ui/AppIcon.icns')
        params.extend([
            '--hidden-import=objc',
            '--hidden-import=Cocoa',
            '--hidden-import=Quartz',
        ])
    
    PyInstaller.__main__.run(params)

    if sys.platform == 'darwin':
        app_path = os.path.join("dist", "LightWidget.app")
        if os.path.exists(app_path):
            # ── Step 1: Sign nested bundles/binaries FIRST (inside-out) ──
            # Find and sign every nested .app, .framework, .dylib, executable
            for root, dirs, files in os.walk(app_path):
                for d in dirs:
                    nested = os.path.join(root, d)
                    if d.endswith('.app') or d.endswith('.framework'):
                        print(f"[codesign] Signing nested: {nested}")
                        subprocess.run([
                            "codesign", "--force", "--sign", "-",
                            "--timestamp=none", nested
                        ], check=False)
                for f in files:
                    fp = os.path.join(root, f)
                    if f.endswith('.dylib') or f.endswith('.so'):
                        subprocess.run([
                            "codesign", "--force", "--sign", "-",
                            "--timestamp=none", fp
                        ], check=False)

            # ── Step 2: Sign the root .app bundle ──
            print(f"[codesign] Signing root app: {app_path}")
            subprocess.run([
                "codesign", "--force", "--deep", "--sign", "-",
                "--timestamp=none", app_path
            ], check=False)

            # ── Step 3: Strip ALL extended attributes (quarantine, etc.) ──
            print("[xattr] Stripping extended attributes...")
            subprocess.run(["xattr", "-cr", app_path], check=False)

            # ── Step 4: Prepare DMG staging directory ──
            staging_dir = "dist_dmg"
            if os.path.exists(staging_dir):
                shutil.rmtree(staging_dir)
            os.makedirs(staging_dir, exist_ok=True)
            
            shutil.copytree(app_path, os.path.join(staging_dir, "LightWidget.app"))
            # Strip xattr from the copy too
            subprocess.run(["xattr", "-cr", os.path.join(staging_dir, "LightWidget.app")], check=False)
            
            if os.path.exists("ui/AppIcon.icns"):
                shutil.copyfile("ui/AppIcon.icns", os.path.join(staging_dir, ".VolumeIcon.icns"))
            try:
                os.symlink("/Applications", os.path.join(staging_dir, "Applications"))
            except Exception:
                pass

            # ── Step 5: Create installer script inside DMG ──
            installer_script = os.path.join(staging_dir, "Установить LightWidget.command")
            with open(installer_script, "w", encoding="utf-8") as f:
                f.write('''#!/bin/bash
# ── LightWidget Installer ──
# Этот скрипт устанавливает LightWidget и снимает блокировку macOS

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_NAME="LightWidget.app"
SOURCE="$SCRIPT_DIR/$APP_NAME"
DEST="/Applications/$APP_NAME"

echo ""
echo "══════════════════════════════════════════════"
echo "   🔆 LightWidget — Установка"
echo "══════════════════════════════════════════════"
echo ""

if [ ! -d "$SOURCE" ]; then
    echo "❌ Ошибка: $APP_NAME не найден рядом со скриптом"
    echo "   Убедитесь, что скрипт запущен из образа DMG"
    echo ""
    read -p "Нажмите Enter для выхода..."
    exit 1
fi

# Remove quarantine from source
xattr -cr "$SOURCE" 2>/dev/null

# Copy to Applications
echo "📦 Копирую $APP_NAME в /Applications..."
if [ -d "$DEST" ]; then
    echo "   ⚠️  Старая версия найдена, удаляю..."
    rm -rf "$DEST"
fi

cp -R "$SOURCE" "$DEST"

# Remove quarantine from installed copy
echo "🔓 Снимаю блокировку macOS Gatekeeper..."
xattr -cr "$DEST" 2>/dev/null
# Re-sign the installed copy
codesign --force --deep --sign - "$DEST" 2>/dev/null

echo ""
echo "✅ LightWidget успешно установлен!"
echo ""

# Launch the app
echo "🚀 Запускаю LightWidget..."
open -n "$DEST"

echo ""
echo "Можете закрыть это окно."
echo ""
exit 0
''')
            os.chmod(installer_script, 0o755)

            # ── Step 6: Build DMG ──
            dmg_path = os.path.join("dist", "LightWidget-macOS.dmg")
            if os.path.exists(dmg_path):
                os.remove(dmg_path)

            subprocess.run([
                "hdiutil", "create",
                "-volname", "LightWidget",
                "-srcfolder", staging_dir,
                "-ov",
                "-format", "UDZO",
                dmg_path
            ], check=False)
            
            if os.path.exists(staging_dir):
                shutil.rmtree(staging_dir)

if __name__ == '__main__':
    build()
