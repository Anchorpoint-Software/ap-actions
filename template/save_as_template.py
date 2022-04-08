import anchorpoint as ap
import apsync as aps
import os

ctx = ap.Context.instance()
ui = ap.UI()

template_dir = ctx.inputs["template_dir"]
template_dir = os.path.join(ctx.yaml_dir, template_dir)
is_file_template = ctx.type == ap.Type.File
source = ctx.path

def get_target(name: str):
    if is_file_template: return f"{template_dir}/file/{name}/{os.path.basename(source)}"
    return f"{template_dir}/folder/{name}/{os.path.basename(source)}"
    
def create_template(dialog: ap.Dialog):
    name = dialog.get_value("name")
    target = get_target(name)
    try:
        print(target)
        if is_file_template == False:
            if aps.is_project(source, True):
                ui.show_info("Could not create template", "The folder contains a project. This is not yet supported, unfortunately.")
                dialog.close()
                return
                
            os.makedirs(target)
            aps.copy_folder(source, target)
        else:
            os.makedirs(os.path.dirname(target))
            aps.copy_file(source, target)

        ui.show_success("Template created")
    except:
        ui.show_error("Failed to create template")
    
    dialog.close()
    
def name_changed(dialog: ap.Dialog, name):
    target = get_target(name)
    is_valid_input = len(name) > 0 and os.path.exists(target) == False and os.path.exists(os.path.dirname(target)) == False
    dialog.set_enabled("button", is_valid_input)

dialog = ap.Dialog()
dialog.icon = ctx.icon

if not is_file_template:
    dialog.title = "Save Folder as Template"
else:
    dialog.title = "Save File as Template"

dialog.add_text("Name:\t").add_input(placeholder = "Your Template Name", var="name", callback=name_changed)
dialog.add_button("Create Template", callback=create_template, enabled=False, var="button")

dialog.show()