import anchorpoint as ap

import sys
import os
import time
import git_errors

current_dir = os.path.dirname(__file__)
parent_dir = os.path.join(current_dir, "..")
sys.path.insert(0, parent_dir)

from vc.apgit.repository import *
from vc.apgit.utility import get_repo_path
import git_repository_helper as helper

if parent_dir in sys.path:
    sys.path.remove(parent_dir)


def fetch_async(channel_id: str, project_path):
    ui = ap.UI()
    path = get_repo_path(channel_id, project_path)
    try:
        progress = None
        repo = GitRepository.load(path)
        if not repo:
            return

        if repo.has_remote():
            progress = ap.Progress("Fetching Git Changes")
            if not repo.fetch(progress=helper.FetchProgress(progress)):
                progress.finish()
                progress = None

        ap.vc_load_pending_changes("Git")
        ap.refresh_timeline_channel(channel_id)

        if progress:
            time.sleep(1)
            progress.finish()

    except Exception as e:
        if "vc_load_pending_changes" in dir(ap):
            ap.vc_load_pending_changes("Git")
        ap.refresh_timeline_channel(channel_id)

        if not git_errors.handle_error(e, path):
            ui.show_error("Failed to fetch Git Repository", str(e))
            raise e


def on_timeline_channel_action(channel_id: str, action_id: str, ctx):
    if action_id != "gitrefresh":
        return False
    ctx.run_async(fetch_async, channel_id, ctx.project_path)
    return True
