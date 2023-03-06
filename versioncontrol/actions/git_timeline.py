import anchorpoint as ap
import apsync as aps
from typing import Optional
import os, logging
import git_errors

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
        changes[change.path] = change
    for file in repo_changes.modified_files:
        change = parse_change(repo_dir, file, ap.VCFileStatus.Modified, selected)
        changes[change.path] = change
    for file in repo_changes.deleted_files:
        change = parse_change(repo_dir, file, ap.VCFileStatus.Deleted, selected)
        changes[change.path] = change
    for file in repo_changes.renamed_files:
        change = parse_change(repo_dir, file, ap.VCFileStatus.Renamed, selected)
        changes[change.path] = change

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
        import sys, os
        sys.path.insert(0, script_dir)
        from vc.apgit.utility import get_repo_path
        from vc.apgit.repository import GitRepository

        info = ap.TimelineChannelVCInfo()

        path = get_repo_path(channel_id, ctx.project_path)
        repo = GitRepository.load(path)
        if not repo: return info

        is_merging = repo.has_conflicts()

        if repo.has_remote() and not is_merging:
            if repo.is_pull_required():
                pull = ap.TimelineChannelAction()
                pull.name = "Pull"
                pull.icon = aps.Icon(":/icons/cloud.svg")
                pull.identifier = "gitpull"
                pull.type = ap.ActionButtonType.Primary
                pull.tooltip = "Get all changes from the remote Git repository"
                info.actions.append(pull)
            elif repo.is_push_required():
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
    
        if is_merging:
            conflicts = ap.TimelineChannelAction()
            conflicts.name = "Resolve Conflicts"
            conflicts.identifier = "gitresolveconflicts"
            conflicts.type = ap.ActionButtonType.Danger
            conflicts.tooltip = "Resolve conflicts from other commits, branches, or from your shelved files"
            conflicts.icon = aps.Icon(":/icons/flash.svg")
            info.actions.append(conflicts)

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
        logging.info (f"on_load_timeline_channel_info exception: {str(e)}")
        return None
    finally:
        sys.path.remove(script_dir)

def on_load_timeline_channel_entries(channel_id: str, count: int, last_id: Optional[str], ctx):
    try:
        import sys, os
        sys.path.insert(0, script_dir)
        from vc.apgit.repository import GitRepository
        from vc.apgit.utility import get_repo_path
        from vc.models import HistoryType
        
        path = get_repo_path(channel_id, ctx.project_path)
        repo = GitRepository.load(path)
        if not repo:
            return []

        history_list = list()
        try:
            history = repo.get_history(count, rev_spec=last_id)
        except Exception as e:
            return history_list
        
        def map_commit(commit):
            entry = ap.TimelineChannelEntry()
            entry.id = commit.id
            entry.user_email = commit.author
            entry.time = commit.date
            entry.message = commit.message
            entry.has_details = True
            
            icon_color = "#90CAF9"
            if commit.type is HistoryType.LOCAL:
                entry.icon = aps.Icon(":/icons/upload.svg", icon_color)
                entry.tooltip = "This is a local commit. <br> You need to push it to make it available to your team."
            elif commit.type is HistoryType.REMOTE:
                entry.icon = aps.Icon(":/icons/cloud.svg", icon_color)
                entry.tooltip = "This commit is not yet synchronized with your project. <br> Press Pull to synchronize your project with the server."
            elif commit.type is HistoryType.SYNCED:
                entry.icon = aps.Icon(":/icons/versioncontrol.svg", icon_color)
                entry.tooltip = "This commit is in sync with your team"

            is_merge = len(commit.parents) > 1
            if is_merge:
                entry.caption = f"Pulled and merged changes"
                if commit.type is HistoryType.SYNCED:
                    entry.icon = aps.Icon(":/icons/merge.svg", icon_color)
                    entry.tooltip = entry.message
            else:
                entry.caption = f"Commited in {os.path.basename(path)}"
          
            return entry

        for commit in history:
            entry = map_commit(commit)
            
            if "parents" in dir(entry):
                parents_list = list()
                for parent in commit.parents:
                    parents_list.append(map_commit(parent))
                entry.parents = parents_list

            history_list.append(entry)

        return history_list
    except Exception as e:
        return []
    finally:
        sys.path.remove(script_dir)

def on_load_timeline_channel_pending_changes(channel_id: str, ctx):
    try:
        import sys, os
        sys.path.insert(0, script_dir)
        from vc.apgit.repository import GitRepository
        from vc.apgit.utility import get_repo_path
        
        path = get_repo_path(channel_id, ctx.project_path)
        repo = GitRepository.load(path)
        if not repo:
            return []

        repo_dir = repo.get_root_path()
        changes = dict[str,ap.VCPendingChange]()

        parse_changes(repo_dir, repo.get_pending_changes(staged = True), changes, True)
        parse_changes(repo_dir, repo.get_pending_changes(staged = False), changes, False)
        parse_conflicts(repo_dir, repo.get_conflicts(), changes)

        info = ap.VCPendingChangesInfo()
        info.changes = ap.VCPendingChangeList(changes.values())
        info.caption = f"changes in {os.path.basename(path)}"

        has_changes = len(info.changes)

        is_rebasing = repo.is_rebasing() or repo.is_merging()
        commit = ap.TimelineChannelAction()
        commit.name = "Commit"
        commit.identifier = "gitcommit"
        commit.icon = aps.Icon(":/icons/submit.svg")
        commit.type = ap.ActionButtonType.Primary
        if is_rebasing:
            commit.enabled = False
            commit.tooltip = "Cannot commit when resolving conflicts"
        else:
            commit.enabled = has_changes
            commit.tooltip = "Commit your changes to Git"
        info.actions.append(commit)

        revert = ap.TimelineChannelAction()
        revert.name = "Revert All"
        revert.identifier = "gitrevertall"
        revert.icon = aps.Icon(":/icons/revert.svg")
        revert.enabled = has_changes
        revert.tooltip = "Reverts all your modifications (cannot be undone)"
        info.actions.append(revert)

        if not repo.branch_has_stash():
            stash = ap.TimelineChannelAction()
            stash.name = "Shelve Files"
            stash.identifier = "gitstashfiles"
            stash.icon = aps.Icon(":/icons/Misc/shelf.svg")
            stash.enabled = has_changes
            stash.tooltip = "Puts all your changed and added files in the shelf. The files will disappear from the uncommitted changes, but can be restored at any time"
            info.actions.append(stash)

        return info
    except Exception as e:
        logging.info (f"on_load_timeline_channel_pending_changes exception: {str(e)}")
        return None
    finally:
        sys.path.remove(script_dir)


def run_func_wrapper(func, callback, *args):
    res = func(*args)
    callback(res)

def on_load_timeline_channel_pending_changes_async(channel_id: str, callback, ctx):
    ctx.run_async(run_func_wrapper, on_load_timeline_channel_pending_changes, callback, channel_id, ctx)

def on_load_timeline_channel_entry_details(channel_id: str, entry_id: str, ctx):
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

        changes = dict[str,ap.VCPendingChange]()
        parse_changes(repo.get_root_path(), repo.get_changes_for_changelist(entry_id), changes)

        if (repo.branch_contains(entry_id)):
            revert = ap.TimelineChannelAction()
            revert.name = "Undo Commit"
            revert.icon = aps.Icon(":/icons/undo.svg")
            revert.identifier = "gitrevertcommit"
            revert.type = ap.ActionButtonType.SecondaryText
            revert.tooltip = "Undos all file changes from a commit. The files will show up in the uncommitted changes."
            details.actions.append(revert)
            
        details.changes = ap.VCChangeList(changes.values())
        return details
    finally:
        sys.path.remove(script_dir)

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

        apply = ap.TimelineChannelAction()
        apply.name = "Restore"
        apply.icon = aps.Icon(":/icons/restore.svg")
        apply.identifier = "gitstashapply"
        apply.type = ap.ActionButtonType.Primary
        apply.tooltip = "Restores all files from the shelf. The files will show up in the uncommitted changes"
        details.actions.append(apply)
            
        drop = ap.TimelineChannelAction()
        drop.name = "Delete"
        drop.icon = aps.Icon("qrc:/icons/multimedia/trash.svg")
        drop.identifier = "gitstashdrop"
        drop.type = ap.ActionButtonType.SecondaryText
        drop.tooltip = "Permanently deletes all files in the shelf. This cannot be undone."
        details.actions.append(drop)       

        details.changes = ap.VCChangeList(changes.values())
        return details
    finally:
        sys.path.remove(script_dir)

def on_load_timeline_channel_entry_details_async(channel_id: str, entry_id: str, callback, ctx):
    ctx.run_async(run_func_wrapper, on_load_timeline_channel_entry_details, callback, channel_id, entry_id, ctx)

def on_vc_switch_branch(channel_id: str, branch: str, ctx):
    import sys, os
    sys.path.insert(0, script_dir)
    try:
        from vc.apgit.utility import get_repo_path
        from vc.apgit.repository import GitRepository
        if channel_id != "Git": return None

        path = get_repo_path(channel_id, ctx.project_path)
        repo = GitRepository.load(path)
        if not repo: return

        if repo.get_current_branch_name() == branch:
            return

        progress = ap.Progress(f"Switching Branch: {branch}", show_loading_screen = True)
        try:
            commits = repo.get_new_commits(repo.get_current_branch_name(), branch)
        except Exception as e:
            commits = []
        
        try:
            repo.switch_branch(branch)
        except Exception as e:
            if not git_errors.handle_error(e):
                ap.UI().show_info("Cannot switch branch", "You have changes that would be overwritten, commit them first.")
            return

        if len(commits) > 0:
            ap.delete_timeline_channel_entries(channel_id, list(commits))
    finally:
        sys.path.remove(script_dir)

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
    finally:
        sys.path.remove(script_dir)

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

        lockfile = os.path.join(repo.get_git_dir(), f"ap-fetch-{os.getpid()}.lock")
        if os.path.exists(lockfile):
            return

        try:
            with open(lockfile, "w") as f:
                repo.fetch()    
        finally:
            ap.refresh_timeline_channel(channel_id)
            os.remove(lockfile)

    except Exception as e:
        pass
    finally:
        sys.path.remove(script_dir)

def on_project_directory_changed(ctx):
    if "vc_load_pending_changes" in dir(ap):
        ap.vc_load_pending_changes("Git")
    else:
        ap.refresh_timeline_channel("Git")

def on_timeout(ctx):
    ctx.run_async(refresh_async, "Git", ctx.project_path)