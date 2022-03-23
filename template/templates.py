import anchorpoint as ap
import apsync as aps
import os
import re 
from datetime import datetime

ctx = ap.Context.instance()
ui = ap.UI()

target_folder = ctx.path

# Stores all tokens which will be resolved before the copy&paste process.
# It contains entries like: "Client_Name": ACME, "Project_Name": Commercial
variables =	{}

# Stores all tokens, which require user input via the Dialog
text_inputs = {}

if "create_project" in ctx.inputs:
    create_project = ctx.inputs["create_project"]
else:
    create_project = False

if "file_mode" in ctx.inputs:
    file_mode = ctx.inputs["file_mode"]
else:
    file_mode = False

template = ctx.inputs["template_dir"]
template_dir = os.path.join(ctx.yaml_dir, template)
yaml_dir = ctx.yaml_dir

# Return all foldernames within a folder
def get_all_foldernames(folder):
    return next(os.walk(folder))[1]

# Deactive UI elements if the chosen template does not require them
def set_variable_availability(dialog, value):
    template_path = os.path.join(template_dir, value)

    for key in text_inputs.keys():
        dialog.set_enabled(str(key),False)

    for _, dirs, files in os.walk(template_path):
        for file in files:
            for key in text_inputs.keys():
                if ("["+str(key)+"]") in file:
                    dialog.set_enabled(str(key),True)
        for dir in dirs:
            for key in text_inputs.keys():
                if ("["+str(key)+"]") in dir:
                    dialog.set_enabled(str(key),True)

# Search for tokens in a single file oder folder name / entry
def get_tokens(entry, variables: dict):
    entry_vars =  re.findall('\[[^\[\]]*\]',entry)
    for var in entry_vars:
        variables[var.replace("[","").replace("]","")] = None

# Traverse the template structure and look for tokens which will be shown in the dialog popup
def get_template_variables():
    variables = {}

    for _, dirs, files in os.walk(template_dir):
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
        else:
            # Check if certain tokens are already in the project (e.g. client name), 
            # so the value can be read from there and the user does not need to enter it again
            if variable not in variables.keys():
                # For all tokens, that cannot be resolved directly, add them to text_inputs,
                # they will be used to create the UI elements in the dialog
                text_inputs[variable] = "text"

# Get the values from the UI
def create_template(dialog):
    template_name = dialog.get_value("dropdown")

    # Load the user input and pass it to the dictionaries
    for key in text_inputs.keys():
        text_inputs[str(key)] = variables[str(key)] = dialog.get_value(str(key))
        
    template_path = os.path.join(template_dir,template_name)

    if (os.path.isdir(template_path)):
        # Run everything async to not block the main thread
        if create_project : 
            ctx.run_async(create_project_from_template, template_path, target_folder, ctx)    
        else: 
            ctx.run_async(create_documents_from_template, template_path, target_folder, ctx)    
    else:
        ui.show_error("Template does not exist", f"Please add a proper template in {template_dir}")

    dialog.close()

def create_dialog():
    dialog = ap.Dialog()

    dialog.title = "New Project" if create_project else "New Document"
    if ctx.icon:
        dialog.icon = ctx.icon
    
    # Set a description and a dropdown. Use \t to create tab spaces
    if len(folder_templates)>1:
        dialog.add_text("Template:\t\t").add_dropdown(
            folder_templates[0],
            folder_templates,
            var="dropdown",
            callback = set_variable_availability
        )
    
    dialog.add_separator()

    # Use the unresolved tokens in text_inputs, to create input fields
    for key in text_inputs.keys():
        dialog.add_text(str(key).replace("_"," ")+":\t").add_input("" , var = str(key))
 
    # Grey out certain inputs if there is no token in the file/ folder name which is currently choosen in the dropdown
    set_variable_availability(dialog,folder_templates[0])

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
        if token in text_inputs:
            project_display_name += text_inputs[token]+ " "

    # Create the actual project and write it in the database
    project = ctx.create_project(target, strip_spaces(project_display_name))
    # Copy the whole folder structure and resolve all tokens using the variables dict
    aps.copy_from_template(source, target, variables)

    # Add metadata to the project, which was recorded by user input.
    # This metadata can be used for any file and subfolder templates
    # The user won't need to enter this data again
    project.update_metadata(text_inputs)
    ui.show_success("Project successfully created")


def create_documents_from_template(template_path, target_folder, ctx):
    # Start the progress indicator in the top right corner
    ap.Progress("Creating From Template", "Copying Files and Attributes")

    # Copy the whole folder structure and resolve all tokens using the variables dict
    if file_mode:
        aps.copy_file_from_template(template_path, target_folder, variables)
    else:
        aps.copy_from_template(template_path, target_folder, variables)

    ui.show_success("Document(s) successfully created")
    
# Look for all folders in the template directory
folder_templates = get_all_foldernames(template_dir)

if len(folder_templates) == 0:
    ui.show_error("No templates available", f"Please add a proper template in {template_dir}")
else:
    if not create_project:
        # Check if the target location is part of a project. A project can store metadata, which could be tokens e.g "Client_Name". 
        # If these tokens show up in the file name, they can be resolved from the project metadata and the user does not need to enter them again
        project = aps.get_project(target_folder)
        if project:
            metadata = project.get_metadata()
            variables.update(metadata)

    # Check all tokens in the file / folder
    get_template_variables()

    # build the dialog
    create_dialog()