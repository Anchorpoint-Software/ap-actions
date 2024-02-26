from git import RemoteProgress
from vc.apgit_utility.install_git import get_git_cmd_path
import subprocess
import platform


def _run_lfs_command(path: str, args, progress: RemoteProgress, env):
    if progress and progress.canceled():
        return

    kwargs = {}
    if platform.system() == "Windows":
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
        **kwargs,
    )

    for line in process.stdout:
        if line is None:
            break

        if progress:
            progress.line_dropped(line)

            if progress.canceled():
                if platform.system() == "Windows":
                    from subprocess import CREATE_NO_WINDOW

                    subprocess.call(
                        ["taskkill", "/F", "/T", "/PID", str(process.pid)],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        creationflags=CREATE_NO_WINDOW,
                    )
                else:
                    process.terminate()

                process.wait()
                return

    process.wait()
    if process.returncode != 0:
        raise RuntimeError("Git LFS error: " + str(process.stderr.read()))


def lfs_fetch(
    path: str,
    remote: str,
    progress: RemoteProgress,
    env,
    branches: list[str] = None,
    files: list[str] = None,
    exclude_files: bool = False,
):
    args = [get_git_cmd_path(), "lfs", "fetch", remote]
    if not branches:
        args.append("@{u}")
    else:
        args.extend(branches)

    if files:
        file_batches = []
        batch = []
        batch_size = 0
        for file in files:
            if (
                batch_size + len(file) + 1 > 7500
            ):  # max characters per command are 8192, but we need some space for the command itself
                file_batches.append(batch)
                batch = []
                batch_size = 0
            batch.append(file)
            batch_size += len(file) + 1
        if batch:
            file_batches.append(batch)

        for file_batch in file_batches:
            batch_args = args.copy()
            batch_args.append("-I" if not exclude_files else "-X")
            batch_args.append(",".join(file_batch))
            _run_lfs_command(path, batch_args, progress, env)
    else:
        _run_lfs_command(path, args, progress, env)


def lfs_push(path: str, remote: str, branch: str, progress: RemoteProgress, env):
    args = [get_git_cmd_path(), "lfs", "push", remote, branch]
    _run_lfs_command(path, args, progress, env)
