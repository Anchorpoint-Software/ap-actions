from asyncio import constants
import io
import os
import shutil
import subprocess
import zipfile
import anchorpoint as ap
import requests

ctx = ap.Context.instance()
ui = ap.UI()
show_menu = None

RCLONE_INSTALL_URL = "https://github.com/rclone/rclone/releases/download/v1.58.1/rclone-v1.58.1-windows-386.zip"

def check_winfsp_and_rclone(menu):
    global show_menu
    show_menu = menu

    winfsp_path = os.path.isfile(os.path.join(os.environ["ProgramFiles(x86)"],"WinFsp/bin/launcher-x64.exe"))
    rclone_path = os.path.isfile(ctx.inputs["rclone_win"])

    if not winfsp_path or not rclone_path:
        show_install_dialog()
    else:
        ctx.run_async(check_and_install_modules)
        show_menu()

def show_install_dialog():
    dialog = ap.Dialog()
    dialog.title = "Install network drive tools"
    dialog.icon = ctx.icon
    dialog.add_text("The Anchorpoint network drive is based on Rclone and WinFSP.")
    dialog.add_info("When installing them you are accepting the license of <a href=\"https://raw.githubusercontent.com/rclone/rclone/master/COPYING\">Rclone</a> and <a href=\"https://github.com/winfsp/winfsp/blob/master/License.txt\">WinFsp</a>.")
    dialog.add_button("Install", callback=prepare_module_install)
    dialog.show()

def prepare_module_install(dialog):
    ctx.run_async(check_and_install_modules)
    ctx.run_async(check_and_install_winfsp)
    dialog.close()

def check_and_install_winfsp():
    winfsp_path = os.path.join(os.environ["ProgramFiles(x86)"],"WinFsp/bin/launcher-x64.exe")
    if os.path.isfile(winfsp_path):
        check_rclone()
    else:
        progress = ap.Progress("Loading WinFsp",infinite = True)
        winget = subprocess.run(
            "winget install -e --id WinFsp.WinFsp --accept-source-agreements", capture_output=True
        )
        progress.finish()
        if winget.returncode != 0:
            print(winget.stderr)
            ui.show_error("Failed to install WinFsp", description="Google WinFsp and install it manually.")
        else:
            check_rclone()


def check_rclone():
    if not os.path.isfile(ctx.inputs["rclone_win"]):
        ctx.run_async(_install_rclone_async)
    else:
        show_menu()

def _install_rclone_async():
    # download zip
    progress = ap.Progress("Loading Rclone", infinite = True)
    r = requests.get(RCLONE_INSTALL_URL)
            
    # open zip file and extract rclone.exe to the right folder
    z = zipfile.ZipFile(io.BytesIO(r.content))
    
    with z.open('rclone-v1.58.1-windows-386/rclone.exe') as source:
        with open(ctx.inputs["rclone_win"], "wb") as target:
            shutil.copyfileobj(source, target)
            
    # make rclone dir
    app_data_roaming = os.getenv('APPDATA')
    app_data = os.path.abspath(os.path.join(app_data_roaming, os.pardir))
    rclone_dir = os.path.join(app_data,"Local/rclone").replace("/","\\")
    
    if not os.path.isdir(rclone_dir):
        os.mkdir(rclone_dir)
        
    progress.finish()
    
    show_menu()
        
def check_and_install_modules():
    try:
        import pyperclip as pc
        from Crypto.Cipher import AES
    except:
        progress = ap.Progress("Loading Modules",infinite = True)
        ui.show_info("Loading Modules", description="This will only happen once")  
        ctx.install("pycryptodome")
        ctx.install("pyperclip")
        progress.finish()
