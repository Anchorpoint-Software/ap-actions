from subprocess import call
import anchorpoint as ap
import apsync as aps
import sys, os

ctx = ap.Context.instance()

git_install_url = "https://github.com/git-for-windows/git/releases/download/v2.36.0.windows.1/Git-2.36.0-64-bit.exe"

def download_git():
    import requests
    progress = ap.Progress("Downloading Git", infinite=True)
    r = requests.get(git_install_url, allow_redirects=True)
    progress.finish()
    return r
    
def install_git_async():
    import tempfile, subprocess
    request = download_git()
    progress = ap.Progress("Installing Git", infinite=True)
    
    with tempfile.TemporaryDirectory() as tempdir:
        with open(os.path.join(tempdir, "git.exe"), "wb") as f:
            f.write(request.content)
    
        try:
            subprocess.check_call([f.name, "/SILENT", "/COMPONENTS=gitlfs"])
            subprocess.check_call(["git", "credential-manager-core", "configure"])
            ap.UI().show_success("Git installed successfully")
        except:
            ap.UI().show_info("User cancelled Git installation")

    progress.finish()

def install_git(dialog: ap.Dialog):
    ctx.run_async(install_git_async)
    dialog.close()

def guarantee_git():
    import shutil
    git_path = shutil.which("git")
    if git_path:
        print(git_path)
        return True

    print("Git must be installed")

    dialog = ap.Dialog()
    dialog.title = "Install Git for Windows"
    dialog.add_text("To use Anchorpoint with Git repositories you have to install Git for Windows.")
    dialog.add_info("When installing Git for Windows you are accepting the <a href=\"https://raw.githubusercontent.com/git-for-windows/git/main/COPYING\">license</a> of the owner.")
    dialog.add_button("Install", callback=install_git)
    dialog.show()

    return False

if not guarantee_git():
    sys.exit(0)

try:
    import git
except:
    ctx.install("GitPython")
    import git



ui = ap.UI()

ui.show_success("Hello Anchorpoint")