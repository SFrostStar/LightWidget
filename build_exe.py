import sys
import PyInstaller.__main__

def build():
    sep = ';' if sys.platform == 'win32' else ':'
    
    params = [
        'app.py',
        '--name=LightWidget',
        '--onefile',
        '--windowed',
        '--noconfirm',
        '--clean',
        f'--add-data=ui{sep}ui',
        f'--add-data=ios{sep}ios',
        '--hidden-import=telethon',
        '--hidden-import=webview',
        '--hidden-import=webview.platforms.winforms',
        '--hidden-import=webview.platforms.edgechromium',
        '--hidden-import=clr',
        '--hidden-import=pythonnet',
        '--hidden-import=urllib.request',
    ]
    
    PyInstaller.__main__.run(params)

if __name__ == '__main__':
    build()
