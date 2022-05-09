from dataclasses import dataclass
import anchorpoint as ap
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

def on_vc_get_pending_changes(path: str, ctx: ap.Context):
    import sys, os
    sys.path.insert(0, os.path.split(__file__)[0])
    import is_git_repo as git

    if not git.path_contains_git_repo(path):
        return None
    
    sys.path.insert(0, os.path.join(os.path.split(__file__)[0], ".."))
    from vc.apgit.repository import GitRepository
    
    repo = GitRepository.load(path)
    if repo == None: return

    changes = set[PendingChange]()

    try:
        parse_changes(repo.get_pending_changes(staged = True), changes)
        parse_changes(repo.get_pending_changes(staged = False), changes)
        parse_conflicts(repo.get_conflicts(), changes)
    except ValueError:
        # Catches errors such as unborn repositories
        return changes

    return list(changes)

if __name__ == "__main__":
    ctx = ap.Context.instance()
    path = ctx.path

    changes = on_vc_get_pending_changes(path, ctx)
    if not changes:
        ap.UI().show_info("Not a Git repository")
    else:
        for change in changes:
            print (change.path, "  |  " , change.status)