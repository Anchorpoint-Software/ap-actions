import anchorpoint as ap
import apsync as aps
import os
import json
from symlink_settings import find_git_root, add_to_local_gitignore


def on_event_received(id, payload, ctx: ap.Context):
    if isinstance(payload, dict):
        payload = payload.get("type")

    if id != "gitclone" or payload != "success":
        return

    if not ctx.project_id:
        return

    project_path = ctx.project_path
    settings = aps.SharedSettings(ctx.project_id, ctx.workspace_id, "symlinks")
    entries_json = settings.get("entries", "[]")
    entries = json.loads(entries_json)

    if not entries:
        return

    created = 0
    skipped = 0

    for entry in entries:
        source = entry.get("source", "")
        link = entry.get("link", "")

        source_abs = os.path.join(project_path, source)
        link_abs = os.path.join(project_path, link)

        if os.path.exists(link_abs) or os.path.islink(link_abs):
            print(f"Symlink already exists, skipping: {link}")
            skipped += 1
            continue

        if not os.path.isdir(source_abs):
            print(f"Source not available, skipping: {source}")
            skipped += 1
            continue

        os.makedirs(os.path.dirname(link_abs), exist_ok=True)

        try:
            os.symlink(source_abs, link_abs, target_is_directory=True)
            add_to_local_gitignore(link_abs)
            print(f"Created symlink: {link_abs} -> {source_abs}")
            created += 1
        except OSError as e:
            print(f"Failed to create symlink {link}: {e}")
            skipped += 1

    if created > 0:
        print(f"Symlinks: Created {created} symlink(s)" +
              (f", skipped {skipped}" if skipped > 0 else ""))
    elif skipped > 0:
        print(f"No symlinks created, {skipped} skipped")
