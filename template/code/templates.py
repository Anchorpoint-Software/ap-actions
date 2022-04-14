import anchorpoint as ap
import apsync as aps
import os, re, sys
from datetime import datetime

ctx = ap.Context.instance()
ui = ap.UI()

target_folder = ctx.path

# Stores all tokens which will be resolved before the copy&paste process.
# It contains entries like: "Client_Name": ACME, "Project_Name": Commercial
variables =	{}

# Stores all tokens, which require user input via the Dialog
user_inputs = {}

# Stores all templates the user can choose from. 
folder_templates = {}

# Stores available tokens per template
template_available_tokens = {}

if "create_project" in ctx.inputs:
    create_project = ctx.inputs["create_project"]
else:
    create_project = False

project = aps.get_project(target_folder)
allow_project_creation = project is None

if "file_mode" in ctx.inputs:
    file_mode = ctx.inputs["file_mode"]
else:
    file_mode = False

template = ctx.inputs["template_dir"]
template_subdir = ctx.inputs["template_subdir"]
template_dir = os.path.join(ctx.yaml_dir, template)
yaml_dir = ctx.yaml_dir

settings = aps.SharedSettings(ctx.workspace_id, "AnchorpointTemplateSettings")
template_dir = os.path.join(settings.get("template_dir", template_dir), template_subdir)
callback_file = os.path.join(settings.get("callback_dir"), "template_action_events.py")
if os.path.exists(callback_file):
    callbacks = aps.import_local(os.path.splitext(callback_file)[0], True)
else:
    callbacks = None

if project:
    project_callbacks = os.path.join(project.path, ".ap/templates/template_action_events.py")
    if os.path.exists(project_callbacks):
        callback_file = project_callbacks
    project_template_dir = os.path.join(project.path, ".ap/templates", template_subdir)
else:
    project_template_dir = ""


if os.path.exists(template_dir) == False and os.path.exists(project_template_dir) == False:
    ui.show_info("No templates available", f"Please add a proper template using the Save as Template action")
    sys.exit(0)

# Return the template path for the project of workspace (project wins)
def get_template_path(template_name):
    template_path = os.path.join(project_template_dir, template_name)
    if project and os.path.exists(template_path):
        return template_path
    return os.path.join(template_dir, template_name)

# Return all foldernames within a folder
def get_all_foldernames(folder):
    if os.path.exists(folder):
        return next(os.walk(folder))[1]
    return []

def compute_variable_availability(template_name):
    template_path = get_template_path(template_name)
    for _, dirs, files in os.walk(template_path):
        for file in files:
            for key in user_inputs.keys():
                if ("["+str(key)+"]") in file:
                    template_available_tokens[template_name].add(str(key))
        for dir in dirs:
            for key in user_inputs.keys():
                if ("["+str(key)+"]") in dir:
                    template_available_tokens[template_name].add(str(key))

# Deactive UI elements if the chosen template does not require them
def set_variable_availability(dialog, value):
    for key in user_inputs.keys():
        dialog.hide_row(str(key),True)

    for key in template_available_tokens[value]:
        dialog.hide_row(str(key),False)

# Search for tokens in a single file oder folder name / entry
def get_tokens(entry, variables: dict):
    entry_vars =  re.findall('\[[^\[\]]*\]',entry)
    for var in entry_vars:
        variables[var.replace("[","").replace("]","")] = None

# Traverse the template structure and look for tokens which will be shown in the dialog popup
def get_template_variables(dir):
    variables = {}

    for _, dirs, files in os.walk(dir):
        for file in files:
            get_tokens(file, variables)
        for dir in dirs:
            get_tokens(dir, variables)

    resolve_tokens(list(variables))

# Build the variables with the tokens from the template. Add a value directly if possible
def resolve_tokens(variable_list):
    for variable in variable_list:
        # Increment logic is simple, we just check for the object count in the folder
        if variable == "Increment":
            increment = len(os.listdir(target_folder))+1
            variables["Increment"] = str(increment*10).zfill(4)
        
        # If the token is a date, add the value to the dict
        elif variable == "YYYY":
            variables["YYYY"] = datetime.today().strftime('%Y')
        elif variable == "YYYYMM":
            variables["YYYYMM"] = datetime.today().strftime('%Y%m')
        elif variable == "YYYY-MM":
            variables["YYYY-MM"] = datetime.today().strftime('%Y-%m')
        elif variable == "YYYYMMDD":
            variables["YYYYMMDD"] = datetime.today().strftime('%Y%m%d')
        elif variable == "YYYY-MM-DD":
            variables["YYYY-MM-DD"] = datetime.today().strftime('%Y-%m-%d')
        elif variable not in variables:
            variables[variable] = ""

    if callbacks and "resolve_tokens" in dir(callbacks):
        callbacks.resolve_tokens(variables, target_folder)

    for variable in variables:
        if len(variables[variable]) == 0:
            user_inputs[variable] = ""

# Get the values from the UI
def create_template(dialog):
    template_name = dialog.get_value("dropdown")
    create_project = dialog.get_value("create_project")

    # Load the user input and pass it to the dictionaries
    for key in user_inputs.keys():
        user_inputs[str(key)] = variables[str(key)] = dialog.get_value(str(key))
        
    template_path = get_template_path(template_name)

    if (os.path.isdir(template_path)):
        # Run everything async to not block the main thread
        if create_project : 
            ctx.run_async(create_project_from_template, template_path, target_folder, ctx)    
        else: 
            ctx.run_async(create_documents_from_template, template_path, target_folder, ctx)    
    else:
        ui.show_error("Template does not exist", f"Please add a proper template")

    dialog.close()

def create_dialog():
    dialog = ap.Dialog()

    dialog.title = "New Project" if create_project else "New Document"
    if ctx.icon:
        dialog.icon = ctx.icon

    # Set a description and a dropdown. Use \t to create tab spaces
    dialog.add_text("Template:\t").add_dropdown(
        folder_templates[0],
        folder_templates,
        var="dropdown",
        callback = set_variable_availability
    )

    # Use the unresolved tokens in text_inputs, to create input fields 
    has_keys = len(user_inputs.keys()) > 0

    if has_keys:
        for key in user_inputs.keys():
            dialog.add_text(str(key).replace("_"," ")+":\t").add_input("" , var = str(key))

        dialog.add_info("Tokens (placeholders) were found in your template. <br> They will be replaced with the entries in the text fields.")    
   
    # Grey out certain inputs if there is no token in the file/ folder name which is currently choosen in the dropdown
    set_variable_availability(dialog,folder_templates[0])

    if file_mode == False and allow_project_creation:
        dialog.add_checkbox(var="create_project").add_text("This is a project")
        dialog.add_info("Select this option if it is a project template. <br> Anchorpoint will create a project in the project list.")

    # Add a button to create the project, register a callback when the button is clicked.
    dialog.add_button("Create", callback = create_template)

    # Deactivate input fields if necessary
    set_variable_availability(dialog,folder_templates[0])

    # Present the dialog to the user
    dialog.show()   

def strip_spaces(string):
    return "".join(string.rstrip().lstrip())
    
def create_project_from_template(template_path, target_folder, ctx):
    # Start the progress indicator in the top right corner
    ap.Progress("Creating Project", "Copying Files and Attributes")
    # Get the template root folder
    foldernames = get_all_foldernames(template_path)
    if len(foldernames) > 1:
        ui.show_error("Failed to create project", "Template folder contains multiple root folder")
        return
    if len(foldernames) == 0:
        ui.show_error("Failed to create project", "Template folder contains no root folder")
        return

    foldername = foldernames[0]
    source = os.path.join(template_path, foldername)

    # Set the root folder in the project. Use the resolved tokens e.g. [Client_Name] -> ACME
    target = os.path.join(target_folder, aps.resolve_variables(foldername, variables))

    if os.path.exists(target):
        ui.show_error("Folder exists", f"The folder {target} already exists")
        return

    # Set a project name which will show up in the project list
    tokens = {}
    get_tokens(source, tokens)
    project_display_name = ""
    for token in tokens:
        if token in user_inputs:
            project_display_name += user_inputs[token]+ " "

    # Create the actual project and write it in the database
    project = ctx.create_project(target, strip_spaces(project_display_name))
    # Copy the whole folder structure and resolve all tokens using the variables dict
    aps.copy_from_template(source, target, variables)

    # Add metadata to the project, which was recorded by user input.
    # This metadata can be used for any file and subfolder templates
    # The user won't need to enter this data again
    project.update_metadata(user_inputs)

    if callbacks and "project_from_template_created" in dir(callbacks):
        callbacks.project_from_template_created(target, source, variables, project)

    ui.show_success("Project successfully created")


def create_documents_from_template(template_path, target_folder, ctx):
    # Start the progress indicator in the top right corner
    ap.Progress("Creating From Template", "Copying Files and Attributes")

    # Copy the whole folder structure and resolve all tokens using the variables dict
    try:
        if file_mode:
            aps.copy_file_from_template(template_path, target_folder, variables)
            if callbacks and "file_from_template_created" in dir(callbacks):
                callbacks.file_from_template_created(target_folder, template_path, variables)
        else:
            aps.copy_from_template(template_path, target_folder, variables)
            if callbacks and "folder_from_template_created" in dir(callbacks):
                callbacks.folder_from_template_created(target_folder, template_path, variables)

        ui.show_success("Document(s) successfully created")
    except Exception as e:
        if "exists" in str(e):
            ui.show_info("Document(s) already exist", "Please choose a different name")
        else:
            ui.show_error("Document(s) could not be created")    

    
# Look for all folders in the template directories
folder_template_list = get_all_foldernames(template_dir)
if project:
    # Project templates with the same name overwrite global templates
    folder_template_list.extend(get_all_foldernames(project_template_dir))

folder_templates = list(dict.fromkeys(folder_template_list))
template_available_tokens = dict.fromkeys(folder_template_list)
for token in template_available_tokens:
    template_available_tokens[token] = set()

if len(folder_templates) == 0:
    ui.show_info("No templates available", f"Please add a proper template using the Save as Template Action")
else:
    if not create_project:
        # Check if the target location is part of a project. A project can store metadata, which could be tokens e.g "Client_Name". 
        # If these tokens show up in the file name, they can be resolved from the project metadata and the user does not need to enter them again
        if project:
            metadata = project.get_metadata()
            variables.update(metadata)

    # Check all tokens in the file / folder
    get_template_variables(template_dir)
    if project:
        get_template_variables(project_template_dir)

    for template in folder_templates:
        compute_variable_availability(template)

    # build the dialog
    create_dialog()