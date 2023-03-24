from typing import Optional
from vc.models import *

class Progress:
    def update(self, operation_code: str, current_count: int, max_count: int, info_text: Optional[str] = None):
        pass

class VCRepository:
    @staticmethod
    def is_repo(path: str) -> bool:
        pass

    @staticmethod
    def is_authenticated(url: str) -> bool:
        pass

    @staticmethod
    def authenticate(url: str, username: str, password: str):
        pass

    @classmethod
    def create(cls, path: str, username: str, email: str):
        pass

    @classmethod
    def clone(cls, remote_url: str, local_path: str, username: str, email: str, progress: Optional[Progress] = None):
        pass

    @classmethod
    def load(cls, path: str):
        pass

    def push(self, progress: Optional[Progress] = None) -> UpdateState:
        pass

    def update(self, progress: Optional[Progress] = None) -> UpdateState:
        pass

    def restore_files(self, files: list[str], changelist_id: Optional[str]):
        pass

    def get_pending_changes(self, checked_out: bool = False) -> Changes:
        pass

    def get_changes_for_changelist(self, id: str) -> Changes:
        pass

    def get_root_path(self):
        pass

    def launch_external_diff(self, tool: Optional[str] = None, paths: Optional[list[str]] = None):
        pass

    def launch_external_merge(self, tool: Optional[str] = None, paths: Optional[list[str]] = None):
        pass

    def get_current_change_id(self) -> str:
        pass

    def get_remote_change_id(self) -> str:
        pass

    def is_pull_required(self) -> bool:
        pass

    def is_push_required(self) -> bool:
        pass