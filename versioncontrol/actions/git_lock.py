import sys, os
current_dir = os.path.dirname(__file__)

class GitFileLocker:
    def __init__(self, repo, ctx) -> None:
        sys.path.insert(0, current_dir)
        from git_lfs_helper import LFSExtensionTracker
        from git_settings import GitProjectSettings
        if current_dir in sys.path:
            sys.path.remove(current_dir)

        try:
            self.lfs_tracker = LFSExtensionTracker(repo)
            self.settings = GitProjectSettings(ctx)
        except Exception as e:
            print(e)
            pass

    def is_file_lockable(self, path: str):
        if self.lfs_tracker and self.lfs_tracker.is_file_tracked(path):
            return True
        
        try:
            if self.settings:
                file_extension = os.path.splitext(path)[1][1:]
                lock_extensions = self.settings.get_lock_extensions()
                return file_extension in lock_extensions
        except:
            return False

        return False