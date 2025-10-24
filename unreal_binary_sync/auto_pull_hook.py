import anchorpoint as ap
import apsync as aps
import pull_binaries


def on_event_received(id, payload, ctx: ap.Context):
    local_settings = aps.Settings()
    project_path = ctx.project_path
    enable_binary_pull = local_settings.get(
        project_path+"_enable_binary_auto_pull", False)

    if not enable_binary_pull:
        return

    if isinstance(payload, dict):
        payload = payload.get('type')

    if id == "gitpull" and payload == "success":
        pull_binaries.pull(ctx)
