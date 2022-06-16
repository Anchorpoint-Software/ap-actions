from calendar import c
from dataclasses import dataclass, field
import time
import anchorpoint as ap
import apsync as aps
from enum import Enum
from typing import Optional
import os

class Status(Enum):
    NEW = 1
    DELETED = 2
    MODIFIED = 3
    RENAMED = 4
    CONFLICTED = 5

@dataclass
class PendingChange:
    status: Status
    path: str
    old_path: Optional[str] = None
    preview: Optional[str] = None

    def __eq__(self, __o: object) -> bool:
        return self.path == __o.path

    def __ne__(self, __o: object) -> bool:
        return self.path != object.path

    def __hash__(self) -> int:
        return self.path.__hash__()

	
def parse_change(repo_dir: str, change, status: ap.VCFileStatus, selected: bool) -> ap.VCPendingChange:
    result = ap.VCPendingChange()
    result.status = status
    result.path = os.path.join(repo_dir, change.path)
    if selected:
        result.selected = True
    return result

def parse_changes(repo_dir: str, repo_changes, changes: set[ap.VCPendingChange], selected: bool):
    for file in repo_changes.new_files:
        changes.add(parse_change(repo_dir, file, ap.VCFileStatus.New, selected))
    for file in repo_changes.modified_files:
        changes.add(parse_change(repo_dir, file, ap.VCFileStatus.Modified, selected))
    for file in repo_changes.deleted_files:
        changes.add(parse_change(repo_dir, file, ap.VCFileStatus.Deleted, selected))
    for file in repo_changes.renamed_files:
        changes.add(parse_change(repo_dir, file, ap.VCFileStatus.Renamed, selected))

def parse_conflicts(conflicts, changes: set[ap.VCPendingChange]):
    for conflict in conflicts:
        if conflict in changes:
            changes[conflict].status = ap.VCFileStatus.Conflicted

@dataclass
class VCBlockAction:
    name: str
    action_id: str = None
    enabled: bool = True
    icon: Optional[str] = None
    color: Optional[str] = None
    tooltip: Optional[str] = None

@dataclass
class VCBranch:
    name: str

@dataclass
class VCPendingBlockContext:
    selected_changes: list[PendingChange]
    unselected_changes: list[PendingChange]

@dataclass
class VCPendingBlockInfo:
    settings: Optional[aps.Settings] = None
    branches: list[VCBranch] = field(default_factory=list)
    current_branch: Optional[VCBranch] = None
    actions: list[VCBlockAction] = field(default_factory=list)
    controls: list[VCBlockAction] = field(default_factory=list)

def create_commit_action(repo, block_ctx: VCPendingBlockContext, actions: list[VCBlockAction], requires_commit_action: bool):
    if requires_commit_action:
        print("add commit button. Enabled: ", len(block_ctx.selected_changes) > 0)
        actions.append(VCBlockAction("Commit", "ap::git::commit", enabled=len(block_ctx.selected_changes) > 0))

def create_sync_action(repo, block_ctx: VCPendingBlockContext, actions: list[VCBlockAction]):
    if repo.is_pull_required():
        actions.append(VCBlockAction("Pull", "ap::git::pull"))
    elif repo.is_push_required():
        actions.append(VCBlockAction("Push", "ap::git::push"))

def create_revert_all_action(repo, block_ctx: VCPendingBlockContext, actions: list[VCBlockAction]):
    if (len(block_ctx.selected_changes) > 0 or len(block_ctx.unselected_changes) > 0):
        actions.append(VCBlockAction("Revert All", "ap::git::revertall"))

def get_settings():
    return aps.Settings("git_commit_settings")

def on_vc_load_block_info(path: str, block_ctx: VCPendingBlockContext, ctx: ap.Context) -> Optional[VCPendingBlockInfo]:
    import sys, os
    sys.path.insert(0, os.path.join(os.path.split(__file__)[0], ".."))
    from vc.apgit.repository import GitRepository

    repo = GitRepository.load(path)
    if not repo:
        return None

    info = VCPendingBlockInfo()
    info.settings = get_settings()
    requires_commit_action = info.settings.get("Auto Push on Commit", True)

    # branches = repo.get_branches()
    # current_branch_name = repo.get_current_branch_name()
    # for branch in branches:
    #     if branch.name == current_branch_name:
    #         info.current_branch = branch
    #         break

    info.branches = [VCBranch("main"), VCBranch("WIP/Anchorpoint")]
    info.current_branch = info.branches[0]

    create_commit_action(repo, block_ctx, info.actions, requires_commit_action)
    create_sync_action(repo, block_ctx, info.actions)
    create_revert_all_action(repo, block_ctx, info.actions)

    return info


def on_vc_get_pending_changes(path: str, ctx: ap.Context) -> Optional[list[PendingChange]]:
    import sys, os
    sys.path.insert(0, os.path.split(__file__)[0])
    import is_git_repo as git

    if not git.path_contains_git_repo(path):
        return None
    
    sys.path.insert(0, os.path.join(os.path.split(__file__)[0], ".."))
    from vc.apgit.repository import GitRepository
    
    repo = GitRepository.load(path)
    if repo == None: 
        return

    repo_dir = repo.get_root_path()
    changes = set[PendingChange]()

    parse_changes(repo_dir, repo.get_pending_changes(staged = True), changes, True)
    parse_changes(repo_dir, repo.get_pending_changes(staged = False), changes, False)
    parse_conflicts(repo.get_conflicts(), changes)
    
    if len(changes) == 0: 
        return []
    
    return list(changes)

def on_load_timeline_channel_info(channel_id: str, ctx):
    print(channel_id)
    info = ap.TimelineChannelVCInfo()
    fetch = ap.TimelineChannelAction()
    fetch.name = "Fetch"
    fetch.identifier = "gitfetch"
    info.actions.append(fetch)

    push = ap.TimelineChannelAction()
    push.name = "Push"
    push.identifier = "gitpush"
    info.actions.append(push)

    main = ap.VCBranch()
    main.name = "main"
    info.current_branch = main
    info.branches.append(main)

    return info

def on_load_timeline_channel_entries(channel_id: str, count: int, last_id: Optional[str], ctx):
    import sys, os
    sys.path.insert(0, os.path.join(os.path.split(__file__)[0], ".."))
    from vc.apgit.repository import GitRepository
    from vc.apgit.utility import get_repo_path
    
    path = get_repo_path(channel_id, ctx.project_path)
    repo = GitRepository.load(path)
    if not repo:
        return []

    history = repo.get_history(count, rev_spec=last_id)
    history_list = list()

    for commit in history:
        entry = ap.TimelineChannelEntry()
        entry.id = commit.id
        entry.user_email = commit.author
        entry.time = commit.date
        entry.message = commit.message
        entry.has_details = True
        entry.caption = "Git Commit"
        history_list.append(entry)

    return history_list

def on_load_timeline_channel_pending_changes(channel_id: str, ctx):
    import sys, os
    sys.path.insert(0, os.path.join(os.path.split(__file__)[0], ".."))
    from vc.apgit.repository import GitRepository
    from vc.apgit.utility import get_repo_path
    
    path = get_repo_path(channel_id, ctx.project_path)
    print("PATH", path)
    repo = GitRepository.load(path)
    if not repo:
        return []

    repo_dir = repo.get_root_path()
    changes = set[ap.VCPendingChange]()

    parse_changes(repo_dir, repo.get_pending_changes(staged = True), changes, True)
    parse_changes(repo_dir, repo.get_pending_changes(staged = False), changes, False)
    parse_conflicts(repo.get_conflicts(), changes)

    info = ap.VCPendingChangesInfo()
    info.changes = ap.VCPendingChangeList(changes)

    commit = ap.TimelineChannelAction()
    commit.name = "Commit"
    commit.identifier = "gitcommit"
    info.actions.append(commit)

    revert = ap.TimelineChannelAction()
    revert.name = "Revert All"
    revert.identifier = "gitrevertall"
    info.actions.append(revert)

    return info

def on_timeline_channel_action(channel_id: str, action_id: str, ctx):
    print("on_timeline_channel_action", channel_id, action_id)
    pass

def on_pending_changes_action(channel_id: str, action_id: str, message: str, changes, ctx):
    print("on_pending_changes_action", channel_id, action_id, message)
    for change in changes:
        print(change.path)
    pass

if __name__ == "__main__":

    ctx = ap.Context.instance()
    path = ctx.path

    changes = on_vc_get_pending_changes(path, ctx)
    if changes is None:
        ap.UI().show_info("Not a Git repository")
    else:
        block_ctx = VCPendingBlockContext(changes, [])
        info = on_vc_load_block_info(path, block_ctx,  ctx)
