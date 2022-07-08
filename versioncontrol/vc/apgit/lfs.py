from git import RemoteProgress
from vc.apgit.utility import get_git_cmd_path
import subprocess, platform

def _run_lfs_command(path: str, args, progress: RemoteProgress, env):
    kwargs = {}
    if platform == "Windows":
        from subprocess import CREATE_NO_WINDOW
        kwargs["creationflags"] = CREATE_NO_WINDOW
    
    process = subprocess.Popen(
        args, 
        env=env, 
        stdout=subprocess.PIPE, 
        stderr=subprocess.PIPE, 
        universal_newlines=True,
        bufsize=1, 
        cwd=path,
        **kwargs)

    for line in process.stdout:
        if line is None:
            break

        if progress:
            progress.line_dropped(line)
            
            if progress.canceled():
                process.terminate()
                process.wait()
                return

    process.wait()
    if process.returncode != 0:
        raise RuntimeError(process.stderr)

def lfs_fetch(path: str, remote: str, progress: RemoteProgress, env):
    args = [get_git_cmd_path(), "lfs", "fetch", remote, "@{u}"]
    _run_lfs_command(path, args, progress, env)

def lfs_push(path: str, remote: str, branch: str, progress: RemoteProgress, env):
    args = [get_git_cmd_path(), "lfs", "push", remote, branch]
    _run_lfs_command(path, args, progress, env)