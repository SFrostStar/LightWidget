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
            try:
                subprocess.run(["codesign", "--force", "--deep", "--sign", "-", app_path], check=False)
            except Exception:
                pass

            staging_dir = "dist_dmg"
            if os.path.exists(staging_dir):
                shutil.rmtree(staging_dir)
            os.makedirs(staging_dir, exist_ok=True)
            
            shutil.copytree(app_path, os.path.join(staging_dir, "LightWidget.app"))
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

