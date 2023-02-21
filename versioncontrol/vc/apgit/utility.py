import anchorpoint as ap
import apsync as aps
import vc.apgit_utility.constants as constants
import vc.apgit_utility.install_git as install_git
import os, platform

def run_git_command(args, cwd = None, **kwargs):
    from vc.apgit.repository import GitRepository
    import subprocess, platform
    current_env = os.environ.copy()
    current_env.update(GitRepository.get_git_environment())

    if platform.system() == "Windows":
        from subprocess import CREATE_NO_WINDOW
        kwargs["creationflags"] = CREATE_NO_WINDOW

    return subprocess.check_output(args, env=current_env, cwd=cwd, **kwargs).decode("utf-8").strip() 

def run_git_command_with_progress(args: list, callback, cwd = None, **kwargs):
    from vc.apgit.repository import GitRepository
    import subprocess, platform
    current_env = os.environ.copy()
    current_env.update(GitRepository.get_git_environment())
    args.append("--verbose")

    if platform.system() == "Windows":
        from subprocess import CREATE_NO_WINDOW
        kwargs["creationflags"] = CREATE_NO_WINDOW

    p = subprocess.Popen(args, env=current_env, cwd=cwd, stdout=subprocess.PIPE, **kwargs)
    line_counter = 0
    while True:
        line = p.stdout.readline()
        if not line:
            break
        line_counter = line_counter + 1
        callback(line_counter, line.decode("utf-8").strip())

    return 0 if p.returncode == None else p.returncode

def _get_git_version():
    return run_git_command([install_git.get_git_cmd_path(), "--version"])

def _install_git(dialog: ap.Dialog):
    ap.Context.instance().run_async(install_git.install_git)
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