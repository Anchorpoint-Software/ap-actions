import anchorpoint as ap
import apsync as aps
import vc.apgit.constants as constants
import os, platform, subprocess

def _download_git():
    import requests
    progress = ap.Progress("Downloading Git", infinite=True)
    r = requests.get(constants.INSTALL_URL_WIN, allow_redirects=True)
    progress.finish()
    return r
    
def _configure_gcm():
    subprocess.check_call(["git", "credential-manager-core", "configure"], creationflags=subprocess.CREATE_NO_WINDOW)

def _install_git_async():
    import tempfile
    request = _download_git()
    progress = ap.Progress("Installing Git", infinite=True)
    
    with tempfile.TemporaryDirectory() as tempdir:
        with open(os.path.join(tempdir, "git.exe"), "wb") as f:
            f.write(request.content)
    
        try:
            subprocess.check_call([f.name, "/SILENT", "/COMPONENTS=gitlfs"])
            _configure_gcm()
            ap.UI().show_success("Git installed successfully")
        except:
            ap.UI().show_info("User cancelled Git installation")

    progress.finish()

def _install_git(dialog: ap.Dialog):
    ap.Context.instance().run_async(_install_git_async)
    dialog.close()

def _check_application(name: str):
    import shutil
    app = shutil.which(name)
    if app:
        print("found: ", app)
        return True
    return False

def _check_gcm():
    if platform.system() == "Darwin":
        return _check_application("git-credential-manager-core")
    else:
        try:
            _configure_gcm()
            return True
        except:
            return False

def guarantee_git():
    git_installed = _check_application("git")
    lfs_installed = _check_application("git-lfs")
    gcm_installed = _check_gcm()

    ui = ap.UI()
    if not lfs_installed:
        ui.show_info("Git LFS not installed", "Git LFS is required for Git to work correctly.")
    elif not gcm_installed:
        ui.show_info("Git Credential Manager not installed", "The Git Credential Manager is required for Git to work correctly.") 

    if git_installed and lfs_installed and gcm_installed:
        _configure_gcm()
        return True

    print("Git must be installed")

    if platform.system() == "Windows":
        dialog = ap.Dialog()
        dialog.title = "Install Git for Windows"
        dialog.add_text("To use Anchorpoint with Git repositories you have to install Git for Windows.")
        dialog.add_info("When installing Git for Windows you are accepting the <a href=\"https://raw.githubusercontent.com/git-for-windows/git/main/COPYING\">license</a> of the owner.")
        dialog.add_button("Install", callback=_install_git)
        dialog.show()
    elif platform.system() == "Darwin":
        dialog = ap.Dialog()
        dialog.title = "Git Installation Not Found"
        dialog.add_text("To use Anchorpoint with Git repositories you have to install <a href=\"https://git-scm.com/download/mac\">Git</a>, <a href=\"https://git-lfs.github.com\">Git LFS</a>, and <a href=\"https://github.com/GitCredentialManager/git-credential-manager\">GCM</a> for Mac.")
        dialog.add_button("OK", callback=lambda dialog: dialog.close())
        dialog.show()

    return False

def get_repo_path(channel_id: str, project_path: str):
    project = aps.get_project(project_path)
    if not project: return None
    channel = aps.get_timeline_channel(project, channel_id)
    if not channel: return None
    if not "gitPathId" in channel.metadata: return None
    return aps.get_folder_by_id(channel.metadata["gitPathId"], project)