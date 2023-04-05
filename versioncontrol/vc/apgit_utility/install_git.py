import os, platform
import io, shutil
import vc.apgit_utility.constants as constants
import anchorpoint as ap

def _check_application(path: str):
    return os.path.exists(path)

def get_git_cmddir():
    # Code duplicated in git_project.py to avoid installation dialog
    dir = os.path.expanduser("~/Documents/Anchorpoint/actions")
    dir = os.path.join(dir, "git-cmd")
    return os.path.normpath(dir)

def is_git_installed():
    dir = get_git_cmddir()
    if not _check_application(get_git_cmd_path()): return False
    if not _check_application(get_gcm_path()): return False
    if not _check_application(get_lfs_path()): return False
    return True

def get_lfs_path():
    if platform.system() == "Windows":
        return os.path.join(get_git_cmddir(),"mingw64","libexec","git-core","git-lfs.exe")
    elif platform.system() == "Darwin":
        return os.path.join(get_git_cmddir(),"libexec","git-core","git-lfs")
    else:
        raise RuntimeError("Unsupported Platform")

def get_gcm_path():
    if platform.system() == "Windows":
        return os.path.join(get_git_cmddir(),"mingw64","libexec","git-core","git-credential-manager-core.exe")
    elif platform.system() == "Darwin":
        return os.path.join(get_git_cmddir(),"libexec","git-core","git-credential-manager-core")
    else:
        raise RuntimeError("Unsupported Platform")

def get_git_cmd_path():
    if platform.system() == "Windows":
        return os.path.join(get_git_cmddir(),"cmd","git.exe")
    elif platform.system() == "Darwin":
        return os.path.join(get_git_cmddir(),"bin","git")
    else:
        raise RuntimeError("Unsupported Platform")

def get_git_exec_path():
    if platform.system() == "Windows":
        return os.path.join(get_git_cmddir(),"mingw64","libexec","git-core")
    elif platform.system() == "Darwin":
        return os.path.join(get_git_cmddir(),"libexec","git-core")
    else:
        raise RuntimeError("Unsupported Platform")

def run_git_command(args, cwd = None, **kwargs):
    from vc.apgit.repository import GitRepository
    import subprocess, platform
    current_env = os.environ.copy()
    current_env.update(GitRepository.get_git_environment())

    if platform.system() == "Windows":
        from subprocess import CREATE_NO_WINDOW
        kwargs["creationflags"] = CREATE_NO_WINDOW

    try:
        p = subprocess.run(args, env=current_env, cwd=cwd, capture_output=True, **kwargs)
        out = p.stdout.decode("utf-8").strip()
        err = p.stderr.decode("utf-8").strip()
        if p.returncode != 0:
            raise Exception(f"Failed to run git command ({args}): \nerr: {err}")
        
        return out
    except Exception as e:
        print("Failed to run git command: " + str(args))
        raise e

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

def install_git():
    r = _download_git()
    progress = ap.Progress("Installing Git", infinite=True, show_loading_screen=True)

    dir = get_git_cmddir()
    if os.path.exists(dir):
        shutil.rmtree(dir)

    if platform.system() == "Darwin":
        # Don't use zipfile on mac as it messes up permissions and alias files
        import subprocess, tempfile
        with tempfile.TemporaryDirectory() as tempdir:
            with open(os.path.join(tempdir, "mac.zip"), "wb") as f:
                f.write(r.content)
            subprocess.check_call(["unzip", f.name, "-d", dir], stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    else:
        from zipfile import ZipFile
        z = ZipFile(io.BytesIO(r.content))
        z.extractall(path=dir)

    _install_git_lfs()
    _setup_git()

    ap.UI().show_success("Git installed successfully")
    progress.finish()

def _download_git():
    import requests
    progress = ap.Progress("Downloading Git", infinite=True, show_loading_screen=True)
    if platform.system() == "Windows":
        r = requests.get(constants.INSTALL_URL_WIN, allow_redirects=True)
    elif platform.system() == "Darwin":
        r = requests.get(constants.INSTALL_URL_MAC, allow_redirects=True)
    else:
        raise RuntimeError("Unsupported Platform")
    progress.finish()
    return r

def _install_git_lfs():
    run_git_command([get_git_cmd_path(), "lfs", "install"])

def _setup_git():
    try:
        email = run_git_command([get_git_cmd_path(), "config", "--global", "user.email"])
    except:
        email = None
    try:
        name = run_git_command([get_git_cmd_path(), "config", "--global", "user.name"])
    except:
        name = None

    ctx = ap.get_context()
    if not email or email == "":
        run_git_command([get_git_cmd_path(), "config", "--global", "user.email", ctx.email])
    if not name or name == "":
        run_git_command([get_git_cmd_path(), "config", "--global", "user.name", ctx.username])
