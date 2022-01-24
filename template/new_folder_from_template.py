import anchorpoint as ap
import apsync as aps
import os

ctx = ap.Context.instance()
ui = ap.UI()

username = ctx.username
folder = ctx.path

dialog_preview_var = "preview"
dialog_template_var = "template"
dialog_type_var = "type"
dialog_name_var = "name"

resolved_vars = []

import sys

sys.path.insert(0, ctx.yaml_dir)
import template_utility


def map_variable_type(variable_type_str):
    if variable_type_str == "Name":
        return template_utility.VariableType.NAME
    if variable_type_str == "Date of Today":
        return template_utility.VariableType.DATE
    if variable_type_str == "User Initials":
        return template_utility.VariableType.USER
    if variable_type_str == "Increment":
        return template_utility.VariableType.INCREMENT
    return template_utility.VariableType.NAME


def resolve_variables(path, resolved_vars):
    for var in resolved_vars:
        path = path.replace("$", var, 1)

    return path


def resolve_dialog_variables(dialog, template):
    variable = 0
    global resolved_vars
    resolved_vars.clear()

    while True:
        if "$" not in template:
            break

        type = dialog.get_value(dialog_type_var + str(variable))
        var_name = dialog.get_value(dialog_name_var + str(variable))
        resolved_var = template_utility.resolve_variable(
            template, map_variable_type(type), folder, var_name, username
        )
        template = template.replace("$", resolved_var, 1)
        variable = variable + 1
        resolved_vars.append(resolved_var)

    return template


def update_preview(dialog):
    template = dialog.get_value(dialog_template_var)
    template = resolve_dialog_variables(dialog, template)
    dialog.set_value(dialog_preview_var, template)


def dropdown_changed(variable, dialog, value):
    dialog.set_enabled(dialog_name_var + str(variable), value == "Name")
    update_preview(dialog)


def name_changed(dialog, value):
    update_preview(dialog)


def rename_folder_entries(dialog, target):
    for root, _, files in os.walk(target):
        if root != target:
            resolved = resolve_variables(root, resolved_vars)
            if resolved != root:
                aps.rename_folder(root, resolved)

        for file in files:
            resolved = resolve_variables(file, resolved_vars)
            if resolved != file:
                aps.rename_file(
                    os.path.join(root, file), os.path.join(root, resolved)
                )


def store_settings(dialog):
    settings = aps.Settings()
    variable = 0
    while True:
        type = dialog.get_value(dialog_type_var + str(variable))
        var_name = dialog.get_value(dialog_name_var + str(variable))

        print(type)
        print(var_name)

        if type == None and var_name == None:
            break

        if type:
            settings.set(f"{folder}_{dialog_type_var}{variable}", type)

        if var_name:
            settings.set(f"{folder}_{dialog_name_var}{variable}", var_name)

        variable = variable + 1

    settings.store()

def copy_folder(dialog, folder, preview, source):
    try:
        store_settings(dialog)
        target = os.path.join(folder, preview)
        aps.copy_folder(source, target)
        rename_folder_entries(dialog, target)
        template_utility.remove_gitkeep(target)
    except Exception as e:
        ui.show_error("Could not create Folder", str(e))
    else:
        ui.show_success("folder copied")

def button_pressed(dialog, source):
    preview = dialog.get_value(dialog_preview_var)
    ctx.run_async(copy_folder, dialog, folder, preview, source)
    dialog.close()


def create_copy_dialog(variable_count, template_folders):
    settings = aps.Settings()

    dialog = ap.Dialog()
    dialog.title = "New Folder from Template"
    if ctx.icon:
        dialog.icon = ctx.icon
    if ctx.icon_color:
        dialog.icon_color = ctx.icon_color

    dialog.add_text("Template:\t").add_input(
        os.path.basename(template_folders), enabled=False, var=dialog_template_var
    )
    dialog.add_text("Preview:\t").add_input(
        "Test", enabled=False, var=dialog_preview_var
    )
    dialog.add_separator()

    for variable in range(variable_count):
        type = settings.get(
            f"{folder}_{dialog_type_var}{variable}",
            "Date of Today" if variable == 0 else "Name",
        )
        input = settings.get(f"{folder}_{dialog_name_var}{variable}", "")

        dialog.start_section(f"variable {variable+1}", foldable=False)

        dialog.add_dropdown(
            type,
            ["Increment", "Date of Today", "User Initials", "Name"],
            var=dialog_type_var + str(variable),
            callback=lambda d, v, var=variable: dropdown_changed(var, d, v),
        )
        dialog.add_input(
            input,
            enabled=type == "Name",
            var=dialog_name_var + str(variable),
            callback=name_changed,
        )
        dialog.end_section()

    dialog.add_button(
        "Create Folder", callback=lambda d, src=template_folders: button_pressed(d, src)
    )

    update_preview(dialog)
    return dialog


def get_variables_count(template_folders):
    return template_folders.count("$")


def check_folder_conflict(folder):
    if os.path.exists(folder):
        ui.show_error("could not create folder", f"target {folder} already exists")
        return True
    return False


def copy_folder_no_variables(template_folders, target_folder):
    if check_folder_conflict(target_folder):
        return

    try:
        aps.copy_folder(template_folders, target_folder)
        template_utility.remove_gitkeep(target_folder)
    except Exception as e:
        ui.show_error("could not copy folder", str(e))

def copy_folder_with_variables(variable_count, template_folders, target_folder):
    dialog = create_copy_dialog(variable_count, template_folders)
    if dialog:
        dialog.show()


def copy_folder(template_folder, target_folder):
    if not os.path.exists(template_folder):
        ui.show_error("could not create folder", "template_folder does not exist")
        return False

    variable_count = get_variables_count(template_folder)
    if variable_count == 0:
        ctx.run_async(copy_folder_no_variables, template_folder, target_folder)
        return

    copy_folder_with_variables(variable_count, template_folder, target_folder)


if "template_folder" not in ctx.inputs or len(ctx.inputs["template_folder"]) == 0:
    ui.show_error("template_folders not set", f"Please adapt {ctx.yaml}", duration=6000)
else:
    template_folder = ctx.inputs["template_folder"]
    if not os.path.exists(template_folder):
        template_folder = os.path.join(ctx.yaml_dir, template_folder)

    copy_folder(
        template_folder, os.path.join(folder, os.path.basename(template_folder))
    )
