import anchorpoint as ap
import apsync as aps
from typing import Optional
import os, logging
import platform, re, sys
from datetime import datetime

current_dir = os.path.dirname(__file__)
script_dir = os.path.join(os.path.dirname(__file__), "..")

def parse_change(repo_dir: str, change, status: ap.VCFileStatus, selected: bool) -> ap.VCPendingChange:
    result = ap.VCPendingChange()
    result.status = status
    result.path = os.path.join(repo_dir, change.path)
    if selected:
        result.selected = True
    return result

def parse_changes(repo_dir: str, repo_changes, changes: dict[str,ap.VCPendingChange], selected: bool = False):
    for file in repo_changes.new_files:
        change = parse_change(repo_dir, file, ap.VCFileStatus.New, selected)
        changes[file.path] = change
    for file in repo_changes.modified_files:
        change = parse_change(repo_dir, file, ap.VCFileStatus.Modified, selected)
        changes[file.path] = change
    for file in repo_changes.deleted_files:
        change = parse_change(repo_dir, file, ap.VCFileStatus.Deleted, selected)
        changes[file.path] = change
    for file in repo_changes.renamed_files:
        change = parse_change(repo_dir, file, ap.VCFileStatus.Renamed, selected)
        changes[file.path] = change

def parse_conflicts(repo_dir: str, conflicts, changes: dict[str,ap.VCPendingChange]):
    for conflict in conflicts:
        conflict_path = os.path.join(repo_dir, conflict).replace(os.sep, "/")
        
        if conflict_path in changes:
            changes[conflict_path].status = ap.VCFileStatus.Conflicted
        else:
            conflict_change = ap.VCPendingChange()
            conflict_change.status = ap.VCFileStatus.Conflicted
            conflict_change.path = conflict_path
            changes[conflict_path] = conflict_change

def on_load_timeline_channel_info(channel_id: str, ctx):
    try:
        import sys
        sys.path.insert(0, script_dir)
        from vc.apgit.utility import get_repo_path
        from vc.apgit.repository import GitRepository
        from git_push import push_in_progress

        progress = ap.Progress("Git is optimizing things", "This can take a while", show_loading_screen=True, delay=2000)
        ap.timeline_channel_action_processing(channel_id, "gitrefresh", "Refreshing Git timeline...")
        info = ap.TimelineChannelVCInfo()

        path = get_repo_path(channel_id, ctx.project_path)
        repo = GitRepository.load(path)
        if not repo: return info

        has_conflicts = repo.has_conflicts()
        is_merging = repo.is_rebasing() or repo.is_merging()
    
        if repo.has_remote() and not has_conflicts:
            if repo.is_pull_required():
                pull = ap.TimelineChannelAction()
                pull.name = "Pull"
                pull.icon = aps.Icon(":/icons/cloud.svg")
                pull.identifier = "gitpull"
                pull.type = ap.ActionButtonType.Primary
                pull.tooltip = "Get all changed files from the remote Git repository"
                info.actions.append(pull)
            elif repo.is_push_required() and not push_in_progress(repo.get_git_dir()):
                push = ap.TimelineChannelAction()
                push.name = "Push"
                push.icon = aps.Icon(":/icons/upload.svg")
                push.identifier = "gitpush"
                push.type = ap.ActionButtonType.Primary
                push.tooltip = "Push all commits to the remote Git repository"
                info.actions.append(push)

        refresh = ap.TimelineChannelAction()
        refresh.name = "Refresh"
        refresh.icon = aps.Icon(":/icons/update.svg")
        refresh.identifier = "gitrefresh"
        refresh.tooltip = "Refresh the Git timeline"
        info.actions.append(refresh)

        if has_conflicts:
            conflicts = ap.TimelineChannelAction()
            conflicts.name = "Resolve Conflicts"
            conflicts.identifier = "gitresolveconflicts"
            conflicts.type = ap.ActionButtonType.Danger
            conflicts.tooltip = "Resolve conflicts from other commits, branches, or from your shelved files"
            conflicts.icon = aps.Icon(":/icons/flash.svg")
            info.actions.append(conflicts)

            if is_merging:
                cancel = ap.TimelineChannelAction()
                cancel.name = "Cancel"
                cancel.identifier = "gitcancelmerge"
                cancel.tooltip = "Cancel"
                cancel.icon = aps.Icon(":/icons/revert.svg")
                info.actions.append(cancel)

        current_branch_name = repo.get_current_branch_name()
        branches = repo.get_branches()
        for b in branches:
            branch = ap.VCBranch()
            branch.name = b.name
            branch.author = b.author
            branch.moddate = b.last_changed
            info.branches.append(branch)

            if b.name == current_branch_name:
                info.current_branch = branch

        if "has_stash" in dir(info):
            stash = repo.get_branch_stash()
            info.has_stash = stash is not None
            if info.has_stash:
                info.stashed_file_count = repo.get_stash_change_count(stash)
        
        return info
    except Exception as e:
        import git_errors
        git_errors.handle_error(e)
        print (f"on_load_timeline_channel_info exception: {str(e)}")
        return None
    finally:
        if script_dir in sys.path: sys.path.remove(script_dir)
        ap.stop_timeline_channel_action_processing(channel_id, "gitrefresh")

def load_timeline_callback():
    ap.open_timeline()

def cleanup_orphan_locks(ctx, repo):
    branch = repo.get_current_branch_name()
    locks = ap.get_locks(ctx.workspace_id, ctx.project_id)
    paths_to_delete = []
    for lock in locks:
        if lock.owner_id == ctx.user_id and "gitbranch" in lock.metadata and lock.metadata["gitbranch"] == branch:
            paths_to_delete.append(lock.path)
            print("Cleaning up orphan lock: " + lock.path)

    ap.unlock(ctx.workspace_id, ctx.project_id, paths_to_delete)

def handle_files_to_pull(repo, ctx):
    from git_lock import GitFileLocker
    locker = GitFileLocker(repo, ctx)

    changes = repo.get_files_to_pull(include_added=False)
    if not changes:
        return
    root_dir = repo.get_root_path()
    def make_readonly(changes):
        for change in changes:
            path = root_dir + "/"+ change.path
            if not os.path.exists(path):
                continue

            if not locker.is_file_lockable(path):
                continue

            try:
                os.chmod(path, 0o444)
            except Exception as e:
                print(f"Failed to make {change.path} readonly: {str(e)}")
                pass
            
    make_readonly(changes.modified_files)
    make_readonly(changes.deleted_files)
    make_readonly(changes.new_files)

def get_config_path():
    from pathlib import Path
    import os, sys
    if sys.platform == "darwin":
        return os.path.join(str(Path.home()), "Library", "Application Support", "Anchorpoint Software", "Anchorpoint", "git")
    elif sys.platform == "win32":
        return os.path.join(str(Path.home()), "AppData", "Roaming", "Anchorpoint Software", "Anchorpoint", "git")
    raise Exception("Unsupported platform")

def get_forced_unlocked_config_path():
    return os.path.join(get_config_path(), "forced_unlocked.bin")
    
def clear_forced_unlocked_config():
    file_path = get_forced_unlocked_config_path()
    if os.path.exists(file_path):
        os.remove(file_path)

def load_last_seen_fetched_commit(project_id: str):
    import pickle
    file_path = os.path.join(get_config_path(), "last_seen_fetched_commit.bin")
    if not os.path.exists(file_path):
        return None
    with open(file_path, "rb") as f:
        project_commit = pickle.load(f)
        if project_id in project_commit:
            commit = project_commit[project_id]
            if type(commit) != str:
                return None
            return commit
    return None

def save_last_seen_fetched_commit(project_id: str, commit: str):
    import pickle
    file_path = os.path.join(get_config_path(), "last_seen_fetched_commit.bin")
    project_commit = dict()
    if os.path.exists(file_path):
        with open(file_path, "rb") as f:
            project_commit = pickle.load(f)
    project_commit[project_id] = commit

    if not os.path.exists(file_path):
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "wb") as f:
        pickle.dump(project_commit, f)

import re

def extract_branches_from_commit_message(commit_message, current_branch):
    # Handle case: "Merge branch 'master' into conflicting-branch"
    into_regex = r"Merge branch '([\w\-\/\.]+)' into ([\w\-\/\.]+)"
    match = re.match(into_regex, commit_message)
    if match:
        return match.group(1),match.group(2)

    # Handle case: "Merge branch 'master' of remote-url" 
    # And also: "Merge branch 'wip/1520-new_merge_dialog' of remote-url into wip/1520-new_merge_dialog"
    of_regex = r"Merge branch '([\w\-\/\.]+)' of https:\/\/[\w\.\/\-]+(?: into ([\w\-\/\.]+))?"
    match = re.match(of_regex, commit_message)
    if match:
        return match.group(1), match.group(2) if match.group(2) else None if current_branch == match.group(1) else current_branch

    # Handle case: "Merge remote-tracking branch 'origin/conflicting-branch'"
    remote_regex = r"Merge remote-tracking branch '([\w\-\/\.]+)'"
    match = re.match(remote_regex, commit_message)
    if match:
        return match.group(1),current_branch

    # Handle case: "Merge pull request #42 from repo/branch"
    pr_regex = r"Merge pull request #\d+ from [\w\-\/\.]+/([\w\-\/\.]+)"
    match = re.match(pr_regex, commit_message)
    if match:
        return match.group(1),current_branch

    # Handle general case: "Merge 'branch'"
    merge_regex = r"Merge '([\w\-\/\.]+)'"
    match = re.match(merge_regex, commit_message)
    if match:
        return match.group(1),current_branch

    # Return None if no match
    return None, None

def map_commit(repo, commit):
    import sys
    sys.path.insert(0, script_dir)
    from vc.models import HistoryType

    entry = ap.TimelineChannelEntry()
    entry.id = commit.id
    entry.user_email = commit.author
    entry.time = commit.date
    entry.message = commit.message
    entry.has_details = True
    
    icon_color = "#f3d582"
    if commit.type is HistoryType.LOCAL:
        icon_color = "#fbbc9f"
        entry.icon = aps.Icon(":/icons/upload.svg", icon_color)
        entry.tooltip = "This is a local commit. <br> You need to push it to make it available to your team."
    elif commit.type is HistoryType.REMOTE:
        icon_color = "#90CAF9"
        entry.icon = aps.Icon(":/icons/cloud.svg", icon_color)
        entry.tooltip = "This commit is not yet synchronized with your project. <br> Press Pull to synchronize your project with the server."
    elif commit.type is HistoryType.SYNCED:
        entry.icon = aps.Icon(":/icons/versioncontrol.svg", icon_color)
        entry.tooltip = "This commit is in sync with your team"

    is_merge = len(commit.parents) > 1
    if is_merge:
        caption = "Pulled and merged files"
        current_branch_name = repo.get_current_branch_name()
        src_branch, target_branch = extract_branches_from_commit_message(commit.message, current_branch_name)
        if target_branch == current_branch_name and src_branch != f"origin/{current_branch_name}":
            caption = f"Merged branch {src_branch}"
        if src_branch == current_branch_name and target_branch and target_branch != f"origin/{current_branch_name}" and target_branch != current_branch_name:
            caption = f"Merged branch {src_branch} into {target_branch}"
            
        icon_color = "#9E9E9E"
        entry.caption = caption
        entry.tooltip = entry.message
        entry.message = ""
        if commit.type is HistoryType.SYNCED:
            entry.icon = aps.Icon(":/icons/merge.svg", icon_color)
    
    if script_dir in sys.path:
        sys.path.remove(script_dir)

    return entry

def on_load_first_timeline_channel_entry(channel_id: str, ctx):
    import sys
    try:
        sys.path.insert(0, script_dir)
        from vc.apgit.repository import GitRepository
        from vc.apgit.utility import get_repo_path
        path = get_repo_path(channel_id, ctx.project_path)
        repo = GitRepository.load(path)
        if not repo:
            return None
        
        if repo.is_unborn():
            if not repo.has_remote():
                return None
            
            try:
                commit = map_commit(repo, repo.get_history_entry("@{u}"))
            except:
                return None
            return commit
        
        return map_commit(repo, repo.get_history_entry("HEAD"))

    except Exception as e:
        import git_errors
        git_errors.handle_error(e)
        print (f"on_load_first_timeline_channel_entry exception: {str(e)}")
        return None
    finally:
        if script_dir in sys.path:
            sys.path.remove(script_dir)



def on_load_timeline_channel_entries(channel_id: str, time_start: datetime, time_end: datetime, ctx):
    try:
        import sys
        sys.path.insert(0, script_dir)
        from vc.apgit.repository import GitRepository
        from vc.apgit.utility import get_repo_path
        from vc.models import HistoryType
        if script_dir in sys.path: sys.path.remove(script_dir)

        from git_settings import GitAccountSettings
        git_settings = GitAccountSettings(ctx)
        
        has_more_commits = True
        path = get_repo_path(channel_id, ctx.project_path)
        repo = GitRepository.load(path)
        if not repo:
            return [], False

        history_list = list()
        try:
            history = repo.get_history(time_start, time_end)
        except Exception as e:
            return history_list, False

        cleanup_locks = True
        commits_to_pull = 0
        newest_committime_to_pull = 0
        newest_commit_to_pull = None
        for commit in history:
            entry = map_commit(repo, commit)
            if "parents" in dir(entry):
                parents_list = list()
                for parent in commit.parents:
                    parents_list.append(map_commit(repo, parent))
                entry.parents = parents_list

            if commit.type is HistoryType.REMOTE:
                commits_to_pull = commits_to_pull + 1
                if newest_committime_to_pull < commit.date:
                    newest_committime_to_pull = commit.date
                    newest_commit_to_pull = commit

            if commit.type is HistoryType.LOCAL:
                cleanup_locks = False

            if len(entry.parents) == 0:
                has_more_commits = False
            history_list.append(entry)

        if len(history_list) == 0 and repo.is_unborn():
            has_more_commits = False

        if newest_committime_to_pull > 0:
            ap.set_timeline_update_count(ctx.project_id, channel_id, commits_to_pull, newest_committime_to_pull)
        else:
            ap.set_timeline_update_count(ctx.project_id, channel_id, commits_to_pull)

        if git_settings.notifications_enabled():
            last_seen_commit = load_last_seen_fetched_commit(ctx.project_id)
            if newest_commit_to_pull and last_seen_commit != newest_commit_to_pull.id:
                if commits_to_pull == 1:
                    ap.UI().show_system_notification("You have new commits", f"You have one new commit to pull from the server.", callback = load_timeline_callback)
                else:
                    ap.UI().show_system_notification("You have new commits", f"You have {commits_to_pull} new commits to pull from the server.", callback = load_timeline_callback)
                save_last_seen_fetched_commit(ctx.project_id, newest_commit_to_pull.id)

        if cleanup_locks:
            cleanup_orphan_locks(ctx, repo)            

        workspace_settings = aps.SharedSettings(ctx.workspace_id, "remoteWorkspaceSettings")
        if git_settings.auto_lock_enabled() and repo.has_remote() and workspace_settings.get("readonlyLocksEnabled", True):
            handle_files_to_pull(repo, ctx)

        return history_list, has_more_commits
    except Exception as e:
        print(f"on_load_timeline_channel_entries exception: {str(e)}")
        raise e
        return [], False

def on_locks_removed(locks, ctx):
    # Git flagged locks (of this user) that are unlocked are stored in a file so that auto_lock will not lock them again
    import pickle
    file_path = get_forced_unlocked_config_path()
    path_mod_status = {}
    if os.path.exists(file_path):
        with open(file_path, 'rb') as file:
            path_mod_status = pickle.load(file)

    for lock in locks:
        if lock.owner_id != ctx.user_id or "type" not in lock.metadata or lock.metadata["type"] != "git": 
            continue
        if os.path.exists(lock.path):
            path_mod_status[lock.path] = os.path.getmtime(lock.path)
        else:
            path_mod_status[lock.path] = None

    if not os.path.exists(file_path):
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, 'wb') as file:
        pickle.dump(path_mod_status, file)

def handle_git_autolock(repo, ctx, changes):
    from git_lock import GitFileLocker
    import pickle
    locker = GitFileLocker(repo, ctx)
    paths_to_lock = set[str]()
    all_paths = set[str]()

    path_mod_status = {}
    file_path = get_forced_unlocked_config_path()
    if os.path.exists(file_path):
        try:
            with open(file_path, 'rb') as file:
                path_mod_status = pickle.load(file)
        except Exception as e:
            print(f"Could not load forced unlocked files: {e}")
            clear_forced_unlocked_config()
    
    for change in changes:
        if change.status != ap.VCFileStatus.New and change.status != ap.VCFileStatus.Unknown and locker.is_file_lockable(change.path):
            all_paths.add(change.path)

            # Do not lock files that are manually unlocked
            entry_exists = change.path in path_mod_status
            if os.path.exists(change.path):
                current_mtime = os.path.getmtime(change.path)
            else:
                current_mtime = None
            if entry_exists and path_mod_status[change.path] == current_mtime:
                continue
            
            if entry_exists:
                del path_mod_status[change.path]

            paths_to_lock.add(change.path)
    
    if os.path.exists(file_path):
        with open(file_path, 'wb') as file:
            pickle.dump(path_mod_status, file)
    
    locks = ap.get_locks(ctx.workspace_id, ctx.project_id)

    paths_to_unlock = list[str]()
    for lock in locks:
        if lock.owner_id == ctx.user_id and lock.path not in all_paths and "type" in lock.metadata and lock.metadata["type"] == "git" and "gitbranch" not in lock.metadata:
            paths_to_unlock.append(lock.path)

    ap.lock(ctx.workspace_id, ctx.project_id, list(paths_to_lock), metadata={"type": "git"})
    ap.unlock(ctx.workspace_id, ctx.project_id, paths_to_unlock)

def get_cached_paths(ref, repo, changes, deleted_only = False):
    sys.path.insert(0, current_dir)
    from git_load_file import get_lfs_cached_file
    from git_lfs_helper import LFSExtensionTracker
    if current_dir in sys.path: sys.path.remove(current_dir)

    lfsExtensions = LFSExtensionTracker(repo)

    currentrefs = []
    beforerefs = [] # ref^ for deleted files

    repo_dir = repo.get_root_path()        

    keys = changes.keys()
    for change_path in keys:
        change = changes[change_path]
        if deleted_only and change.status != ap.VCFileStatus.Deleted:
            continue

        if not lfsExtensions.is_file_tracked(change.path):
            continue
        if change.status == ap.VCFileStatus.Deleted:
            beforerefs.append(change_path)
        else:
            currentrefs.append(change_path)
    
    hashes = repo.get_lfs_filehash(paths=currentrefs, ref=ref)
    try:
        beforehashes = repo.get_lfs_filehash(paths=beforerefs, ref=ref + "^")
    except:
        beforehashes = []
        pass
    for change_path in keys:
        if change_path in hashes:
            file_hash = hashes[change_path]
            changes[change_path].cached_path = get_lfs_cached_file(file_hash, repo_dir)
            changes[change_path].cachable = True
        elif change_path in beforehashes:
            file_hash = beforehashes[change_path]
            changes[change_path].cached_path = get_lfs_cached_file(file_hash, repo_dir)
            changes[change_path].cachable = True


def on_load_timeline_channel_pending_changes(channel_id: str, ctx):
    try:
        import sys, os
        sys.path.insert(0, current_dir)
        sys.path.insert(0, script_dir)
        from vc.apgit.repository import GitRepository
        from vc.apgit.utility import get_repo_path
        from git_push import push_in_progress

        from git_settings import GitAccountSettings
        git_settings = GitAccountSettings(ctx)
        
        path = get_repo_path(channel_id, ctx.project_path)
        repo = GitRepository.load(path)
        if not repo:
            return []

        auto_push = git_settings.auto_push_enabled() and repo.has_remote()
        auto_lock = git_settings.auto_lock_enabled() and repo.has_remote()

        repo_dir = repo.get_root_path()
        changes = dict[str,ap.VCPendingChange]()

        parse_changes(repo_dir, repo.get_pending_changes(staged = True), changes, True)
        parse_changes(repo_dir, repo.get_pending_changes(staged = False), changes, False)
        parse_conflicts(repo_dir, repo.get_conflicts(), changes)

        get_cached_paths("HEAD", repo, changes, deleted_only=True)

        info = ap.VCPendingChangesInfo()
        info.changes = ap.VCPendingChangeList(changes.values())
        info.caption = f"changes in {os.path.basename(path)}"

        try:
            if auto_lock: handle_git_autolock(repo, ctx, info.changes)
        except Exception as e:
            print(f"Could not handle auto lock: {e}")

        has_changes = len(info.changes)

        is_push_in_progress = push_in_progress(repo.get_git_dir())
        is_rebasing = repo.is_rebasing() or repo.is_merging()
        commit = ap.TimelineChannelAction()
        commit.name = "Commit" if not auto_push or is_push_in_progress else "Push"
        commit.identifier = "gitcommit"
        commit.icon = aps.Icon(":/icons/submit.svg")
        commit.type = ap.ActionButtonType.Primary
        if is_rebasing:
            commit.enabled = False
            commit.tooltip = "Cannot commit when resolving conflicts" if not auto_push else "Cannot push when resolving conflicts"
        else:
            commit.enabled = has_changes
            commit.tooltip = "Commit your changes to Git" if not auto_push else "Push your changes to Git (disable auto-push in Git settings)"
        info.actions.append(commit)

        revert = ap.TimelineChannelAction()
        revert.name = "Revert"
        revert.identifier = "gitrevert"
        revert.icon = aps.Icon(":/icons/revert.svg")
        revert.tooltip = "Removes all your file changes (cannot be undone)"
        info.entry_actions.append(revert)

        return info
    except Exception as e:
        import git_errors
        git_errors.handle_error(e)
        print (f"on_load_timeline_channel_pending_changes exception: {str(e)}")
        return None
    finally:
        if script_dir in sys.path: sys.path.remove(script_dir)
        if current_dir in sys.path: sys.path.remove(current_dir)

def run_func_wrapper(func, callback, *args):
    res = func(*args)
    callback(res)

def on_load_timeline_channel_pending_changes_async(channel_id: str, callback, ctx):
    ctx.run_async(run_func_wrapper, on_load_timeline_channel_pending_changes, callback, channel_id, ctx)

def on_load_timeline_channel_entry_details(channel_id: str, entry_id: str, ctx):
    import sys
    sys.path.insert(0, script_dir)
    try:
        from vc.apgit.utility import get_repo_path
        from vc.apgit.repository import GitRepository

        if channel_id != "Git": return None
        details = ap.TimelineChannelEntryVCDetails()

        path = get_repo_path(channel_id, ctx.project_path)
        repo = GitRepository.load(path)
        if not repo: return details

        changes = dict[str,ap.VCPendingChange]()
        parse_changes(repo.get_root_path(), repo.get_changes_for_changelist(entry_id), changes)
        get_cached_paths(entry_id, repo, changes)

        has_remote = repo.has_remote()
        current_commit = repo.get_current_change_id()

        if not repo.commit_not_pulled(entry_id):
            revert = ap.TimelineChannelAction()
            revert.name = "Undo Commit"
            revert.icon = aps.Icon(":/icons/undo.svg")
            revert.identifier = "gitrevertcommit"
            revert.type = ap.ActionButtonType.SecondaryText
            revert.tooltip = "Undoes all file changes from this commit. The files will show up as changed files."
            details.actions.append(revert)

            if has_remote and current_commit != entry_id:
                reset = ap.TimelineChannelAction()
                reset.name = "Reset Project"
                reset.icon = aps.Icon(":/icons/restoreproject.svg")
                reset.identifier = "gitresetproject"
                reset.type = ap.ActionButtonType.SecondaryText
                reset.tooltip = "Resets the entire project to the state of this commit" if not repo.is_push_required() else "Cannot reset project, push your changes first"
                reset.enabled = not repo.is_push_required()
                details.actions.append(reset)

            restore_entry = ap.TimelineChannelAction()
            restore_entry.name = "Restore"
            restore_entry.icon = aps.Icon(":/icons/restore.svg")
            restore_entry.identifier = "gitrestorecommitfiles"
            restore_entry.tooltip = "Restores the selected files from this commit. The files will show up as changed files."
            details.entry_actions.append(restore_entry)
            
        details.changes = ap.VCChangeList(changes.values())
        return details
    except Exception as e:
        raise e
    finally:
        if script_dir in sys.path: sys.path.remove(script_dir)
        

def on_load_timeline_channel_stash_details(channel_id: str, ctx):
    import sys, os
    sys.path.insert(0, script_dir)
    try:
        from vc.apgit.utility import get_repo_path
        from vc.apgit.repository import GitRepository

        if channel_id != "Git": return None
        details = ap.TimelineChannelEntryVCDetails()

        path = get_repo_path(channel_id, ctx.project_path)
        repo = GitRepository.load(path)
        if not repo: return details

        stash = repo.get_branch_stash()
        if not stash:
            ap.UI().show_error("Could not find shelved files")
            return None
        
        changes = dict[str,ap.VCPendingChange]()
        parse_changes(repo.get_root_path(), repo.get_stash_changes(stash), changes)
        get_cached_paths(f"stash@{{{stash.id}}}", repo, changes)

        has_changes = repo.has_pending_changes(True)

        drop = ap.TimelineChannelAction()
        drop.name = "Clear"
        drop.icon = aps.Icon("qrc:/icons/multimedia/trash.svg")
        drop.identifier = "gitstashdrop"
        drop.type = ap.ActionButtonType.SecondaryText
        drop.tooltip = "Removes all files in the shelf (cannot be undone)"
        details.actions.append(drop)   

        apply = ap.TimelineChannelAction()
        apply.name = "Move to Changed Files"
        apply.icon = aps.Icon(":/icons/restoreMultipleFiles.svg")
        apply.identifier = "gitstashapply"
        apply.type = ap.ActionButtonType.SecondaryText
        if not has_changes:
            apply.enabled = True
            apply.tooltip = "Moves all files from the shelf to the changed files."
        else:
            apply.enabled = False
            apply.tooltip = "Unable to move shelved files when you already have changed files"

        details.actions.append(apply)

        details.changes = ap.VCChangeList(changes.values())
        return details
    except Exception as e:
        raise e
    finally:
        if script_dir in sys.path: sys.path.remove(script_dir)

def on_load_timeline_channel_entry_details_async(channel_id: str, entry_id: str, callback, ctx):
    ctx.run_async(run_func_wrapper, on_load_timeline_channel_entry_details, callback, channel_id, entry_id, ctx)

def on_vc_switch_branch(channel_id: str, branch: str, ctx):
    import sys, os
    sys.path.insert(0, script_dir)
    progress = ap.Progress(f"Switching Branch: {branch}", show_loading_screen = True)
    lock_disabler = ap.LockDisabler()
    try:
        from vc.apgit.utility import get_repo_path, is_executable_running
        from vc.apgit.repository import GitRepository
        from git_lfs_helper import LFSExtensionTracker
        if channel_id != "Git": return None

        path = get_repo_path(channel_id, ctx.project_path)
        repo = GitRepository.load(path)
        if not repo: return

        if repo.get_current_branch_name() == branch:
            return

        if platform.system() == "Windows":
            if is_executable_running(["unrealeditor.exe"]):
                lfsExtensions = LFSExtensionTracker(repo)
                if lfsExtensions.is_extension_tracked("umap") or lfsExtensions.is_extension_tracked("uasset"):
                    ap.UI().show_info("Cannot switch branch", "Unreal Engine prevents the switching of branches. Please close Unreal Engine and try again", duration = 10000)
                    return

        try:
            repo.switch_branch(branch)
        except Exception as e:
            import git_errors
            if not git_errors.handle_error(e):
                ap.UI().show_info("Cannot switch branch", "You have changes that would be overwritten, commit them first.")
            return

        ap.reload_timeline_entries()
    except Exception as e:
        raise e
    finally:
        if script_dir in sys.path: sys.path.remove(script_dir)

def on_vc_merge_branch(channel_id: str, branch: str, ctx):
    import sys, os
    import git_repository_helper as helper
    sys.path.insert(0, script_dir)
    lock_disabler = ap.LockDisabler()
    try:
        from vc.apgit.utility import get_repo_path, is_executable_running
        from vc.apgit.repository import GitRepository
        from vc.models import UpdateState
        from git_lfs_helper import LFSExtensionTracker
        if channel_id != "Git": return None

        path = get_repo_path(channel_id, ctx.project_path)
        repo = GitRepository.load(path)
        if not repo: return

        if repo.get_current_branch_name() == branch:
            return
        
        ui = ap.UI()

        # if platform.system() == "Windows":
        #     if is_executable_running(["unrealeditor.exe"]):
        #         lfsExtensions = LFSExtensionTracker(repo)
        #         if lfsExtensions.is_extension_tracked("umap") or lfsExtensions.is_extension_tracked("uasset"):
        #             ui.show_info("Cannot merge branch", "Unreal Engine prevents the merging of branches. Please close Unreal Engine and try again", duration = 10000)
        #             return

        if repo.has_pending_changes(True):
            ui.show_info("Cannot merge branch", "You have changes that would be overwritten, commit them first.")
            return

        if repo.has_remote():
            progress = ap.Progress(f"Merging Branch: {branch}", show_loading_screen = True)
            try:
                state = repo.fetch(progress=helper.FetchProgress(progress))
                if state != UpdateState.OK:
                    print("failed to fetch in merge")
                repo.fetch_lfs_files([branch], progress=helper.FetchProgress(progress))
            except Exception as e:
                print("failed to fetch in merge", str(e))
                raise e

        progress = ap.Progress(f"Merging Branch: {branch}", show_loading_screen = True)
        
        try:
            if not repo.merge_branch(branch):
                ui.show_info("Merge not needed", "Branch is already up to date.")
        except Exception as e:
            import git_errors
            if not git_errors.handle_error(e):
                if "conflict" in str(e):
                    ui.show_info("Conflicts detected", "Please resolve your conflicts.")  
                    ap.vc_load_pending_changes(channel_id, True)  
                else:
                    ui.show_info("Cannot merge branch", "You have changes that would be overwritten, commit them first.")
            return

        ap.vc_load_pending_changes(channel_id, True)  
        ap.reload_timeline_entries()
    except Exception as e:
        raise e
    finally:
        if script_dir in sys.path: sys.path.remove(script_dir)
        
def on_vc_create_branch(channel_id: str, branch: str, ctx):
    import sys
    sys.path.insert(0, script_dir)
    try:
        from vc.apgit.utility import get_repo_path
        from vc.apgit.repository import GitRepository
        if channel_id != "Git": return None

        path = get_repo_path(channel_id, ctx.project_path)
        repo = GitRepository.load(path)
        if not repo: return

        progress = ap.Progress(f"Creating Branch: {branch}", show_loading_screen = True)
        
        try:
            repo.create_branch(branch)
        except Exception as e:
            ap.UI().show_info("Cannot create branch")
            return
    except Exception as e:
        raise e
    finally:
        if script_dir in sys.path : sys.path.remove(script_dir)
        
def delete_lockfiles(repo_git_dir):
    import glob
    pattern = os.path.join(repo_git_dir, "ap-fetch-*.lock")

    # Find all files that match the pattern
    lockfiles = glob.glob(pattern)

    # And delete them
    for lockfile in lockfiles:
        try:
            os.remove(lockfile)
        except Exception as e:
            print(f"An error occurred while deleting {lockfile}: {e}")


def refresh_async(channel_id: str, project_path):
    if channel_id != "Git": return None
    project = aps.get_project(project_path)
    if not project: 
        return
    
    timeline_channel = aps.get_timeline_channel(project, channel_id)
    if not timeline_channel:
        return

    import sys, os
    sys.path.insert(0, script_dir)
    try:
        from vc.apgit.repository import GitRepository
        from vc.apgit.utility import get_repo_path

        path = get_repo_path(channel_id, project_path)
        repo = GitRepository.load(path)
        if not repo: return

        git_dir = repo.get_git_dir()
        lockfile = os.path.join(git_dir, f"ap-fetch-{os.getpid()}.lock")
        if os.path.exists(lockfile):
            return

        try:
            with open(lockfile, "w") as f:
                repo.fetch()
        finally:
            ap.refresh_timeline_channel(channel_id)
            delete_lockfiles(git_dir)

    except Exception as e:
        if "didn't exist" not in str(e):
            print("refresh_async exception: " + str(e))
        pass
    finally:
        if script_dir in sys.path: sys.path.remove(script_dir)
        
def on_project_directory_changed(ctx):
    ap.vc_load_pending_changes("Git")

def on_add_logging_data(channel_id: str, ctx):
    log = ""
    try:
        from vc.apgit.repository import GitRepository
        from vc.apgit.utility import get_repo_path
        path = get_repo_path(channel_id, ctx.project_path)
        repo = GitRepository.load(path)
        if not repo: return ""
        
        try:
            status = repo.git_status()
            log = "\nStatus:\n"
            log = log + "=========\n"
            log = log + status
        except Exception as e:
            print("on_add_logging_data status exception: " + str(e))

        try:
            git_log = repo.git_log()
            log = log + "\n\nLog:\n"
            log = log + "=========\n"
            log = log + git_log
        except Exception as e:
            print("on_add_logging_data log exception: " + str(e))

        try:
            git_config = repo.git_list_config()
            log = log + "\n\nConfig:\n"
            log = log + "=========\n"
            log = log + git_config
        except Exception as e:
            print("on_add_logging_data config exception: " + str(e))

        return log
    except Exception as e:
        print("on_add_logging_data exception: " + str(e))
        return log

def on_timeout(ctx):
    ctx.run_async(refresh_async, "Git", ctx.project_path)

def on_vc_get_changes_info(channel_id: str, entry_id: Optional[str], ctx):
    if channel_id != "Git": return None
    from git_lfs_helper import file_is_binary
    from git_load_file import get_lfs_cached_file
    try:
        from vc.apgit.repository import GitRepository
        from vc.apgit.utility import get_repo_path
        from git_lfs_helper import LFSExtensionTracker

        path = get_repo_path(channel_id, ctx.project_path)
        repo = GitRepository.load(path)
        if not repo: return None
        lfsExtensions = LFSExtensionTracker(repo)

        info = ap.VCGetChangesInfo()
        rel_path = os.path.relpath(ctx.path, ctx.project_path).replace("\\", "/")

        is_binary = lfsExtensions.is_file_tracked(ctx.path) or file_is_binary(ctx.path)
        
        if entry_id:
            if entry_id == "vcStashedChanges":
                stash = repo.get_branch_stash()
                if not stash:
                    return None
                if not is_binary:
                    try:
                        info.modified_content = repo.get_stash_content(rel_path, stash).rstrip()
                        info.original_content = repo.get_file_content(rel_path, "HEAD").rstrip()
                    except:
                        print("on_vc_get_changes_info exception: could not load stash content for changes info")
                else:
                    try:
                        # TODO: set info.original_filepath to allow an image diff view in the detail page
                        hash = repo.get_lfs_filehash(paths=[rel_path], ref=f"stash@{{{stash.id}}}")[rel_path]
                        info.modified_filepath = get_lfs_cached_file(hash, path)
                    except:
                        pass
            else:
                if not is_binary:
                    try:
                        info.modified_content = repo.get_file_content(rel_path, entry_id).rstrip()
                        info.original_content = repo.get_file_content(rel_path, entry_id + "~").rstrip()
                    except:
                        print("on_vc_get_changes_info exception: could not load commit content for changes info")
                else:
                    try:
                        # TODO: set info.original_filepath to allow an image diff view in the detail page
                        hash = None
                        hashes = repo.get_lfs_filehash(paths=[rel_path], ref=entry_id)
                        if rel_path in hashes:
                            hash = hashes[rel_path]
                        else:
                            hashes = repo.get_lfs_filehash(paths=[rel_path], ref=entry_id + "^")
                            if rel_path in hashes:
                                hash = hashes[rel_path]
                        if hash:
                            info.modified_filepath = get_lfs_cached_file(hash, path)
                    except:
                        pass
        else:
            if not is_binary:
                try:
                    info.original_content = repo.get_file_content(rel_path, "HEAD").rstrip()
                except:
                    print("on_vc_get_changes_info exception: could not load HEAD content for changes info")
            if os.path.exists(ctx.path):
                if not is_binary:
                    with open(ctx.path, encoding="utf-8") as f:                
                        info.modified_content = f.read().rstrip()
                info.modified_filepath = ctx.path
            else:
                info.modified_content = ""
                info.modified_filepath = ctx.path

        return info

    except Exception as e:
        import git_errors
        git_errors.handle_error(e)
        print("on_vc_get_changes_info exception")
        return None
    
