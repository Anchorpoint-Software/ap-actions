import anchorpoint as ap
import apsync as aps

import sys, os
current_dir = os.path.dirname(__file__)
parent_dir = os.path.join(current_dir, "..")
sys.path.insert(0, parent_dir)

from vc.apgit.repository import * 
from vc.apgit.utility import get_repo_path, GIT_COMMIT_AUTO_PUSH
sys.path.remove(parent_dir)

def stage_files(changes, all_files_selected, repo, lfs, progress):
    def lfs_progress_callback(current, max):
        if progress.canceled:
            return False
        if max > 0:
            progress.report_progress(current / max)
        return True

    to_stage = []
    for change in changes:
        if change.selected:
            to_stage.append(change.path)

    if len(to_stage) == 0:
        return

    progress.set_text("Finding binary files")
    lfs.lfs_track_binary_files(to_stage, repo, lfs_progress_callback)
    if progress.canceled: 
        return

    progress.stop_progress()
    progress.set_text("Preparing your files to be committed. This may take some time")

    def progress_callback(current, max):
        if progress.canceled:
            return False
        progress.set_text("Staging files")
        if max > 0:
            progress.report_progress(current / max)
        return True

    try:
        repo.sync_staged_files(to_stage, all_files_selected, progress_callback)
    except Exception as e:
        submodule_error = False
        submodule_location = ""
        for change in to_stage:
            if os.path.isdir(change):
                gitdir = os.path.join(change, ".git")
                if os.path.exists(gitdir):
                    submodule_error = True
                    submodule_location = gitdir
                    break
        
        if submodule_error:
            rel_path = os.path.relpath(submodule_location,repo.get_root_path())
            d = ap.Dialog()
            d.title = "Your project contains more than one Git repository"
            d.icon = ":/icons/versioncontrol.svg"
            d.add_text(f"A folder in your project contains another Git repository and Git submodules<br>are currently not supported by Anchorpoint.<br><br>To resolve the issue, do the following:<ol><li>Backup the folder <b>{os.path.dirname(rel_path)}</b></li><li>Delete the hidden .git folder: <b>{rel_path}</b></li><li>Commit again</li></ol><br>Do not touch the .git folder in your project root!")
            d.show()
        else:
            raise e

def push_changes(repo: GitRepository, channel_id: str):
    import sys
    script_dir = os.path.dirname(__file__)
    sys.path.insert(0, script_dir)
    from git_push import PushProgress, show_push_failed
    if script_dir in sys.path:
        sys.path.remove(script_dir)

    try:
        progress = ap.Progress("Pushing Git Changes", cancelable=True)
        ap.timeline_channel_action_processing(channel_id, "gitpush", "Pushing...")
        ap.timeline_channel_action_processing(channel_id, "gitpull", "Pushing...")
        state = repo.push(progress=PushProgress(progress))
        if state == UpdateState.CANCEL:
            ap.UI().show_info("Push Canceled")
        elif state != UpdateState.OK:
            show_push_failed("", channel_id, repo.get_root_path())    
        else:
            ap.UI().show_success("Push Successful")
    except Exception as e:
        show_push_failed(str(e), channel_id, repo.get_root_path())
    finally:
        ap.stop_timeline_channel_action_processing(channel_id, "gitpush")
        ap.stop_timeline_channel_action_processing(channel_id, "gitpull")
        ap.refresh_timeline_channel(channel_id)

def pull_changes(repo: GitRepository, channel_id: str):
    from git_pull import pull
    
    rebase = False
    if rebase: raise NotImplementedError()

    try:
        if not pull(repo, channel_id):
            raise Exception("Pull Failed")
        
        ap.vc_load_pending_changes(channel_id, True)
        ap.refresh_timeline_channel(channel_id)

    except Exception as e:
        print(e)
        raise e
    
def repo_needs_pull(repo: GitRepository):
    progress = ap.Progress("Looking for Changes on Server", show_loading_screen=True, cancelable=True)
    
    try:
        repo.fetch()
        return repo.is_pull_required(), progress.canceled
    except Exception as e:
        ap.UI().show_info("Could not get remote changes", "Your changed files have been committed, you can push them manually to the server", duration = 8000)
        raise e
    

def commit_auto_push(repo: GitRepository, channel_id: str):
    ui = ap.UI()
    pull_required, canceled = repo_needs_pull(repo)
    if canceled:
        ui.show_success("Push canceled")
    if not pull_required:
        push_changes(repo, channel_id)
    else:
        try:
            pull_changes(repo, channel_id)
        except:
            return

        # Queue async to give Anchorpoint a chance to update the timeline
        ap.get_context().run_async(push_changes, repo, channel_id)


def on_pending_changes_action(channel_id: str, action_id: str, message: str, changes, all_files_selected, ctx):
    import git_lfs_helper as lfs
    if action_id != "gitcommit": return False
    ui = ap.UI()
    progress = ap.Progress("Committing Files", "Depending on your file count and size this may take some time", show_loading_screen=True, cancelable=True)
    try:
        path = get_repo_path(channel_id, ctx.project_path)
        repo = GitRepository.load(path)
        if not repo: return
        stage_files(changes, all_files_selected, repo, lfs, progress)
        if progress.canceled:
            ui.show_success("commit canceled")
            return
        
        progress.stop_progress()
        progress.set_text("Creating the commit. This may take some time")

        staged = repo.get_pending_changes(staged=True)
        changecount = staged.size()
        if changecount == 0:
            ui.show_info("Nothing to commit")
            return

        if len(ctx.username) > 0 and len(ctx.email) > 0:
            repo.set_username(ctx.username, ctx.email, ctx.project_path)

        repo.commit(message)

        if GIT_COMMIT_AUTO_PUSH:
            print("auto push enabled")
            progress.finish()
            commit_auto_push(repo, channel_id)
        else:
            ui.show_success("Commit succeeded")
        
    except Exception as e:
        print(str(e))
        ui.show_error("Commit Failed", str(e).splitlines()[0])
        raise e
    finally:
        ap.vc_load_pending_changes(channel_id, True)
        ap.refresh_timeline_channel(channel_id)
        return True