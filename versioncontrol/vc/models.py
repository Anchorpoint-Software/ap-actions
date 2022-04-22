from dataclasses import dataclass
from types import new_class
from typing import Optional
from enum import Enum

class UpdateState(Enum):
    OK = 1
    ERROR = 2
    CONFLICT = 3

@dataclass
class Change:
    """Represents a versioned controlled change"""
    path: str
    old_path: Optional[str] = None
    cached_path: Optional[str] = None

@dataclass
class Changes:
    """Represents the changes of a version controlled instance (e.g. the working directory or a changelist)"""
    new_files: list[Change]
    modified_files: list[Change]
    deleted_files: list[Change]
    renamed_files: list[Change]

    def __init__(self) -> None:
        self.new_files = []
        self.modified_files = []
        self.deleted_files = []
        self.renamed_files = []
    
    def size(self) -> int:
        return len(self.new_files) + len(self.modified_files) + len(self.deleted_files) + len(self.renamed_files)

    @staticmethod
    def _list_to_string(list: list[Change]) -> str:
        if len(list) > 0: 
            repr = ""
            for f in list:
                repr += f"\n{f}"
            return repr
        else: return "None"

    def __repr__(self) -> str:
        repr = ""
        if len(self.new_files) > 0:
            repr += "New Files:\n"
            repr += Changes._list_to_string(self.new_files) + "\n\n"
        
        if len(self.modified_files) > 0:
            repr += "\n\nChanged Files:\n"
            repr += Changes._list_to_string(self.modified_files)
        
        if len(self.deleted_files) > 0:
            repr += "\n\nDeleted Files:\n"
            repr += Changes._list_to_string(self.deleted_files)
        
        if len(self.renamed_files) > 0:
            repr += "\n\nRenamed Files:\n"
            repr += Changes._list_to_string(self.renamed_files)
        return "None" if len(repr) == 0 else repr

@dataclass
class HistoryEntry:
    """Represents a history entry of a version controlled repository"""
    id: str
    author: str
    message: str
    date: int

