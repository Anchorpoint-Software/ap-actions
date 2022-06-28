import anchorpoint as ap
import apsync as aps
import vc.apgit.constants as constants
import os, platform
import io, shutil

from vc.apgit.zip_helper import ZipFileWithPermissions

def _download_git():
    import requests
    progress = ap.Progress("Downloading Git", infinite=True)
    if platform.system() == "Windows":
        r = requests.get(constants.INSTALL_URL_WIN, allow_redirects=True)
    elif platform.system() == "Darwin":
        r = requests.get(constants.INSTALL_URL_MAC, allow_redirects=True)
    else:
        raise RuntimeError("Unsupported Platform")
    progress.finish()
    return r

def _install_git_async():
    r = _download_git()
    progress = ap.Progress("Installing Git", infinite=True)

    z = ZipFileWithPermissions(io.BytesIO(r.content))
    dir = _get_git_cmddir()
    if os.path.exists(dir):
        shutil.rmtree(dir)
    z.extractall(path=dir)

    ap.UI().show_success("Git installed successfully")
    progress.finish()

def _install_git(dialog: ap.Dialog):
    ap.Context.instance().run_async(_install_git_async)
    dialog.close()

def _check_application(path: str):
    return os.path.exists(path)

def _get_git_cmddir():
    dir = os.path.dirname(__file__)
    dir = os.path.join(dir, "git-cmd")
    return dir

def _check_installation():
    dir = _get_git_cmddir()
    if not _check_application(get_git_cmd_path()): return False
    if not _check_application(get_gcm_path()): return False
    if not _check_application(get_lfs_path()): return False
    return True

def get_lfs_path():
    if platform.system() == "Windows":
        return os.path.join(_get_git_cmddir(),"mingw64","libexec","git-core","git-lfs.exe")
    elif platform.system() == "Darwin":
        return os.path.join(_get_git_cmddir(),"libexec","git-core","git-lfs")
    else:
        raise RuntimeError("Unsupported Platform")

def get_gcm_path():
    if platform.system() == "Windows":
        return os.path.join(_get_git_cmddir(),"mingw64","libexec","git-core","git-credential-manager-core.exe")
    elif platform.system() == "Darwin":
        return os.path.join(_get_git_cmddir(),"libexec","git-core","git-credential-manager-core")
    else:
        raise RuntimeError("Unsupported Platform")

def get_git_cmd_path():
    if platform.system() == "Windows":
        return os.path.join(_get_git_cmddir(),"cmd","git.exe")
    elif platform.system() == "Darwin":
        return os.path.join(_get_git_cmddir(),"bin","git")
    else:
        raise RuntimeError("Unsupported Platform")

def get_git_exec_path():
    if platform.system() == "Windows":
        return os.path.join(_get_git_cmddir(),"mingw64","libexec","git-core")
    elif platform.system() == "Darwin":
        return os.path.join(_get_git_cmddir(),"libexec","git-core")
    else:
        raise RuntimeError("Unsupported Platform")

def guarantee_git():
    git_installed = _check_installation()
    if git_installed: return True

    print("Git must be installed")

    dialog = ap.Dialog()
    dialog.title = "Install Git"
    dialog.add_text("To use Anchorpoint with Git repositories you have to install it.")
    dialog.add_info("When installing Git you are accepting the <a href=\"https://raw.githubusercontent.com/git-for-windows/git/main/COPYING\">license</a> of the owner.")
    dialog.add_button("Install", callback=_install_git)
    dialog.show()

    return False

def get_repo_path(channel_id: str, project_path: str):
    project = aps.get_project(project_path)
    if not project: return None
    channel = aps.get_timeline_channel(project, channel_id)
    if not channel: return None
    if not "gitPathId" in channel.metadata: return None
    return aps.get_folder_by_id(channel.metadata["gitPathId"], project)