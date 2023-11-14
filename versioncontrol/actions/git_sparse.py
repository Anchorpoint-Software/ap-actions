import anchorpoint as ap
import apsync as aps
from vc.apgit.repository import * 
import os
import time

current_dir = os.path.dirname(__file__)
script_dir = os.path.join(os.path.dirname(__file__), "..")

class SparseProgress(Progress):
    def __init__(self, progress: ap.Progress) -> None:
        super().__init__()
        self.ap_progress = progress

    def update(self, operation_code: str, current_count: int, max_count: int, info_text: Optional[str] = None):
        if operation_code == "downloading":
            if info_text:
                self.ap_progress.set_text(f"Downloading Files: {info_text}")
            else:
                self.ap_progress.set_text("Downloading Files")
            self.ap_progress.report_progress(current_count / max_count)
        elif operation_code == "updating":
            self.ap_progress.set_text("Updating Files")
            self.ap_progress.report_progress(current_count / max_count)
        else:
            self.ap_progress.set_text("Talking to Server")
            self.ap_progress.stop_progress()

    def canceled(self):
        return self.ap_progress.canceled

def on_load_remote_folders(ctx):
    try:
        import sys
        sys.path.insert(0, script_dir)
        # from vc.apgit.utility import get_repo_path
        # from git_push import push_in_progress

        if ctx.project_path is None:
            print("on_load_remote_folders: project_path is None")
            return None

        repo = GitRepository.load(ctx.project_path)

        def is_remote_path(path, sparse_checkout_set):
            if not sparse_checkout_set:
                return False
            path_parts = path.split("/")
            for i in range(len(path_parts)):
                if "/".join(path_parts[:i + 1]) in sparse_checkout_set:
                    return False
            return True

        def is_download_root(path, sparse_checkout_set):
            if not sparse_checkout_set:
                return False
            return path in sparse_checkout_set

        tree_entries = []
        tree_entry_path_list = repo.get_folders_from_tree()
        has_root_added = False
        try:
            sparse_checkout_set = repo.get_sparse_checkout_folder_set()
        except Exception as e:
            sparse_checkout_set = set()
            if("is not sparse" in str(e)):
                print("Sparse checkout is not enabled in this repository")
                entry = ap.RemoteFolderEntry()
                entry.path = ""
                entry.is_remote = False
                entry.is_download_root = True
                tree_entries.append(entry)
                has_root_added = True

        has_any_remote_folders = False

        for folder_path in tree_entry_path_list:
            if "/.ap" in folder_path or folder_path.startswith(".ap"):
                continue
            entry = ap.RemoteFolderEntry()
            entry.path = folder_path
            entry.is_remote = is_remote_path(folder_path, sparse_checkout_set)
            if entry.is_remote:
                has_any_remote_folders = True
            entry.is_download_root = is_download_root(folder_path, sparse_checkout_set)
            tree_entries.append(entry)

        if not has_root_added:
            entry = ap.RemoteFolderEntry()
            entry.path = ""
            entry.is_remote = has_any_remote_folders
            entry.is_download_root = True
            tree_entries.append(entry)
        return tree_entries

    except Exception as e:
        import git_errors
        git_errors.handle_error(e)
        raise e
    finally:
        if script_dir in sys.path: sys.path.remove(script_dir)

def on_download_remote_folder(relative_folder_path: str, ctx):
    try:
        import sys
        sys.path.insert(0, script_dir)
        from vc.apgit.repository import GitRepository

        progress = ap.Progress("Downloading", show_loading_screen=True, cancelable=False)

        if ctx.project_path is None:
            raise Exception("project_path is None")

        repo = GitRepository.load(ctx.project_path)
        needed_download = repo.sparse_checkout_folder(relative_folder_path, progress=SparseProgress(progress))
        if needed_download:
            ui = ap.UI()
            ui.reload_tree()
            time.sleep(2)
            ui.reload()
        progress.finish()

        return True

    except Exception as e:
        import git_errors
        git_errors.handle_error(e)
        raise e
    finally:
        if script_dir in sys.path: sys.path.remove(script_dir)

def on_unload_remote_folder(relative_folder_path: str, ctx):
    try:
        import sys
        sys.path.insert(0, script_dir)
        from vc.apgit.repository import GitRepository

        progress = ap.Progress("Unloading", show_loading_screen=True, cancelable=False)

        if ctx.project_path is None:
            raise Exception("project_path is None")

        repo = GitRepository.load(ctx.project_path)
        needed_unload = repo.sparse_unload_folder(relative_folder_path, progress=SparseProgress(progress))
        if needed_unload:
            ui = ap.UI()
            ui.reload_tree()
            time.sleep(2)
            ui.reload()
        progress.finish()

        return True

    except Exception as e:
        import git_errors
        if git_errors.handle_error(e):
            raise e
        message = str(e)
        if "it contains uncommitted changes" in message:
            print("Failed to unload folder because it contains uncommitted changes")
            ui = ap.UI()
            ui.show_info(title="Cannot unload folder", duration=6000, description="This folder contains changed files. Commit them first.")
            ui.navigate_to_channel_detail("Git", "vcPendingChanges")
    finally:
        if script_dir in sys.path: sys.path.remove(script_dir)