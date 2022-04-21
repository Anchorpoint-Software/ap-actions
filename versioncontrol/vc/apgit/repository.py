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
        return repo

    @classmethod
    def clone(cls, remote_url: str, local_path: str, progress: Optional[CloneProgress] = None):
        repo = cls()
        if progress is not None:
            repo.repo = git.Repo.clone_from(remote_url, local_path,  progress = _CloneProgressImpl(progress))
        else:
            repo.repo = git.Repo.clone_from(remote_url, local_path)
            
        repo.repo.git(local_path).lfs("--local", "install")
        return repo