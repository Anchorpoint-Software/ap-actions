import anchorpoint as ap
import apsync as aps
import pull_binaries

# This is not using Git hooks but Anchorpoint's event system to listen for Git pull events


def on_event_received(id, payload, ctx: ap.Context):
    local_settings = aps.Settings()
    project_path = ctx.project_path
    enable_binary_pull = local_settings.get(
        project_path+"_enable_binary_auto_pull", False)

    if not enable_binary_pull:
        return

    # payload looks like this: {'type': 'success'}

    if isinstance(payload, dict):
        payload = payload.get('type')

    # trigger on pull
    if id == "gitpull" and payload == "success":
        pull_binaries.pull(ctx)
    # trigger on merge
    if id == "gitmergebranch" and payload == "success":
        pull_binaries.pull(ctx)
    # trigger on switch branch
    if id == "gitswitchbranch" and payload == "success":
        pull_binaries.pull(ctx)
