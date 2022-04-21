from typing import Optional
from vc.models import *

class CloneProgress:
    def update(self, operation_code: str, current_count: int, max_count: int):
        pass

class VCRepository:
    @staticmethod
    def is_repo(path: str) -> bool:
        pass

    @classmethod
    def create(cls, path: str):
        pass

    @classmethod
    def clone(cls, remote_url: str, local_path: str, progress: Optional[CloneProgress] = None):
        pass

    @classmethod
    def load(cls, path: str):
        pass

    def get_pending_changes(self, checked_out: bool = False) -> Changes:
        pass

    def launch_external_diff(self, tool: Optional[str] = None, paths: Optional[list[str]] = None):
        pass

    def launch_external_merge(self, tool: Optional[str] = None, paths: Optional[list[str]] = None):
        pass