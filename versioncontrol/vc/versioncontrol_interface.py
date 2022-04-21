from typing import Optional


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