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
    running = [p for p in psutil.process_iter(attrs=['name']) if p.name().lower() in names]
    return len(running) > 0

def is_git_running():
    try:
        is_executable_running(["git"])
    except:
        return True # Expect it to be running
    
def get_locking_application(path: str):
    import psutil
    for process in psutil.process_iter():
        try:
            for file in process.open_files():
                if file.path == path:
                    return process.name()
        except:
            continue
    return None

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