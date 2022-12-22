import io
import os
import platform
import shutil
import stat
import subprocess
import zipfile
import anchorpoint as ap
import requests

ctx = ap.Context.instance()
ui = ap.UI()

show_menu = None
show_menu_args = []
show_menu_kwargs = {}

rclone_folder_path = "~/Documents/Anchorpoint/actions/rclone"
rclone_folder_path_mac = "~/library/application support/anchorpoint software/anchorpoint/actions/rclone"
macFUSE_folder_path = "/Library/Frameworks/macFUSE.framework"

RCLONE_INSTALL_URL_WIN = "https://github.com/rclone/rclone/releases/download/v1.59.0/rclone-v1.59.0-windows-amd64.zip"
RCLONE_INSTALL_URL_MAC = "https://github.com/rclone/rclone/releases/download/v1.59.0/rclone-v1.59.0-osx-arm64.zip"
RCLONE_INSTALL_URL_MAC_X86 = "https://github.com/rclone/rclone/releases/download/v1.59.0/rclone-v1.59.0-osx-amd64.zip"
MACFUSE_INSTALL_URL = "https://github.com/osxfuse/osxfuse/releases/download/macfuse-4.4.0/macfuse-4.4.0.dmg"

def _get_zip_executable(url: str):
    base = os.path.splitext(os.path.basename(url))[0]
    if isWin():
        return os.path.join(base, "rclone.exe")
    else:
        return os.path.join(base, "rclone")

def _get_rclone_folder():
    dir = os.path.expanduser(rclone_folder_path)
    return os.path.normpath(dir)

def _get_rclone_path():
    dir = os.path.expanduser(rclone_folder_path)
    if isWin():
        dir = os.path.join(dir, "rclone.exe")
    else:
        dir = os.path.join(dir, "rclone")
    return os.path.normpath(dir)

def check_winfsp_and_rclone(menu, *args, **kwargs):
    global show_menu
    global show_menu_args
    global show_menu_kwargs

    show_menu = menu
    show_menu_args = args
    show_menu_kwargs = kwargs
    macFuse = False
    
    if isWin():
        winfsp_path = os.path.isfile(os.path.join(os.environ["ProgramFiles(x86)"],"WinFsp/bin/launcher-x64.exe"))
    else:
        macFuse = True if os.path.isdir(macFUSE_folder_path) else False
        
    rclone_path = os.path.isfile(_get_rclone_path())

    if (isWin() and not winfsp_path) or not rclone_path or (not macFuse and not isWin()):
        show_install_dialog()
    else:
        ctx.run_async(check_and_install_modules)
        show_menu(*show_menu_args, **show_menu_kwargs)

def show_install_dialog():
    dialog = ap.Dialog()
    dialog.title = "Install network drive tools"
    dialog.icon = ctx.icon

    if isWin():
        dialog.add_text("The Anchorpoint network drive is based on Rclone and WinFSP.")
        dialog.add_info("When installing them you are accepting the license of <a href=\"https://raw.githubusercontent.com/rclone/rclone/master/COPYING\">Rclone</a> and <a href=\"https://github.com/winfsp/winfsp/blob/master/License.txt\">WinFsp</a>.")
    else:
        dialog.add_text("The Anchorpoint network drive is based on Rclone and macFUSE.<br>When clicking <b>Install</b> we will download and launch the macFUSE installer.")
        dialog.add_info("When installing you are accepting the license of <a href=\"https://raw.githubusercontent.com/rclone/rclone/master/COPYING\">Rclone</a>.")
    
    dialog.add_button("Install", callback=prepare_module_install)
    dialog.show()

def prepare_module_install(dialog):
    ctx.run_async(check_and_install_modules)
    if isWin():
        ctx.run_async(check_and_install_winfsp)
    check_rclone()
    if not isWin(): # install after rclone
        check_macfuse()
    dialog.close()

def check_and_install_winfsp():
    winfsp_path = os.path.join(os.environ["ProgramFiles(x86)"],"WinFsp/bin/launcher-x64.exe")
    if not os.path.isfile(winfsp_path):
        progress = ap.Progress("Loading WinFsp",infinite = True)
        winget = subprocess.run(
            "winget install -e --id WinFsp.WinFsp --accept-source-agreements", capture_output=True
        )
        progress.finish()
        if winget.returncode != 0:
            print(winget.stderr)
            ui.show_error("Failed to install WinFsp", description="Google WinFsp and install it manually.")

def check_rclone():
    if not os.path.isfile(_get_rclone_path()):
        ctx.run_async(_install_rclone_async)
    else:
        show_menu(*show_menu_args, **show_menu_kwargs)

def make_dirs():
    if not os.path.isdir(os.path.expanduser("~/Documents/Anchorpoint")):
        os.mkdir(os.path.expanduser("~/Documents/Anchorpoint"))
    
    if not os.path.isdir(os.path.expanduser("~/Documents/Anchorpoint/actions")):
        os.mkdir(os.path.expanduser("~/Documents/Anchorpoint/actions"))

    if not os.path.isdir(_get_rclone_folder()):
        os.mkdir(_get_rclone_folder())

def _install_rclone_async():
    if not os.path.isdir(_get_rclone_folder()):
        make_dirs()
    
    # download zip
    progress = ap.Progress("Loading Rclone", infinite = True)

    if isWin():
        request_url = RCLONE_INSTALL_URL_WIN
    else:
        machine = platform.uname().machine
        apple_silicon = machine != "x86_64"
        request_url = RCLONE_INSTALL_URL_MAC_X86 if not apple_silicon else RCLONE_INSTALL_URL_MAC

    r = requests.get(request_url)
            
    # open zip file and extract rclone.exe to the right folder
    z = zipfile.ZipFile(io.BytesIO(r.content))
    
    openFile = _get_zip_executable(request_url).replace("\\","/")
    
    with z.open(openFile) as source:
        with open(_get_rclone_path(), "wb") as target:
            shutil.copyfileobj(source, target)
    
    if isWin():
        os.chmod(os.path.expanduser("~/Documents/Anchorpoint/actions/rclone/rclone.exe"), stat.S_IRWXU)     
    else:
        os.chmod(os.path.expanduser("~/Documents/Anchorpoint/actions/rclone/rclone"), stat.S_IRWXU)

    # make rclone dir
    # app_data_roaming = os.getenv('APPDATA')
    # app_data = os.path.abspath(os.path.join(app_data_roaming, os.pardir))
    # rclone_dir = os.path.join(app_data,"Local/rclone").replace("/","\\")
    # if not os.path.isdir(rclone_dir):
    #     os.mkdir(rclone_dir)
    progress.finish()

    dialog = ap.Dialog()
    dialog.title = "Installation Successful"
    dialog.add_text("To finish the installation, please <b>restart Anchorpoint</b>.<br>Once that's done, you'll be able to mount your Cloud Drive.")
    dialog.icon = ctx.icon
    dialog.show()
        
def check_macfuse():
    if not os.path.isdir(macFUSE_folder_path):
        ctx.run_async(_install_mac_fuse_async)

def _install_mac_fuse_async():
    # download zip
    progress = ap.Progress("Loading macFUSE", infinite = True)

    request_url = MACFUSE_INSTALL_URL
    r = requests.get(request_url)

    folder_macfuse = os.path.expanduser("~/Downloads")
    path_macfuse = os.path.join(folder_macfuse, 'macfuse.dmg')

    with open(path_macfuse, 'wb') as f:
        f.write(r.content)

    try:
        subprocess.check_call(["hdiutil", "mount", "macfuse.dmg"], cwd=folder_macfuse)
        subprocess.check_call(["open", "-W", "/Volumes/macFUSE/Install macFUSE.pkg"])
    finally:
        if os.path.exists(path_macfuse):
            os.remove(path_macfuse)
        #subprocess.check_call(["hdiutil", "unmount", "/Volumes/macFUSE/"], cwd=folder_macfuse)

    progress.finish()

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
        
        show_menu(*show_menu_args, **show_menu_kwargs)

def isWin():
    if platform.system() == "Windows":
        return True
    return False
