from dataclasses import dataclass, field
import anchorpoint as ap
import apsync
from enum import Enum
from typing import Optional

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

	
def parse_change(change, status: Status) -> PendingChange:
    result = PendingChange(path = change.path, old_path = change.old_path, status = status)
    return result

def parse_changes(repo_changes, changes: set[PendingChange]):
    for file in repo_changes.new_files:
        changes.add(parse_change(file, Status.NEW))
    for file in repo_changes.modified_files:
        changes.add(parse_change(file, Status.MODIFIED))
    for file in repo_changes.deleted_files:
        changes.add(parse_change(file, Status.DELETED))
    for file in repo_changes.renamed_files:
        changes.add(parse_change(file, Status.RENAMED))

def parse_conflicts(conflicts, changes: set[PendingChange]):
    for conflict in conflicts:
        if conflict in changes:
            changes[conflict].status = Status.CONFLICTED

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
    settings: Optional[apsync.Settings] = None
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
        print("add pull button")
        actions.append(VCBlockAction("Pull", "ap::git::pull"))
    elif repo.is_push_required():
        print("add push button")
        actions.append(VCBlockAction("Push", "ap::git::push"))

def create_revert_all_action(repo, block_ctx: VCPendingBlockContext, actions: list[VCBlockAction]):
    if (len(block_ctx.selected_changes) > 0 or len(block_ctx.unselected_changes) > 0):
        print("add revert button")
        actions.append(VCBlockAction("Revert All", "ap::git::revertall"))

def get_settings():
    return apsync.Settings("git_commit_settings")

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

    changes = set[PendingChange]()

    parse_changes(repo.get_pending_changes(staged = True), changes)
    parse_changes(repo.get_pending_changes(staged = False), changes)
    parse_conflicts(repo.get_conflicts(), changes)
    
    if len(changes) == 0: 
        return []
    
    return list(changes)

if __name__ == "__main__":
    ctx = ap.Context.instance()
    path = ctx.path

    changes = on_vc_get_pending_changes(path, ctx)
    if changes is None:
        ap.UI().show_info("Not a Git repository")
    else:
        block_ctx = VCPendingBlockContext(changes, [])
        info = on_vc_load_block_info(path, block_ctx,  ctx)
