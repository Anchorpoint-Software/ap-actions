from shutil import copyfile
import anchorpoint as ap
import apsync as aps
import os

ctx = ap.Context.instance()
ui = ap.UI()

template_dir = os.path.join(ctx.yaml_dir, ctx.inputs["template_dir"])
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
dialog.icon = ":/icons/settings.svg"

dialog.add_text("Templates Location")
dialog.add_input(template_dir, browse=ap.BrowseType.Folder, var="template_dir")
dialog.add_text("Event Callbacks Location")
dialog.add_input(browse=ap.BrowseType.Folder, var="callback_dir")

dialog.add_button("Apply", callback = apply_callback)

# Present the dialog to the user
dialog.show(settings, store_settings_on_close=False)

