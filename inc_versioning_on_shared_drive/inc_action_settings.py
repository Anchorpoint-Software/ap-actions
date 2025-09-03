import anchorpoint as ap
import apsync as aps
import os

ctx = ap.get_context()
ui = ap.UI()
settings = aps.SharedSettings(ctx.workspace_id, "inc_workspace_settings")


def apply_callback(dialog):
    template_dir_win = dialog.get_value("template_dir_win")
    template_dir_mac = dialog.get_value("template_dir_mac")
    webhook_url = dialog.get_value("webhook_url")

    # Check if the directories are valid or empty
    if (template_dir_win and not os.path.isdir(template_dir_win)) or (template_dir_mac and not os.path.isdir(template_dir_mac)):
        ui.show_error("One of the folders does not exist",
                      "Add an existing folder or leave it empty")
        return  # Exit the function if the paths are invalid

    settings.set("template_dir_win", template_dir_win)
    settings.set("template_dir_mac", template_dir_mac)
    settings.set("webhook_url", webhook_url)
    settings.store()
    dialog.close()
    ap.UI().show_success("Settings applied")


def main():
    # Create a dialog container
    dialog = ap.Dialog()
    dialog.title = "Template Settings"
    template_dir_win = settings.get("template_dir")
    template_dir_mac = settings.get("template_dir_mac")

    dialog.add_text("<b>Workspace Templates Location</b>")
    dialog.add_text("Windows", width=70).add_input(
        template_dir_win, browse=ap.BrowseType.Folder, var="template_dir_win", width=400, placeholder="C:/Projects/Templates"
    )
    dialog.add_text("macOS", width=70).add_input(
        template_dir_mac, browse=ap.BrowseType.Folder, var="template_dir_mac", width=400, placeholder="/Users/John/Templates"
    )
    dialog.add_info(
        "Set a location that your team can access and that is the same for all Windows and macOS users"
    )
    dialog.add_text("<b>Webhook</b>")
    dialog.add_text("Url", width=70).add_input(
        settings.get("webhook_url", ""), var="webhook_url", width=400, placeholder="https://yourdomain.com/webhook"
    )
    dialog.add_info(
        "Optional: Set a webhook URL to trigger an automation when a new version is published"
    )

    dialog.add_button("Apply", callback=apply_callback)

    # Present the dialog to the user
    dialog.show(settings, store_settings_on_close=False)


main()
