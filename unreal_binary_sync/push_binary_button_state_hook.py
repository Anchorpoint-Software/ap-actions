import anchorpoint as ap
import apsync as aps


def on_is_action_enabled(path: str, type: ap.Type, ctx: ap.Context):

    local_settings = aps.Settings()
    button_enabled = local_settings.get(
        ctx.project_path+"_enable_binary_push", False)

    return button_enabled
