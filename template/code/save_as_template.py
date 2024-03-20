import anchorpoint as ap
import apsync as aps
import os

import template_utility
from template_settings import get_workspace_template_dir, get_callback_location

ctx = ap.get_context()
ui = ap.UI()

template_dir = ctx.inputs["template_dir"]
template_dir = os.path.join(ctx.yaml_dir, template_dir)
is_file_template = ctx.type == ap.Type.File or ctx.type == ap.Type.NewFile
source = ctx.path

settings = aps.SharedSettings(ctx.workspace_id, "AnchorpointTemplateSettings")
template_dir = get_workspace_template_dir(settings, template_dir)
callback_file = get_callback_location(settings, template_dir)

project = aps.get_project(source)
if project:
    project_templates_location = template_utility.get_template_dir(project.path)
    project_callbacks = template_utility.get_template_callbacks(
        project_templates_location
    )
    if os.path.exists(project_callbacks):
        callback_file = project_callbacks

if os.path.exists(callback_file):
    callbacks = aps.import_local(os.path.splitext(callback_file)[0], True)
else:
    callbacks = None


def get_template_dir(save_in_project: bool):
    if project and save_in_project:
        return project_templates_location
    return template_dir


def get_target(name: str, save_in_project: bool):
    if is_file_template:
        return f"{get_template_dir(save_in_project)}/file/{name}/{os.path.basename(source)}"
    return (
        f"{get_template_dir(save_in_project)}/folder/{name}/{os.path.basename(source)}"
    )


def create_template_async(name, source, target, ctx):
    try:
        progress = ap.Progress("Create Template", "Copying Files", infinite=True)
        if is_file_template is False:
            if aps.is_project(source, True):
                ui.show_info(
                    "Could not create template",
                    "The folder contains a project. This is not yet supported, unfortunately.",
                )
                dialog.close()
                return

            os.makedirs(target)
            aps.copy_folder(source, target, workspace_id=ctx.workspace_id)
            if callbacks and "folder_template_saved" in dir(callbacks):
                callbacks.folder_template_saved(name, target)
        else:
            os.makedirs(os.path.dirname(target))
            aps.copy_file(source, target, workspace_id=ctx.workspace_id)
            if callbacks and "file_template_saved" in dir(callbacks):
                callbacks.file_template_saved(name, target)

        ui.create_tab(os.path.dirname(target))

        ui.show_success("Template created")
    except:
        ui.show_error("Failed to create template")


def create_template(dialog: ap.Dialog):
    name = dialog.get_value("name")
    save_in_project = dialog.get_value("project")
    target = get_target(name, save_in_project)
    ctx.run_async(create_template_async, name, source, target, ctx)
    dialog.close()


def validate_input(name: str, target: str):
    if len(name) == 0:
        return False
    if os.path.exists(target):
        return False
    if os.path.exists(os.path.dirname(target)):
        return False
    if "." in name:
        return False
    return True


def name_changed(dialog: ap.Dialog, name):
    save_in_project = dialog.get_value("project")
    target = get_target(name, save_in_project)
    is_valid_input = validate_input(name, target)
    dialog.set_enabled("button", is_valid_input)


def project_check_changed(dialog: ap.Dialog, save_in_project):
    name = dialog.get_value("name")
    target = get_target(name, save_in_project)
    is_valid_input = validate_input(name, target)
    dialog.set_enabled("button", is_valid_input)


dialog = ap.Dialog()
dialog.icon = ctx.icon

if not is_file_template:
    dialog.title = "Save Folder as Template"
else:
    dialog.title = "Save File as Template"

dialog.add_text("Name:").add_input(
    placeholder="Character Template", var="name", callback=name_changed
)
dialog.add_info(
    "Your template will appear in a <b>new tab.</b> <br> Templates are accessible from the <b>New</b> context menu. <br> <a href='https://www.anchorpoint.app/blog/automate-folder-structures-and-naming-conventions-without-writing-code'>Learn more about templates</a>"
)

if project:
    dialog.add_separator()
    project_dir = os.path.split(project.path)[1]
    dialog.add_checkbox(
        True, var="project", callback=project_check_changed, text="Save in Project"
    )
    dialog.add_info(
        f"Project templates are stored here:<br><b>{project_dir}</b>/anchorpoint/templates"
    )

dialog.add_button(
    "Create Template", callback=create_template, enabled=False, var="button"
)

dialog.show()
