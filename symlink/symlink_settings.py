import anchorpoint as ap
import apsync as aps
import os
import json


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
    rel_path = os.path.relpath(link_path, git_root).replace(os.sep, "/")

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


class SymlinkSettings(ap.AnchorpointSettings):
    def __init__(self, ctx):
        super().__init__()
        self.ctx = ctx
        self.project_path = ctx.project_path
        self.settings = aps.SharedSettings(
            ctx.project_id, ctx.workspace_id, "symlinks")
        self.dialog = ap.Dialog()
        self._build_dialog()

    def _get_entries(self):
        entries_json = self.settings.get("entries", "[]")
        return json.loads(entries_json)

    def _build_dialog(self):
        entries = self._get_entries()

        if not entries:
            self.dialog.add_info(
                "No symlinks configured yet. Use the <b>Folder Link</b> action<br>"
                "in the New Folder menu to create symlinks."
            )
            return

        self.dialog.add_info(
            "Manage folder symlinks for this project. Symlinks that exist<br>"
            "on disk are marked with ✔."
        )

        for i, entry in enumerate(entries):
            source = entry.get("source", "")
            link = entry.get("link", "")
            link_abs = os.path.join(self.project_path, link)
            exists = os.path.islink(link_abs)

            # Row for when symlink does NOT exist: text + Create button
            self.dialog.add_text(
                f"{source} → {link}", var=f"missing_{i}", width=400
            ).add_button(
                "Create",
                callback=lambda d, s=source, l=link, idx=i: self._create_symlink(
                    d, s, l, idx),
                var=f"create_{i}",
                primary=True,
            )

            # Row for when symlink EXISTS: text + Remove button
            self.dialog.add_text(
                f"✔ {source} → {link}", var=f"exists_{i}", width=400
            ).add_button(
                "Remove",
                callback=lambda d, s=source, l=link, rv=i: self._remove_symlink(
                    d, s, l, rv),
                var=f"remove_{i}",
                primary=False,
            )

            if exists:
                self.dialog.hide_row(f"missing_{i}", True)
            else:
                self.dialog.hide_row(f"exists_{i}", True)

    def _create_symlink(self, dialog, source, link, idx):
        source_abs = os.path.join(self.project_path, source)
        link_abs = os.path.join(self.project_path, link)

        if not os.path.isdir(source_abs):
            self._show_browse_dialog(source, link, idx, dialog)
            return

        self._do_create_symlink(dialog, source_abs, link_abs, source, link, idx)

    def _show_browse_dialog(self, source, link, idx, settings_dialog):
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)

        new_source_abs = filedialog.askdirectory(
            title="Locate Source Folder",
            initialdir=self.project_path,
        )

        root.destroy()

        if not new_source_abs or not os.path.isdir(new_source_abs):
            return

        link_abs = os.path.join(self.project_path, link)

        try:
            new_source_rel = os.path.relpath(new_source_abs, self.project_path).replace(os.sep, "/")
        except ValueError:
            new_source_rel = None

        # Update the settings entry with the new source path
        if new_source_rel:
            entries = self._get_entries()
            for entry in entries:
                if entry.get("source") == source and entry.get("link") == link:
                    entry["source"] = new_source_rel
                    break
            self.settings.set("entries", json.dumps(entries))
            self.settings.store()

        self._do_create_symlink(settings_dialog, new_source_abs, link_abs, new_source_rel or source, link, idx)

    def _do_create_symlink(self, dialog, source_abs, link_abs, source, link, idx):
        if os.path.exists(link_abs) or os.path.islink(link_abs):
            ap.UI().show_error("Already exists",
                               f"A file or folder already exists at:\n{link_abs}")
            return

        os.makedirs(os.path.dirname(link_abs), exist_ok=True)

        try:
            os.symlink(source_abs, link_abs, target_is_directory=True)
            print(f"Created symlink: {link_abs} -> {source_abs}")
        except OSError as e:
            if hasattr(e, "winerror") and e.winerror == 1314:
                ap.UI().show_error(
                    "Permission denied",
                    "Creating symbolic links requires Developer Mode or administrator "
                    "privileges on Windows.",
                )
            else:
                ap.UI().show_error("Failed to create symlink", str(e))
            return

        add_to_local_gitignore(link_abs)
        dialog.hide_row(f"missing_{idx}", True)
        dialog.hide_row(f"exists_{idx}", False)
        ap.UI().show_success("Symlink Created",
                             f"'{link}' has been linked successfully")

    def _remove_symlink(self, dialog, source, link, idx):
        link_abs = os.path.join(self.project_path, link)

        if os.path.islink(link_abs):
            try:
                os.remove(link_abs)
                print(f"Removed symlink: {link_abs}")
            except OSError as e:
                ap.UI().show_error("Failed to remove symlink", str(e))
                return

        # Remove matching entry from settings
        entries = self._get_entries()
        entries = [e for e in entries if not (
            e.get("source") == source and e.get("link") == link)]
        self.settings.set("entries", json.dumps(entries))
        self.settings.store()

        dialog.hide_row(f"missing_{idx}", True)
        dialog.hide_row(f"exists_{idx}", True)
        ap.UI().show_success("Symlink Removed", f"'{link}' has been removed")

    def get_dialog(self):
        return self.dialog


def on_show_project_preferences(settings_list, ctx):
    if not ctx.project_id:
        return

    settings = SymlinkSettings(ctx)
    settings.name = "Symlinks"
    settings.priority = 50
    settings.icon = os.path.join(os.path.dirname(__file__), "symlink.svg")
    settings_list.add(settings)
