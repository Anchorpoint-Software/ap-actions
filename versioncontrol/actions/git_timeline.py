import anchorpoint as ap
import apsync as aps
from typing import Optional
import os

def parse_change(repo_dir: str, change, status: ap.VCFileStatus, selected: bool) -> ap.VCPendingChange:
    result = ap.VCPendingChange()
    result.status = status
    result.path = os.path.join(repo_dir, change.path)
    if selected:
        result.selected = True
    return result

def parse_changes(repo_dir: str, repo_changes, changes: dict[str,ap.VCPendingChange], selected: bool):
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
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
        from vc.apgit.utility import get_repo_path
        from vc.apgit.repository import GitRepository

        info = ap.TimelineChannelVCInfo()

        path = get_repo_path(channel_id, ctx.project_path)
        repo = GitRepository.load(path)
        if not repo: return info

        is_rebasing = repo.is_rebasing()

        if repo.has_remote() and not is_rebasing:
            if repo.is_pull_required():
                pull = ap.TimelineChannelAction()
                pull.name = "Pull"
                pull.icon = aps.Icon(":/icons/cloud.svg")
                pull.identifier = "gitpullrebase"
                pull.type = ap.ActionButtonType.Primary
                info.actions.append(pull)
            elif repo.is_push_required():
                push = ap.TimelineChannelAction()
                push.name = "Push"
                push.icon = aps.Icon(":/icons/upload.svg")
                push.identifier = "gitpush"
                push.type = ap.ActionButtonType.Primary
                info.actions.append(push)
            else:
                fetch = ap.TimelineChannelAction()
                fetch.name = "Fetch"
                fetch.icon = aps.Icon(":/icons/update.svg")
                fetch.identifier = "gitfetch"
                info.actions.append(fetch)
        
        if is_rebasing:
            conflicts = ap.TimelineChannelAction()
            conflicts.name = "Resolve Conflicts"
            conflicts.identifier = "gitresolveconflicts"
            conflicts.type = ap.ActionButtonType.Danger
            conflicts.icon = aps.Icon(":/icons/flash.svg")
            info.actions.append(conflicts)

            cancel = ap.TimelineChannelAction()
            cancel.name = "Cancel"
            cancel.identifier = "gitcancelrebase"
            cancel.icon = aps.Icon(":/icons/revert.svg")
            info.actions.append(cancel)

        main = ap.VCBranch()
        main.name = "main"
        info.current_branch = main
        info.branches.append(main)

        return info
    except Exception as e:
        print (e)
        return None

def on_load_timeline_channel_entries(channel_id: str, count: int, last_id: Optional[str], ctx):
    try:
        import sys, os
        sys.path.insert(0, os.path.join(os.path.split(__file__)[0], ".."))
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
        except:
            return history_list
        
        for commit in history:
            entry = ap.TimelineChannelEntry()
            entry.id = commit.id
            entry.user_email = commit.author
            entry.time = commit.date
            entry.message = commit.message
            entry.has_details = True
            entry.caption = f"Made a Git Commit in {os.path.basename(path)}"

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
            
            history_list.append(entry)

        return history_list
    except Exception as e:
        print (e)
        return []

def on_load_timeline_channel_pending_changes(channel_id: str, ctx):
    try:
        import sys, os
        sys.path.insert(0, os.path.join(os.path.split(__file__)[0], ".."))
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

        is_rebasing = repo.is_rebasing()
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
        if is_rebasing:
            revert.enabled = False
            revert.tooltip = "Cannot revert files when resolving conflicts"
        else:
            revert.enabled = has_changes
            revert.tooltip = "Reverts all your modifications (cannot be undone)"
        info.actions.append(revert)

        return info
    except Exception as e:
        print (e)
        return None

def refresh_async(channel_id: str, project_path):
    project = aps.get_project(project_path)
    if not project: 
        return
    
    timeline_channel = aps.get_timeline_channel(project, channel_id)
    if not timeline_channel:
        return

    import sys, os
    sys.path.insert(0, os.path.join(os.path.split(__file__)[0], ".."))
    try:
        from vc.apgit.repository import GitRepository
        from vc.apgit.utility import get_repo_path

        path = get_repo_path(channel_id, project_path)
        repo = GitRepository.load(path)
        if not repo: return

        lockfile = os.path.join(repo.get_git_dir(), f"ap-fetch-{os.getpid()}.lock")
        if os.path.exists(lockfile):
            print("fetch is already running")
            return

        try:
            with open(lockfile, "w") as f:
                repo.fetch()    
        finally:
            ap.refresh_timeline_channel(channel_id)
            os.remove(lockfile)

    except Exception as e:
        pass

def on_project_directory_changed(ctx):
    ap.refresh_timeline_channel("Git")

def on_timeout(ctx):
    ctx.run_async(refresh_async, "Git", ctx.project_path)