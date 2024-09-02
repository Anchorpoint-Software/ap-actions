import apsync
import anchorpoint

ctx = anchorpoint.get_context()

# Optional
project = apsync.get_project_by_id(ctx.project_id, ctx.workspace_id)

users = apsync.get_users(ctx.workspace_id, project)
for u in users:
    print(u.name)
    print(u.email)
    print(u.id)
    print(u.picture_url)

anchorpoint.UI().show_console()