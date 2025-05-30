import anchorpoint as ap
import apsync as aps
import os
import re
import sys
from datetime import datetime
from template_settings import get_workspace_template_dir, get_callback_location

import template_utility

ctx = ap.get_context()
ui = ap.UI()

target_folder = ctx.path

# Stores all tokens which will be resolved before the copy&paste process.
# It contains entries like: "Client_Name": ACME, "Project_Name": Commercial
variables = {}

# Stores all tokens, which require user input via the Dialog
user_inputs = {}

# Stores all templates the user can choose from.
folder_templates = {}

# Stores available tokens per template
template_available_tokens = {}

username = ctx.username

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
template_root_dir = get_workspace_template_dir(settings, template_dir)
template_dir = os.path.join(template_root_dir, template_subdir)
callback_file = get_callback_location(settings, template_root_dir)

if project:
    project_templates_location = template_utility.get_template_dir(
        project.path)
    project_callbacks = template_utility.get_template_callbacks(
        project_templates_location
    )
    if os.path.exists(project_callbacks):
        callback_file = project_callbacks
    project_template_dir = os.path.join(
        project_templates_location, template_subdir)
else:
    project_template_dir = ""

if os.path.exists(callback_file):
    callbacks = aps.import_local(os.path.splitext(callback_file)[0], True)
else:
    callbacks = None

if (
    os.path.exists(template_dir) is False
    and os.path.exists(project_template_dir) is False
):
    ui.show_info(
        "No templates available",
        "Please add a proper template using the Save as Template action",
    )
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
                if ("[" + str(key) + "]") in file:
                    template_available_tokens[template_name].add(str(key))
        for dir in dirs:
            for key in user_inputs.keys():
                if ("[" + str(key) + "]") in dir:
                    template_available_tokens[template_name].add(str(key))


# Deactive UI elements if the chosen template does not require them
def set_variable_availability(dialog, value):
    for key in user_inputs.keys():
        dialog.hide_row(str(key), True)

    if value in template_available_tokens:
        for key in template_available_tokens[value]:
            dialog.hide_row(str(key), False)


def get_user_input_for_template(template_name):
    if template_name in template_available_tokens.keys():
        tokens = template_available_tokens[template_name]
        template_user_inputs = {}
        for token in tokens:
            if token in user_inputs.keys():
                template_user_inputs[token] = user_inputs[token]
        return template_user_inputs
    else:
        return {}


# Search for tokens in a single file oder folder name / entry
def get_tokens(entry, variables: dict):
    entry_vars = re.findall("\[[^\[\]]*\]", entry)
    for var in entry_vars:
        variables[var.replace("[", "").replace("]", "")] = None


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
        increment = len(os.listdir(target_folder)) + 1
        if variable == "Increment":
            variables["Increment"] = str(increment * 10).zfill(4)
        if variable == "Inc####":
            variables["Inc####"] = str(increment).zfill(4)
        if variable == "Inc###":
            variables["Inc###"] = str(increment).zfill(3)
        if variable == "Inc##":
            variables["Inc##"] = str(increment).zfill(2)
        if variable == "Inc#":
            variables["Inc#"] = str(increment)

        # If the token is a date, add the value to the dict
        elif variable == "YYYY":
            variables["YYYY"] = datetime.today().strftime("%Y")
        elif variable == "YYYYMM":
            variables["YYYYMM"] = datetime.today().strftime("%Y%m")
        elif variable == "YYYY-MM":
            variables["YYYY-MM"] = datetime.today().strftime("%Y-%m")
        elif variable == "YYYYMMDD":
            variables["YYYYMMDD"] = datetime.today().strftime("%Y%m%d")
        elif variable == "YYYY-MM-DD":
            variables["YYYY-MM-DD"] = datetime.today().strftime("%Y-%m-%d")
        elif variable == "DD-MM-YYYY":
            variables["DD-MM-YYYY"] = datetime.today().strftime("%d-%m-%Y")
        elif variable == "YY":
            variables["YY"] = datetime.today().strftime("%y")
        elif variable == "YYMM":
            variables["YYMM"] = datetime.today().strftime("%y%m")
        elif variable == "YY-MM":
            variables["YY-MM"] = datetime.today().strftime("%y-%m")
        elif variable == "YYMMDD":
            variables["YYMMDD"] = datetime.today().strftime("%y%m%d")
        elif variable == "YY-MM-DD":
            variables["YY-MM-DD"] = datetime.today().strftime("%y-%m-%d")
        elif variable == "DD-MM-YY":
            variables["DD-MM-YY"] = datetime.today().strftime("%d-%m-%y")
        elif variable == "ProjectFolder":
            projectFolder = os.path.basename(
                os.path.normpath(ctx.project_path))
            variables["ProjectFolder"] = str(projectFolder)
        elif variable == "User":
            username_underscore = username.replace(
                " ", "_").replace(".", "_").lower()
            variables["User"] = str(username_underscore)
        elif variable == "UserInitials":
            username_split = username.split(" ")
            initials = ""
            for name in username_split:
                initials += name[0].lower()
            variables["UserInitials"] = str(initials)
        elif variable == "ParentFolder":
            variables["ParentFolder"] = os.path.basename(ctx.path)
        elif variable == "ParentParentFolder":
            variables["ParentParentFolder"] = os.path.basename(
                os.path.dirname(ctx.path))
        elif variable == "ParentParentParentFolder":
            variables["ParentParentParentFolder"] = os.path.basename(
                os.path.dirname(os.path.dirname(ctx.path)))
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
        user_inputs[str(key)] = variables[str(
            key)] = dialog.get_value(str(key))

    template_path = get_template_path(template_name)

    if os.path.isdir(template_path):
        # Run everything async to not block the main thread
        if create_project:
            ctx.run_async(
                create_project_from_template_async,
                template_path,
                target_folder,
                ctx,
                template_name,
            )
        else:
            ctx.run_async(
                create_documents_from_template_async, template_path, target_folder, ctx
            )
    else:
        ui.show_error("Template does not exist",
                      "Please add a proper template")

    dialog.close()


def create_dialog():
    dialog = ap.Dialog()

    dialog.title = "New Project" if create_project else "New Document"
    if ctx.icon:
        dialog.icon = ctx.icon

    # Set a description and a dropdown. Use \t to create tab spaces
    dialog.add_text("Template",width=72).add_dropdown(
        folder_templates[0],
        folder_templates,
        var="dropdown",
        callback=set_variable_availability,
    )

    # Use the unresolved tokens in text_inputs, to create input fields
    has_keys = len(user_inputs.keys()) > 0

    if has_keys:
        for key in user_inputs.keys():
            dialog.add_text(str(key).replace("_", " "),width=72).add_input(
                "", var=str(key)
            )
        dialog.add_info(
            "Tokens (placeholders) were found in your template. <br> They will be replaced with the entries in the text fields."
        )

    # Present the dialog to the user
    dialog.show(settings)

    # Grey out certain inputs if there is no token in the file/ folder name which is currently choosen in the dropdown
    set_variable_availability(dialog, dialog.get_value("dropdown"))

    if file_mode is False and allow_project_creation:
        dialog.add_checkbox(var="create_project", text="This is a project")
        dialog.add_info(
            "Select this option if it is a project template. <br> Anchorpoint will create a project in the project list."
        )

    # Add a button to create the project, register a callback when the button is clicked.
    dialog.add_button("Create", callback=create_template)

    # Deactivate input fields if necessary
    set_variable_availability(dialog, dialog.get_value("dropdown"))


def strip_spaces(string):
    return "".join(string.rstrip().lstrip())


def create_project_from_template_async(
    template_path, target_folder, ctx, template_name
):
    # Start the progress indicator in the top right corner
    ap.Progress("Creating Project", "Copying Files and Attributes")
    # Get the template root folder
    foldernames = get_all_foldernames(template_path)
    if len(foldernames) > 1:
        ui.show_error(
            "Failed to create project", "Template folder contains multiple root folder"
        )
        return
    if len(foldernames) == 0:
        ui.show_error(
            "Failed to create project", "Template folder contains no root folder"
        )
        return

    foldername = foldernames[0]
    source = os.path.join(template_path, foldername)

    # Set the root folder in the project. Use the resolved tokens e.g. [Client_Name] -> ACME
    target = os.path.join(
        target_folder, aps.resolve_variables(foldername, variables))

    if os.path.exists(target):
        ui.show_error("Folder exists", f"The folder {target} already exists")
        return

    # Set a project name which will show up in the project list
    tokens = {}
    get_tokens(source, tokens)
    project_display_name = os.path.split(target)[1]
    project_display_name = project_display_name.replace(
        "-", " ").replace("_", " ")

    # Create the actual project and write it in the database
    project = ctx.create_project(
        target, strip_spaces(project_display_name), workspace_id=ctx.workspace_id
    )
    # Copy the whole folder structure and resolve all tokens using the variables dict
    aps.copy_from_template(source, target, variables,
                           workspace_id=ctx.workspace_id)

    # Add the resolved tokens as metadata to the project
    # This metadata can be used for any file and subfolder templates
    # The user won't need to enter this data again
    user_inputs_for_template = get_user_input_for_template(template_name)
    if len(user_inputs_for_template) > 0:
        project.update_metadata(user_inputs_for_template)

    if callbacks and "project_from_template_created" in dir(callbacks):
        callbacks.project_from_template_created(
            target, source, variables, project)

    ui.show_success("Project successfully created")


def create_documents_from_template_async(template_path, target_folder, ctx):
    # Start the progress indicator in the top right corner
    ap.Progress("Creating From Template", "Copying Files and Attributes")

    # Copy the whole folder structure and resolve all tokens using the variables dict
    try:
        if file_mode:
            aps.copy_file_from_template(
                template_path, target_folder, variables, workspace_id=ctx.workspace_id
            )
            if callbacks and "file_from_template_created" in dir(callbacks):
                callbacks.file_from_template_created(
                    target_folder, template_path, variables
                )
        else:
            aps.copy_from_template(
                template_path, target_folder, variables, workspace_id=ctx.workspace_id
            )
            if callbacks and "folder_from_template_created" in dir(callbacks):
                callbacks.folder_from_template_created(
                    target_folder, template_path, variables
                )

        ui.show_success("Document(s) successfully created")
    except Exception as e:
        if "exists" in str(e):
            ui.show_info("Document(s) already exist",
                         "Please choose a different name")
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
    ui.show_info(
        "No templates available",
        "Please add a proper template using the Save as Template Action",
    )
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
