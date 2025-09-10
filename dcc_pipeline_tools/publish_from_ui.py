import anchorpoint as ap
import apsync as aps
# Import the publish class, that is also triggered from the DCC plugins
import publish

# Summary
# This action is triggered from the right click context menu on a file.
# The purpose is to allow to publish files that don't have a plugin yet

ctx = ap.get_context()
project_id = ctx.project_id
workspace_id = ctx.workspace_id
shared_settings = aps.SharedSettings(
    project_id, workspace_id, "inc_settings")
create_master = shared_settings.get("create_master_file", True)

# send the data to the publish class that creates the timeline entry


def trigger_publish(msg, path, type, post_process_object):
    progress = ap.Progress("Publishing File", "Please wait...")
    publish_process = publish.publish_file(
        msg, path, type, post_process_object)
    ui = ap.UI()
    if publish_process:
        ui.show_success("Publish Successful",
                        "The file has been added to the timeline",)
    else:
        ui.show_error("Cannot publish the file",
                      "An error occurred during publishing")
    progress.finish()

# The function that is triggered when the user clicks on the button


def button_callback(dialog):
    post_process_object = {"create_master": dialog.get_value("create_master")}
    comment = dialog.get_value("comment")
    # Run the publish process async because it could take a while
    ctx.run_async(trigger_publish, comment, ctx.path, "", post_process_object)
    dialog.close()


def main():
    # Create the dialog
    dialog = ap.Dialog()
    dialog.title = "Publish to Timeline"
    if ctx.icon:
        dialog.icon = ctx.icon
    dialog.add_input(
        var="comment",
        placeholder="Add a comment to this version",
        width=400,
    )
    dialog.add_info(
        "Creates a timeline entry for this file")
    dialog.add_checkbox(
        create_master, text="Create Master File", var="create_master")
    dialog.add_info(
        "This will create a file without increments in the file name")
    dialog.add_button("Publish", callback=button_callback)
    dialog.show()


main()
