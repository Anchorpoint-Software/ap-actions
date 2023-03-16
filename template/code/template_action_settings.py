from re import template
import anchorpoint as ap
import apsync as aps
import os, sys

sys.path.insert(0, os.path.dirname(__file__))
import template_utility

ctx = ap.get_context()
ui = ap.UI()

is_file_template = ctx.type == ap.Type.File or ctx.type == ap.Type.NewFile
settings = aps.SharedSettings(ctx.workspace_id, "AnchorpointTemplateSettings")
project = aps.get_project(ctx.path)

template_dir = os.path.join(ctx.yaml_dir, ctx.inputs["template_dir"])
template_dir = settings.get("template_dir", template_dir)

def get_tab_location(template_dir: str):
    if is_file_template:
        return os.path.join(template_dir, "file")  
    else:
        return os.path.join(template_dir, "folder")  

template_dir = get_tab_location(template_dir)

# Open the template directories in new tabs
has_project_templates = False
if project:
    project_templates_location = get_tab_location(template_utility.get_template_dir(project.path))
    if os.path.exists(project_templates_location):
        has_project_templates = True
        ui.open_tab(project_templates_location)

if os.path.exists(template_dir):
    if has_project_templates:
        ui.create_tab(template_dir)
    else:
        ui.open_tab(template_dir)
elif has_project_templates == False:
    ui.show_info("No templates installed", "Use \"Save as Template\" Action to create a new template")