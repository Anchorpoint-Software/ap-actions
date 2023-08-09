from shutil import copyfile
import anchorpoint as ap
import apsync as aps
import os

ctx = ap.get_context()
ui = ap.UI()

template_dir = os.path.join(ctx.yaml_dir, ctx.inputs["template_dir"]).replace("/", os.sep)
events_stub_dir =  os.path.join(ctx.yaml_dir, "code", "events.stub")

settings = aps.SharedSettings(ctx.workspace_id, "AnchorpointTemplateSettings")

def apply_callback(dialog : ap.Dialog):
    dir = dialog.get_value("callback_dir")
    if len(dir) > 0:
        target = os.path.join(dir, "template_action_events.py")
        if os.path.exists(target) == False:
            if os.path.exists(dir) == False:
                os.makedirs(dir)
            copyfile(events_stub_dir, target)
    
    dialog.store_settings()
    dialog.close()

# Create a dialog container
dialog = ap.Dialog()
dialog.title = "Template Action Settings"
dialog.icon = ctx.icon

dialog.add_text("Workspace Templates Location")
dialog.add_input(template_dir, browse=ap.BrowseType.Folder, var="template_dir")
dialog.add_info("Set a location that your team can access, such as a folder in your Dropbox")

dialog.add_empty()

dialog.add_text("Workspace Event Callbacks Location")
dialog.add_input(placeholder="Optional", browse=ap.BrowseType.Folder, var="callback_dir")
dialog.add_info("Use event callbacks to customize templates according to your needs<br>For projects, place event callbacks here: <b>project/anchorpoint/templates/template_action_events.py</b>")

dialog.add_button("Apply", callback = apply_callback)

# Present the dialog to the user
dialog.show(settings, store_settings_on_close=False)

