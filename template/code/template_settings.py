from shutil import copyfile
import anchorpoint as ap
import apsync as aps
import os
import platform

ctx = ap.get_context()
ui = ap.UI()


def _get_workspace_template_dir_impl(template_dir_win, template_dir_mac, fallback):
    if os.path.exists(template_dir_win) and template_dir_win != fallback:
        return template_dir_win

    if platform.system() == "Darwin":
        return template_dir_mac

    return fallback


def get_workspace_template_dir(settings, fallback):
    template_dir_win = settings.get("template_dir", fallback)
    template_dir_mac = settings.get("template_dir_mac", fallback)
    return _get_workspace_template_dir_impl(
        template_dir_win, template_dir_mac, fallback
    )


def _get_callback_location_impl(callback_dir, template_dir):
    if len(callback_dir) == 0:
        return ""

    if os.path.isabs(callback_dir):
        return os.path.join(callback_dir, "template_action_events.py")
    else:
        return os.path.join(template_dir, callback_dir, "template_action_events.py")


def get_callback_location(settings, template_dir):
    callback_dir = settings.get("callback_dir", "")
    return _get_callback_location_impl(callback_dir, template_dir)


template_dir = os.path.join(ctx.yaml_dir, ctx.inputs["template_dir"]).replace(
    "/", os.sep
)
events_stub_dir = os.path.join(ctx.yaml_dir, "code", "events.stub")

settings = aps.SharedSettings(ctx.workspace_id, "AnchorpointTemplateSettings")


def apply_callback(dialog: ap.Dialog):
    dir = dialog.get_value("callback_dir")
    template_dir_win = dialog.get_value("template_dir")
    template_dir_mac = dialog.get_value("template_dir_mac")

    template_dir = _get_workspace_template_dir_impl(
        template_dir_win, template_dir_mac, template_dir_win
    )
    callback_file = _get_callback_location_impl(dir, template_dir)
    if callback_file and len(callback_file) > 0:
        if os.path.exists(callback_file) is False:
            callback_dir = os.path.dirname(callback_file)
            if os.path.exists(callback_dir) is False:
                os.makedirs(callback_dir)
            copyfile(events_stub_dir, callback_file)

    dialog.store_settings()
    dialog.close()


# Create a dialog container
dialog = ap.Dialog()
dialog.title = "Template Action Settings"
dialog.icon = ctx.icon

dialog.add_text("Workspace Templates Location")
dialog.add_text("Windows\t").add_input(
    template_dir, browse=ap.BrowseType.Folder, var="template_dir", width=400
)
dialog.add_text("macOS\t").add_input(
    template_dir, browse=ap.BrowseType.Folder, var="template_dir_mac", width=400
)
dialog.add_info(
    "Set a location that your team can access, such as a folder in your Dropbox"
)

dialog.add_empty()

dialog.add_text("Workspace Event Callbacks Location")
dialog.add_input(
    placeholder="Optional", browse=ap.BrowseType.Folder, var="callback_dir"
)
dialog.add_info(
    "Use event callbacks to customize templates according to your needs. Can be a relative path.<br>For projects, place event callbacks here: <b>project/anchorpoint/templates/template_action_events.py</b>"
)

dialog.add_button("Apply", callback=apply_callback)

# Present the dialog to the user
dialog.show(settings, store_settings_on_close=False)
