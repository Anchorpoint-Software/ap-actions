import anchorpoint as ap
import apsync as aps
import inc_publish

ctx = ap.get_context()
project_id = ctx.project_id
workspace_id = ctx.workspace_id
shared_settings = aps.SharedSettings(
    project_id, workspace_id, "inc_settings")
create_master = shared_settings.get("create_master_file", True)


def trigger_publish(msg, path, type):
    if create_master:
        progress = ap.Progress("Publishing File", "Creating Master File...")
    else:
        progress = ap.Progress("Publishing File", "Please wait...")
    publish_process = inc_publish.publish_file(msg, path, type)
    ui = ap.UI()
    if publish_process:
        ui.show_success("Publish Successful",
                        "The file has been added to the timeline",)
    else:
        ui.show_error("Cannot publish the file",
                      "An error occurred during publishing")
    progress.finish()


def button_callback(dialog):
    comment = dialog.get_value("comment")
    ctx.run_async(trigger_publish, comment, ctx.path, "")
    dialog.close()


def main():
    dialog = ap.Dialog()
    dialog.title = "Publish to Timeline"
    if ctx.icon:
        dialog.icon = ctx.icon
    dialog.add_input(
        var="comment",
        placeholder="Add a comment to this version",
        width=400,
    )
    if create_master:
        dialog.add_info(
            "Creates a timeline entry for this file and a master file")
    else:
        dialog.add_info(
            "Creates a timeline entry for this file and a master file"
        )
    dialog.add_button("Create File", callback=button_callback)
    dialog.show()


main()
