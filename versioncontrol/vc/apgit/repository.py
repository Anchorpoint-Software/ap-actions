import os
import git
from vc.versioncontrol_interface import *

def _map_op_code(op_code: int) -> str:
    if op_code == 32:
        return "downloading"
    if op_code == 256:
        return "updating"
    return str(op_code)

class _CloneProgressImpl(git.RemoteProgress):
    def __init__(self, progress) -> None:
        super().__init__()
        self.progress = progress

    def update(self, op_code, cur_count, max_count=None, message=''):
        self.progress.update(_map_op_code(op_code), cur_count, max_count)

class GitRepository(VCRepository):
    @staticmethod
    def is_repo(path: str) -> bool:
        return os.path.exists(os.path.join(path, ".git"))

    @classmethod
    def create(cls, path: str):
        repo = cls()
        repo.repo = git.Repo.init(path)
        repo.repo.git.lfs("install", "--local")
        return repo

    @classmethod
    def clone(cls, remote_url: str, local_path: str, progress: Optional[CloneProgress] = None):
        repo = cls()
        if progress is not None:
            repo.repo = git.Repo.clone_from(remote_url, local_path,  progress = _CloneProgressImpl(progress))
        else:
            repo.repo = git.Repo.clone_from(remote_url, local_path)
            
        repo.repo.git.lfs("install", "--local")
        return repo

    @classmethod
    def load(cls, path: str):
        repo = cls()
        repo.repo = git.Repo(path, search_parent_directories=True)
        repo.repo.git.lfs("install", "--local")
        return repo

    def get_pending_changes(self, staged: bool = False) -> Changes:
        changes = Changes()
        if staged:
            diff = self.repo.head.commit.diff()
        else:
            diff = self.repo.index.diff(None) 
        
        self._get_file_changes(diff, changes)

        if not staged:
            for untracked_file in self.repo.untracked_files:
                changes.new_files.append(Change(path = untracked_file)) 
        
        return changes

    def stage_all_files(self):
        self.repo.git.add(".")

    def unstage_all_files(self):
        self.repo.git.restore("--staged", ".")

    def stage_files(self, paths: list[str]):
        existing = []
        deleted = []
        for path in paths:
            if os.path.exists(path):
                existing.append(path)
            else:
                deleted.append(path)

        if len(existing) > 0:
            self.repo.index.add(existing)
        if len(deleted) > 0:
            self.repo.index.remove(deleted)

    def unstage_files(self, paths: list[str]):
        existing = []
        deleted = []
        for path in paths:
            if os.path.exists(path):
                existing.append(path)
            else:
                deleted.append(path)

        if len(existing) > 0:
            self.repo.index.remove(existing)
        if len(deleted) > 0:
            self.repo.index.add(deleted)

    def commit(self, message: str):
        self.repo.index.commit(message)

    def _get_file_changes(self, diff: git.Diff, changes: Changes):
        for change in diff.iter_change_type("M"):
            changes.modified_files.append(Change(path = change.a_path)) 
        for change in diff.iter_change_type("A"):
            changes.new_files.append(Change(path = change.a_path)) 
        for change in diff.iter_change_type("R"):
            changes.renamed_files.append(Change(path = change.a_path, old_path = change.b_path)) 
        for change in diff.iter_change_type("D"):
            print("DELETED ", change.a_path)
            changes.deleted_files.append(Change(path = change.a_path)) 