import anchorpoint as ap
import apsync as aps
import os
from datetime import date

ctx = ap.Context.instance()
api = ctx.create_api()
ui = ap.UI()

username = ctx.username
folder = ctx.path

dialog_preview_var = "preview"
dialog_template_var = "template"
dialog_type_var = "type"
dialog_name_var = "name"

def get_next_increment(template):
    increment = 10
    directories = [item for item in os.listdir(folder) if os.path.isdir(os.path.join(folder,item))]

    while True:
        name = template.replace("$", str(increment), 1)
        pos_var = name.find("$")
        substr = name if pos_var == -1 else name[:pos_var]
        
        if substr not in directories:
            return str(increment)

        increment = increment + 10

def resolve_one_variable(name, variable_type, var_name):
    replacement = ""
    if variable_type == "Name":
        replacement = var_name
    elif variable_type == "Date of Today":
        replacement = date.today().strftime("%y%m%d")
    elif variable_type == "User Initials":
        initials = username.split(" ")
        for initial in initials:
            replacement = replacement + initial[0].upper()
    elif variable_type == "Increment":
        replacement = get_next_increment(name)

    return name.replace("$", replacement, 1)
    
def resolve_variables(dialog, template):
    variable = 0
    while True:
        if "$" not in template:
            break

        type = dialog.get_value(dialog_type_var+str(variable))
        var_name = dialog.get_value(dialog_name_var+str(variable))
        template = resolve_one_variable(template, type, var_name)
        variable = variable + 1

    return template

def update_preview(dialog):
    template = dialog.get_value(dialog_template_var)
    template = resolve_variables(dialog, template)
    dialog.set_value(dialog_preview_var, template)
    

def dropdown_changed(variable, dialog, value):
    name_entry = dialog.get(dialog_name_var+str(variable))
    if name_entry:
        name_entry.enabled = value == "Name"
    update_preview(dialog)

def name_changed(dialog, value):
    update_preview(dialog)

def rename_folder_entries(dialog, target):
    for root, _, files in os.walk(target):
        if root != target:
            resolved = resolve_variables(dialog, root)
            if resolved != root: 
                aps.rename_folder(api, root, resolved)

        for file in files:
            resolved = resolve_variables(dialog, file)
            if resolved != file: 
                aps.rename_file(api, os.path.join(root, file), os.path.join(root, resolved))

def button_pressed(dialog, source):
    preview = dialog.get_value(dialog_preview_var)

    def copy_folder_async():    
        try:
            target = os.path.join(folder, preview)
            aps.copy_folder(api, source, target)
            rename_folder_entries(dialog, target)
            remove_gitkeep(target)
        except Exception as e:
            ui.show_error("Could not create Folder", str(e))
        else:
            ui.show_success("folder copied")
    
    ctx.run_async(copy_folder_async)
    dialog.close()

def create_copy_dialog(variable_count, template_folders, target_folder):
    dialog = ap.Dialog()
    dialog.title = "New Folder from Template"
    if ctx.icon:
        dialog.icon = ctx.icon
    if ctx.icon_color:
        dialog.icon_color = ctx.icon_color

    dialog.add_text("Template:\t").add_input(os.path.basename(template_folders), enabled=False, var=dialog_template_var)
    dialog.add_text("Preview:\t").add_input("Test", enabled=False, var=dialog_preview_var)
    dialog.add_separator()

    for variable in range(variable_count):
        dialog.start_section(f"variable {variable+1}", foldable=False)
        
        default = "Date of Today" if variable == 0 else "Name"
        dialog.add_dropdown(default, ["Increment", "Date of Today", "User Initials", "Name"], var=dialog_type_var+str(variable), \
            callback=lambda d,v,var=variable : dropdown_changed(var,d,v))
        dialog.add_input("", enabled=default=="Name", var=dialog_name_var+str(variable), callback=name_changed)
        dialog.end_section()

    dialog.add_button("Create Folder", callback=lambda d,src=template_folders: button_pressed(d,src))

    update_preview(dialog)
    return dialog

def get_variables_count(template_folders):
    return template_folders.count("$")

def check_folder_conflict(folder):
    if os.path.exists(folder):
        ui.show_error("could not create folder", f"target {folder} already exists")
        return True
    return False

def remove_gitkeep(folder):
    for root, _, files in os.walk(folder):
        for file in files:
            if file == ".gitkeep":
                os.remove(os.path.join(root, file))

def copy_folder_no_variables(template_folders, target_folder):
    if check_folder_conflict(target_folder):
        return    
    
    def copy_folder_no_variables_async():
        try:
            aps.copy_folder(api, template_folders, target_folder)
            remove_gitkeep(target_folder)
        except Exception as e:
            ui.show_error("could not copy folder", str(e))
    
    ctx.run_async(copy_folder_no_variables_async)

def copy_folder_with_variables(variable_count, template_folders, target_folder):
    dialog = create_copy_dialog(variable_count, template_folders, target_folder)
    if dialog:
        dialog.show()

def copy_folder(template_folder, target_folder):
    if not os.path.exists(template_folder):
        ui.show_error("could not create folder", "template_folder does not exist")
        return False

    variable_count = get_variables_count(template_folder)
    if variable_count == 0:
        copy_folder_no_variables(template_folder, target_folder)
        return
        
    copy_folder_with_variables(variable_count, template_folder, target_folder)
    

if "template_folder" not in ctx.inputs or len(ctx.inputs["template_folder"]) is 0:
    ui.show_error("template_folders not set", f"Please adapt {ctx.yaml}", duration=6000)
else:
    template_folder = ctx.inputs["template_folder"]
    if not os.path.exists(template_folder):
        template_folder = os.path.join(ctx.yaml_dir, template_folder)
    
    copy_folder(template_folder, os.path.join(ctx.path, os.path.basename(template_folder)))