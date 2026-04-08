from tkinter import filedialog
import tkinter as tk
import anchorpoint as ap
import apsync as aps
import os
import sys
import json

SYMLINK_DOCS_URL = "https://docs.anchorpoint.app/assets/utilities/symlinks/"

ctx = ap.get_context()
ui = ap.UI()


def is_developer_mode_enabled():
    if sys.platform != "win32":
        return True
    import winreg
    try:
        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\AppModelUnlock",
        )
        value, _ = winreg.QueryValueEx(
            key, "AllowDevelopmentWithoutDevLicense")
        winreg.CloseKey(key)
        return value == 1
    except OSError:
        return False


def find_git_root(path):
    """Walk up the directory tree to find the root .git folder."""
    current = path
    while True:
        git_dir = os.path.join(current, ".git")
        if os.path.isdir(git_dir):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            return None
        current = parent


def add_to_local_gitignore(link_path):
    """Add the symlink path to .git/info/exclude (local, not committed)."""
    git_root = find_git_root(os.path.dirname(link_path))
    if not git_root:
        print("No git repository found, skipping gitignore update")
        return

    exclude_path = os.path.join(git_root, ".git", "info", "exclude")
    rel_path = "/" + os.path.relpath(link_path, git_root).replace(os.sep, "/")

    content = ""
    if os.path.exists(exclude_path):
        with open(exclude_path, "r", encoding="utf-8") as f:
            content = f.read()

    if rel_path in content.splitlines():
        print(f"'{rel_path}' is already in .git/info/exclude")
        return

    with open(exclude_path, "a", encoding="utf-8") as f:
        if content and not content.endswith("\n"):
            f.write("\n")
        f.write(f"{rel_path}\n")

    print(f"Added '{rel_path}' to .git/info/exclude")


def _store_symlink_entry(source_abs, link_abs):
    """Store symlink entry in shared settings for project-wide management."""
    if not ctx.project_id:
        return

    project_path = ctx.project_path
    try:
        source_rel = os.path.relpath(
            source_abs, project_path).replace(os.sep, "/")
    except ValueError:
        source_rel = source_abs.replace(os.sep, "/")

    link_rel = os.path.relpath(link_abs, project_path).replace(os.sep, "/")

    settings = aps.SharedSettings(ctx.project_id, ctx.workspace_id, "symlinks")
    entries_json = settings.get("entries", "[]")
    entries = json.loads(entries_json)

    for entry in entries:
        if entry.get("source") == source_rel and entry.get("link") == link_rel:
            return

    entries.append({"source": source_rel, "link": link_rel})
    settings.set("entries", json.dumps(entries))
    settings.store()


if not is_developer_mode_enabled():
    ui.show_info(
        "Developer Mode Required",
        f'Creating symlinks requires Windows Developer Mode. Learn how to <a href="{SYMLINK_DOCS_URL}">enable this setting</a> on your computer.',
        duration=6000,
    )
    raise SystemExit()

root = tk.Tk()
root.withdraw()
root.attributes("-topmost", True)

source_folder = filedialog.askdirectory(
    title="Select Folder to Link",
    initialdir=ctx.path,
)

root.destroy()

if source_folder and os.path.isdir(source_folder):
    link_name = os.path.basename(source_folder.rstrip("/\\"))
    link_path = os.path.join(ctx.path, link_name)

    if os.path.exists(link_path) or os.path.islink(link_path):
        ui.show_error(
            "Already exists",
            f"A file or folder named '{link_name}' already exists in the current location.",
        )
    else:
        try:
            os.symlink(source_folder, link_path, target_is_directory=True)
            print(f"Created symlink: {link_path} -> {source_folder}")
            add_to_local_gitignore(link_path)
            _store_symlink_entry(source_folder, link_path)
            ui.reload()
            ui.show_success("Folder Link Created",
                            f"'{link_name}' has been linked successfully")
        except OSError as e:
            if hasattr(e, "winerror") and e.winerror == 1314:
                ui.show_error(
                    "Permission denied",
                    "Creating symbolic links requires Developer Mode or administrator privileges on Windows. "
                    "Enable Developer Mode in Windows Settings > Privacy & Security > For developers.",
                )
            else:
                ui.show_error("Failed to create symlink", str(e))
