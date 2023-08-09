import anchorpoint as ap
import apsync as aps
import vc.apgit_utility.constants as constants
import vc.apgit_utility.install_git as install_git
import os, platform

def _get_git_version():
    return install_git.run_git_command([install_git.get_git_cmd_path(), "--version"])

def _install_git(dialog: ap.Dialog):
    ap.get_context().run_async(install_git.install_git)
    dialog.close()

def _check_update_available():
    try:
        version = _get_git_version()
    except Exception as e:
        # Fix an invalid certificate causing issues on macOS git installation
        if platform.system() == "Darwin":
            version =  "git version 2.35.3"
        else:
            return   

    if platform.system() == "Windows": update_available = version != constants.GIT_VERSION_WIN
    else: update_available = version != constants.GIT_VERSION_MAC

    if update_available:
        dialog = ap.Dialog()
        dialog.title = "Git Update Available"
        dialog.add_text("A new version of Git is available.")
        dialog.add_info("When installing Git you are accepting the <a href=\"https://raw.githubusercontent.com/git-for-windows/git/main/COPYING\">license</a> of the owner.")
        dialog.add_button("Install", callback=_install_git)
        dialog.show()
        pass

# Returns True if any executable is running
def is_executable_running(names: list[str]):
    import psutil
    for p in psutil.process_iter(attrs=['name']):
        try:
            if len(p.name()) > 0 and p.name().lower() in names:
                return True 
        except:
            continue
    return False

def is_git_running():
    try:
        return is_executable_running(["git", "git.exe"])
    except Exception as e:
        return True # Expect it to be running
    
def get_locking_application(path: str):
    import psutil
    for process in psutil.process_iter():
        try:
            if process.name() in ["svchost.exe", "conhost.exe", "explorer.exe", "wsl.exe", "wslhost.exe", "runtimebroker.exe", "crashpad_handler.exe", "chrome.exe"]:
                continue
            for file in process.open_files():
                if path in file.path:
                    return process.name()
        except:
            pass
    return None

def make_file_writable(path: str):
    try:
        os.chmod(path, 0o666)
        return True
    except Exception as e:
        print(f"Could not make file writable: {e}")
        return False

def is_file_writable(path: str):
    try:
        if not os.path.exists(path):
            return True
        f=open(path, "a")
        f.close()
        return True
    except Exception as e:
        return False

def guarantee_git():
    git_installed = install_git.is_git_installed()
    if git_installed: 
        _check_update_available()
        return True

    dialog = ap.Dialog()
    dialog.title = "Install Git"
    dialog.add_text("To use Anchorpoint with Git repositories you have to install it.")
    dialog.add_info("When installing Git you are accepting the <a href=\"https://raw.githubusercontent.com/git-for-windows/git/main/COPYING\">license</a> of the owner.")
    dialog.add_button("Install", callback=_install_git)
    dialog.show()

    return False

def get_repo_path(channel_id: str, project_path: str):
    project = aps.get_project(project_path)
    if not project: return project_path
    channel = aps.get_timeline_channel(project, channel_id)
    if not channel: return project_path
    if not "gitPathId" in channel.metadata: return project_path
    try:
        folder = aps.get_folder_by_id(channel.metadata["gitPathId"], project)
    except:
        return project_path
    if not folder: return project_path
    return folder