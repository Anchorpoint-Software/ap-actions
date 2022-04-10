from shutil import copyfile
import anchorpoint as ap
import apsync as aps
import os

ctx = ap.Context.instance()
ui = ap.UI()

template_dir = os.path.join(ctx.yaml_dir, ctx.inputs["template_dir"])
callback_stub_dir =  os.path.join(ctx.yaml_dir, "code", "callback_stubs.py")

settings = aps.SharedSettings(ctx.workspace_id, "AnchorpointTemplateSettings")

def create_callbacks(dialog : ap.Dialog):
    dir = dialog.get_value("callback_dir")
    if len(dir) > 0:
        target = os.path.join(dir, "template_action_callbacks.py")
        if os.path.exists(target) == False:
            if os.path.exists(dir) == False:
                os.makedirs(dir)
            copyfile(callback_stub_dir, target)
    pass

# Create a dialog container
dialog = ap.Dialog()
dialog.title = "Template Action Settings"
dialog.icon = ":/icons/settings.svg"

dialog.add_text("Templates Location")
dialog.add_input(template_dir, browse=ap.BrowseType.Folder, var="template_dir")
dialog.add_text("Callbacks Location")
dialog.add_input(browse=ap.BrowseType.Folder, var="callback_dir")

dialog.callback_closed = create_callbacks

# Present the dialog to the user
dialog.show(settings)

