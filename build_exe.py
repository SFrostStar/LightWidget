import sys
import os
import shutil
import subprocess
import PyInstaller.__main__


def _codesign_app_bundle(app_path):
    """Sign all components of a macOS .app bundle step-by-step.
    
    The '--deep' flag fails on PyInstaller bundles because of non-standard
    sub-directories (python3.11, __dot__ renames, etc.). Instead we sign
    every binary individually, from the innermost components outward.
    """
    sign_cmd = ["codesign", "--force", "--sign", "-"]

    # 1. Sign all individual .so and .dylib files
    for root, _dirs, files in os.walk(app_path):
        for fname in files:
            fpath = os.path.join(root, fname)
            if fname.endswith((".so", ".dylib")):
                subprocess.run(sign_cmd + [fpath], check=False)

    # 2. Sign embedded .app bundles (e.g. LightWidgetNotifier*.app)
    for root, dirs, _files in os.walk(app_path):
        for dname in dirs:
            if dname.endswith(".app") or "__dot__app" in dname:
                sub_app = os.path.join(root, dname)
                subprocess.run(sign_cmd + [sub_app], check=False)

    # 3. Sign embedded .framework bundles
    for root, dirs, _files in os.walk(app_path):
        for dname in dirs:
            if dname.endswith(".framework"):
                fw_path = os.path.join(root, dname)
                subprocess.run(sign_cmd + [fw_path], check=False)

    # 4. Sign the main executable
    main_exe = os.path.join(app_path, "Contents", "MacOS", "LightWidget")
    if os.path.exists(main_exe):
        subprocess.run(sign_cmd + [main_exe], check=False)

    # 5. Sign the top-level .app bundle
    subprocess.run(sign_cmd + [app_path], check=False)

    # Verify
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


