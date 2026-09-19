import sys
import os
import shutil
import subprocess
import PyInstaller.__main__


def _codesign_app_bundle(app_path):
    frameworks_notifier = os.path.join(app_path, "Contents", "Frameworks", "core", "notifier_bundle")
    if os.path.exists(frameworks_notifier):
        if os.path.islink(frameworks_notifier):
            os.unlink(frameworks_notifier)
        else:
            shutil.rmtree(frameworks_notifier, ignore_errors=True)

    sign_cmd = ["codesign", "--force", "--sign", "-"]

    for root, _dirs, files in os.walk(app_path):
        for fname in files:
            fpath = os.path.join(root, fname)
            if fname.endswith((".so", ".dylib")):
                subprocess.run(sign_cmd + [fpath], check=False)

    notifier_bin = os.path.join(app_path, "Contents", "Resources", "core", "notifier_bundle", "LightWidgetNotifier.app", "Contents", "MacOS", "notifier_bin")
    if os.path.exists(notifier_bin):
        subprocess.run(sign_cmd + [notifier_bin], check=False)

    for root, dirs, _files in os.walk(app_path):
        for dname in dirs:
            if dname.endswith(".app") and root != os.path.dirname(app_path):
                sub_app = os.path.join(root, dname)
                subprocess.run(sign_cmd + [sub_app], check=False)

    for root, dirs, _files in os.walk(app_path):
        for dname in dirs:
            if dname.endswith(".framework"):
                fw_path = os.path.join(root, dname)
                subprocess.run(sign_cmd + [fw_path], check=False)

    main_exe = os.path.join(app_path, "Contents", "MacOS", "LightWidget")
    if os.path.exists(main_exe):
        subprocess.run(sign_cmd + [main_exe], check=False)

    subprocess.run(sign_cmd + [app_path], check=False)

    result = subprocess.run(
        ["codesign", "--verify", "--verbose", app_path],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        print(f"[build] Code signing verified: {app_path}")
    else:
        print(f"[build] Code signing verification warning: {result.stderr.strip()}")


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
            target_notifier = os.path.join(app_path, "Contents", "Resources", "core", "notifier_bundle")
            if os.path.exists(target_notifier):
                shutil.rmtree(target_notifier, ignore_errors=True)
            if os.path.exists("core/notifier_bundle"):
                shutil.copytree("core/notifier_bundle", target_notifier, symlinks=False)

            print("[build] Signing app bundle components...")
            _codesign_app_bundle(app_path)

            staging_dir = "dist_dmg"
            if os.path.exists(staging_dir):
                shutil.rmtree(staging_dir)
            os.makedirs(staging_dir, exist_ok=True)
            
            shutil.copytree(app_path, os.path.join(staging_dir, "LightWidget.app"), symlinks=True)
            if os.path.exists("ui/AppIcon.icns"):
                shutil.copyfile("ui/AppIcon.icns", os.path.join(staging_dir, ".VolumeIcon.icns"))
            try:
                os.symlink("/Applications", os.path.join(staging_dir, "Applications"))
            except Exception:
                pass

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


