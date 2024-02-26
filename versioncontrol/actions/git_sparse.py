import anchorpoint as ap
import apsync as aps
import os
import time
import webbrowser
import sys
import git_repository_helper as helper

current_dir = os.path.dirname(__file__)
script_dir = os.path.join(os.path.dirname(__file__), "..")

sys.path.insert(0, script_dir)

from vc.apgit.repository import GitRepository

if script_dir in sys.path:
    sys.path.remove(script_dir)


def disable_sparse_checkout(dialog, ctx):
    settings = aps.Settings("sparse_checkout_dialog_seen")
    settings.set(ctx.project_id, True)
    settings.store()
    dialog.close()
    ctx.run_async(on_download_remote_folder, "", ctx)


def navigate_to_pricing(dialog, ctx):
    settings = aps.Settings("sparse_checkout_dialog_seen")
    settings.set(ctx.project_id, True)
    settings.store()
    webbrowser.open("https://www.anchorpoint.app/pricing")
    dialog.close()


def show_sparse_checkout_feature_dialog(ctx):
    settings = aps.Settings("sparse_checkout_dialog_seen")
    already_seen = settings.get(ctx.project_id, False)
    if already_seen:
        return

    dialog = ap.Dialog()
    dialog.title = "Download feature required"
    dialog.icon = ctx.icon
    dialog.add_info(
        "You are using partial folder download in this project.<br>This feature is only available in the Team plan of Anchorpoint.<br>Please upgrade your plan or disable the feature."
    )
    dialog.add_button(
        "Disable", callback=lambda d: disable_sparse_checkout(d, ctx)
    ).add_button("Upgrade", callback=lambda d: navigate_to_pricing(d, ctx))
    dialog.show()


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
                if "/".join(path_parts[: i + 1]) in sparse_checkout_set:
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
            if "is not sparse" in str(e):
                entry = ap.RemoteFolderEntry()
                entry.path = ""
                entry.is_remote = False
                entry.is_download_root = True
                tree_entries.append(entry)
                has_root_added = True

        has_any_remote_folders = False

        if len(sparse_checkout_set) > 0 and not ctx.has_team_features():
            show_sparse_checkout_feature_dialog(ctx)

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

        git_errors.handle_error(e, ctx.project_path)
        raise e
    finally:
        if script_dir in sys.path:
            sys.path.remove(script_dir)


def on_download_remote_folder(relative_folder_path: str, ctx):
    try:
        import sys

        sys.path.insert(0, script_dir)
        from vc.apgit.repository import GitRepository

        progress = ap.Progress("Downloading", show_loading_screen=True, cancelable=True)

        if ctx.project_path is None:
            raise Exception("project_path is None")

        repo = GitRepository.load(ctx.project_path)
        needed_download = repo.sparse_checkout_folder(
            relative_folder_path, progress=helper.SparseProgress(progress)
        )
        if needed_download:
            ap.evaluate_locks(ctx.workspace_id, ctx.project_id)
            ui = ap.UI()
            ui.reload_tree()
            time.sleep(2)
            ui.reload()
        progress.finish()
        if not needed_download:
            ui = ap.UI()
            ui.show_info(
                title="No remote repository available",
                duration=5000,
                description="Selective download / unload only works in combination with a remote repository.",
            )

        return True

    except Exception as e:
        import git_errors

        git_errors.handle_error(e, ctx.project_path)
        raise e
    finally:
        if script_dir in sys.path:
            sys.path.remove(script_dir)


def continue_unload(dialog, ctx, relative_folder_path):
    dialog.close()
    ctx.run_async(unload_remote_folder, relative_folder_path, True, ctx)


def show_unload_warning_dialog(relative_folder_path, ignored_files_in_folder, ctx):
    dialog = ap.Dialog()

    dialog.title = "Ignored Files"
    dialog.icon = ctx.icon

    dialog.add_text(
        "The folder you are unloading contains ignored files.<br>If you continue, these files will be <b>permamently deleted</b>."
    )
    dialog.add_info(f"Example: <b>{ignored_files_in_folder[0]}</b>")
    dialog.add_button(
        "Unload and Delete",
        var="continue",
        callback=lambda d: continue_unload(d, ctx, relative_folder_path),
        primary=False,
    ).add_button("Cancel", var="cancel", callback=lambda d: d.close(), primary=False)

    dialog.show()


def unload_remote_folder(relative_folder_path: str, forced: bool, ctx):
    try:
        import sys

        sys.path.insert(0, script_dir)
        from vc.apgit.repository import GitRepository

        progress = ap.Progress("Unloading", show_loading_screen=True, cancelable=False)

        if ctx.project_path is None:
            raise Exception("project_path is None")

        repo = GitRepository.load(ctx.project_path)

        if repo.is_unborn():
            progress.finish()
            ui = ap.UI()
            ui.show_info(
                title="Cannot unload folder",
                duration=5000,
                description="This repository is not initialized.",
            )
            return True

        if not forced:
            ignore_check_path = relative_folder_path
            if ignore_check_path == "":
                ignore_check_path = "."
            ignored_files_in_folder = repo.get_ignored_files([ignore_check_path])
            if len(ignored_files_in_folder) > 0:
                progress.finish()
                show_unload_warning_dialog(
                    relative_folder_path, ignored_files_in_folder, ctx
                )
                return False

        needed_unload = repo.sparse_unload_folder(relative_folder_path)
        if needed_unload:
            ui = ap.UI()
            ui.reload_tree()
            time.sleep(2)
            ui.reload()
        progress.finish()
        if not needed_unload:
            ui = ap.UI()
            ui.show_info(
                title="No remote repository available",
                duration=5000,
                description="Selective download / unload only works in combination with a remote repository.",
            )

        return True

    except Exception as e:
        import git_errors

        if not git_errors.handle_error(e, ctx.project_path):
            message = str(e)
            if "it contains uncommitted changes" in message:
                print("Failed to unload folder because it contains uncommitted changes")
                ui = ap.UI()
                ui.show_info(
                    title="Cannot unload folder",
                    duration=5000,
                    description="This folder contains changed files. Commit them first.",
                )
                ui.navigate_to_channel_detail("Git", "vcPendingChanges")
            elif "Cannot unload root when it is the only sparse root" in message:
                ui = ap.UI()
                ui.show_info(
                    title="Cannot unload folder",
                    duration=5000,
                    description="The root folder is already unloaded.",
                )
            else:
                raise e
        return False
    finally:
        if script_dir in sys.path:
            sys.path.remove(script_dir)


def on_unload_remote_folder(relative_folder_path: str, ctx):
    return unload_remote_folder(relative_folder_path, False, ctx)
