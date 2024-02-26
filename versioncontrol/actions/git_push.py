from typing import Optional
import anchorpoint as ap

import sys
import os
import importlib

current_dir = os.path.dirname(__file__)
parent_dir = os.path.join(current_dir, "..")
sys.path.insert(0, parent_dir)

from git_pull import pull
from git_timeline import clear_forced_unlocked_config

importlib.invalidate_caches()
import git_errors
from vc.apgit.repository import GitRepository
from vc.apgit.utility import get_repo_path
from vc.models import UpdateState
from vc.versioncontrol_interface import Progress

if parent_dir in sys.path:
    sys.path.remove(parent_dir)


class PushProgress(Progress):
    def __init__(self, progress: ap.Progress) -> None:
        super().__init__()
        self.ap_progress = progress

    def update(
        self,
        operation_code: str,
        current_count: int,
        max_count: int,
        info_text: Optional[str] = None,
    ):
        if operation_code == "writing":
            if info_text:
                self.ap_progress.set_text(f"Uploading Files: {info_text}")
            else:
                self.ap_progress.set_text("Uploading Files")
            self.ap_progress.report_progress(current_count / max_count)
        else:
            self.ap_progress.set_text("Talking to Server")
            self.ap_progress.stop_progress()

    def canceled(self):
        return self.ap_progress.canceled


def show_push_failed(repo, error: str, channel_id, ctx):
    d = ap.Dialog()
    d.title = "Could not Push"
    d.icon = ":/icons/versioncontrol.svg"

    ap.log_error(f"Could not push: {error}")

    if (
        "Updates were rejected because the remote contains work that you do" in error
        or "failed to push some refs to" in error
        or "non-fast-forward" in error
        or "Updates were rejected because the tip of your current branch is behind"
        in error
        or "has already been updated" in error
    ):
        d.add_text("There are newer changes on the server.")
        d.add_info(
            "While pushing your changes, someone else has pushed new changes to the server.<br>Just hit retry to pull the new changes and push your changes again."
        )
    elif "Size must be less than or equal to" in error:
        d.add_text("A file is too large for GitHub.")
        d.add_info(
            'GitHub does enforce a maximium size limit per file for Git LFS. Learn more about it <a href="https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-git-large-file-storage">here.</a>'
        )
    elif "This repository is over its data quota" in error:
        d.add_text("The GitHub LFS limit has been reached.")
        d.add_info(
            'To solve the problem open your GitHub <a href="https://docs.github.com/en/billing/managing-billing-for-git-large-file-storage/about-billing-for-git-large-file-storage">Billing and Plans</a> page and buy more <b>Git LFS Data</b>.'
        )
    elif "protected branch" in error:
        d.add_text("The branch is protected, you cannot push to it.")
    elif (
        "Couldn't connect to server" in error
        or "Could not resolve host" in error
        or "Timed out" in error
        or "Connection refused" in error
        or "no such host" in error
    ):
        d.add_text("Could not connect to the Git server, maybe you are offline?")
        d.add_info("Please check your internet connection and try again.")
    else:
        from textwrap import TextWrapper

        d.add_text("Something went wrong, the Git push did not work correctly")
        d.add_info(
            'In order to help you as quickly as possible, you can <a href="ap://sendfeedback">send us a message</a>. We will get back to you by e-mail.'
        )
        error = "\n".join(TextWrapper(width=100).wrap(error))
        if error != "":
            d.add_text(f"Error: <i>{error}</i>")

    def retry():
        ctx = ap.get_context()
        ctx.run_async(sync_changes, channel_id, ctx)
        d.close()

    d.add_button("Retry", callback=lambda d: retry()).add_button(
        "Close", callback=lambda d: d.close(), primary=False
    )
    d.show()


def handle_git_autoprune(ctx, repo):
    from git_settings import GitAccountSettings

    git_settings = GitAccountSettings(ctx)
    prune_days = git_settings.auto_prune_days()
    if prune_days < 0:
        return

    prune_kwargs = {}
    if prune_days > 0:
        prune_kwargs["recent_commits_days"] = prune_days
    elif prune_days == 0:
        prune_kwargs["force"] = True

    try:
        lfs_version = repo.get_lfs_version()
        if "Anchorpoint" not in lfs_version:
            print(
                f"Skipping LFS auto prune because it is not supported by the version of LFS {lfs_version}."
            )
            return
        count = repo.prune_lfs(**prune_kwargs)
        print(f"Automatically pruned {count} LFS objects after push.")
    except Exception as e:
        print(f"An error occurred while pruning LFS objects: {e}")


def handle_git_autolock(ctx, repo):
    branch = repo.get_current_branch_name()
    locks = ap.get_locks(ctx.workspace_id, ctx.project_id)

    paths_to_unlock = []
    for lock in locks:
        if (
            lock.owner_id == ctx.user_id
            and "gitbranch" in lock.metadata
            and lock.metadata["gitbranch"] == branch
        ):
            paths_to_unlock.append(lock.path)

    ap.unlock(ctx.workspace_id, ctx.project_id, paths_to_unlock)
    clear_forced_unlocked_config()


def get_push_lockfile(repo_git_dir):
    return os.path.join(repo_git_dir, f"ap-push-{os.getpid()}.lock")


def push_in_progress(repo_git_dir):
    lockfile = get_push_lockfile(repo_git_dir)
    return os.path.exists(lockfile)


def delete_push_lockfiles(repo_git_dir):
    import glob

    pattern = os.path.join(repo_git_dir, "ap-push-*.lock")

    # Find all files that match the pattern
    lockfiles = glob.glob(pattern)

    # And delete them
    for lockfile in lockfiles:
        try:
            os.remove(lockfile)
        except Exception as e:
            print(f"An error occurred while deleting {lockfile}: {e}")


def delay(func, progress, *args, **kwargs):
    import time

    time.sleep(1)
    if progress:
        progress.finish()
    func(*args, **kwargs)


def repo_needs_pull(repo: GitRepository, progress):
    if not progress:
        progress = ap.Progress("Looking for Changes on Server", cancelable=True)
    else:
        progress.set_text("Looking for Changes on Server")

    try:
        repo.fetch()
        return repo.is_pull_required(), progress.canceled
    except Exception as e:
        git_errors.handle_error(e)
        ap.UI().show_info("Could not get remote changes", duration=4000)
        raise e


def pull_changes(repo: GitRepository, channel_id: str, ctx):
    rebase = False
    if rebase:
        raise NotImplementedError()

    try:
        if not pull(repo, channel_id, ctx):
            raise Exception("Pull Failed")

        ap.vc_load_pending_changes(channel_id)
        ap.refresh_timeline_channel(channel_id)

    except Exception as e:
        print(e)
        raise e


def sync_changes(channel_id: str, ctx):
    ui = ap.UI()
    path = get_repo_path(channel_id, ctx.project_path)
    repo = GitRepository.load(path)
    if not repo:
        return

    ap.timeline_channel_action_processing(channel_id, "gitpush", "Pushing...")
    ap.timeline_channel_action_processing(channel_id, "gitpull", "Pushing...")

    pull_required, canceled = repo_needs_pull(repo, None)
    if canceled:
        ui.show_success("Push canceled")

    if not pull_required:
        # Queue async to give Anchorpoint a chance to update the timeline
        ap.get_context().run_async(delay, push_changes, None, ctx, path, channel_id)
    else:
        try:
            pull_changes(repo, channel_id, ctx)
        except Exception as e:
            git_errors.handle_error(e, path)
            print(f"Auto-Push: Could not pull {str(e)}")
            ui.show_info(
                "Could not pull changes from server",
                "Your changed files have been committed, you can push them manually to the server",
                duration=20000,
            )

            ap.stop_timeline_channel_action_processing(channel_id, "gitpull")
            ap.stop_timeline_channel_action_processing(channel_id, "gitpush")
            return

        # Queue async to give Anchorpoint a chance to update the timeline
        ap.get_context().run_async(delay, push_changes, None, ctx, path, channel_id)


def push_changes(ctx, path, channel_id):
    ui = ap.UI()
    try:
        repo = GitRepository.load(path)
        if not repo:
            return
        progress = ap.Progress("Pushing Git Changes", cancelable=True)
        git_dir = repo.get_git_dir()
        if push_in_progress(git_dir):
            return

        ap.timeline_channel_action_processing(channel_id, "gitpush", "Pushing...")

        lockfile = get_push_lockfile(git_dir)

        with open(lockfile, "w") as f:
            state = repo.push(progress=PushProgress(progress))

            if state == UpdateState.CANCEL:
                ui.show_info("Push Canceled")
            elif state != UpdateState.OK:
                show_push_failed(repo, "", channel_id, ctx)
            else:
                handle_git_autolock(ctx, repo)

                progress.set_text("Clearing Cache")
                handle_git_autoprune(ctx, repo)
                ui.show_success("Push Successful")
                ap.update_timeline_last_seen()
    except Exception as e:
        if not git_errors.handle_error(e, path):
            show_push_failed(repo, str(e), channel_id, ctx)
    finally:
        progress.finish()
        if git_dir:
            delete_push_lockfiles(git_dir)

        ap.stop_timeline_channel_action_processing(channel_id, "gitpull")
        ap.stop_timeline_channel_action_processing(channel_id, "gitpush")

    ap.refresh_timeline_channel(channel_id)


def on_timeline_channel_action(channel_id: str, action_id: str, ctx):
    if action_id != "gitpush":
        return False
    ctx.run_async(sync_changes, channel_id, ctx)
    return True
