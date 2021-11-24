import anchorpoint as ap
import string
import random
import os

ctx = ap.Context.instance()
ui = ap.UI()

current_folder = ctx.path

username = ctx.username

create_button_var = "create"
action_name_var = "name"
action_filename_var = "filename"
action_desc_var = "desc"
action_author_var = "author"
action_cat_var = "category"
action_id_var = "id"
action_icon_var = "icon"
action_python_var = "python"
registration_file_var = "regfile"
registration_folder_var = "regfolder"
registration_filefilter_var = "regfilefilter"
registration_folderfilter_var = "regfolderfilter"

def create_random_id():
    ran = "".join(random.choices(string.ascii_uppercase + string.digits, k=10))    
    return f"user::{str(ran)}"

def cb_name(dialog, value):
    button = dialog.get(create_button_var)   
    if button:
        button.enabled = len(value) != 0
    
    filename = get_filename(value)
    dialog.set_value(action_filename_var, filename + ".yaml")
    
def cb_reg_file(dialog, value):
    checkbox_file_entry = dialog.get(registration_filefilter_var)
    if checkbox_file_entry:
        checkbox_file_entry.enabled = value

def cb_reg_folder(dialog, value):
    checkbox_folder_entry = dialog.get(registration_folderfilter_var)
    if checkbox_folder_entry:
        checkbox_folder_entry.enabled = value

def get_filename(action_name):
    return action_name.lower().replace(" ", "_")

def create_action(dialog):
    action = ap.Action()
    action.name = dialog.get_value(action_name_var)
    action.description = dialog.get_value(action_desc_var)
    action.author = dialog.get_value(action_author_var)
    action.category = dialog.get_value(action_cat_var)
    action.id = dialog.get_value(action_id_var)
    action.icon = dialog.get_value(action_icon_var)
    action.is_python = dialog.get_value(action_python_var)

    regfile = dialog.get_value(registration_file_var)
    regfolder = dialog.get_value(registration_folder_var)
    if regfile:
        action.file_registration = dialog.get_value(registration_filefilter_var)
    if regfolder:
        action.folder_registration = dialog.get_value(registration_folderfilter_var)

    filename = dialog.get_value(action_filename_var)
    filepath = os.path.join(current_folder, filename)
    if action.is_python:
        action.script  = filepath.replace(".yaml", ".py")

    ap.create_action(filepath, action)    

    dialog.close()


dialog = ap.Dialog()
dialog.title = "Create New Action"
dialog.icon = ctx.icon

dialog.add_text("Name:\t").add_input("", var=action_name_var, callback=cb_name)
dialog.add_text("File:\t").add_input(".yaml", var=action_filename_var, enabled=False)
dialog.add_text("Description:\t").add_input("", var=action_desc_var)
dialog.add_checkbox(True, var=action_python_var).add_text("Use Python")
dialog.add_separator()

dialog.start_section("Registration", foldable=False)
dialog.add_checkbox(True, var=registration_file_var, callback=cb_reg_file) \
    .add_text("File\tFilter:").add_input("", var=registration_filefilter_var)
dialog.add_checkbox(False, var=registration_folder_var, callback=cb_reg_folder) \
    .add_text("Folder\tFilter:").add_input("", var=registration_folderfilter_var, enabled=False)
dialog.end_section()

dialog.start_section("Advanced")
dialog.add_text("Unique ID:\t").add_input(create_random_id(), var=action_id_var)
dialog.add_text("Author:\t").add_input(username, var=action_author_var)
dialog.add_text("Catgeory:\t").add_input("user", var=action_cat_var)
dialog.add_text("Icon:\t").add_input(":/icons/action.svg", var=action_icon_var)
dialog.end_section()

dialog.add_button("Create", create_action, var = create_button_var, enabled = False)

dialog.show()
