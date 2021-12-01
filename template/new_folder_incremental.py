import anchorpoint as ap
import apsync as aps

import os
from shutil import copyfile
from distutils.dir_util import copy_tree

# Anchorpoint UI class allows us to show e.g. Toast messages in Anchorpoint
ui = ap.UI()

# The Anchorpoint context object provides the predefined variables and the inputs from the YAML file.
ctx = ap.Context.instance()

# API to talk to the server
api = ctx.create_api()

import sys
sys.path.insert(0, ctx.yaml_dir)
import template_utility

def rename_folder_entries(target, variable_resolved):
    for root, _, files in os.walk(target):
        if root != target:
            root_resolved = root.replace("$", variable_resolved)
            if root_resolved != root: 
                aps.rename_folder(api, root, root_resolved)

        for file in files:
            file_resolved = file.replace("$", variable_resolved)
            if file_resolved != file: 
                aps.rename_file(api, os.path.join(root, file), os.path.join(root, file_resolved))

def copy_folder_async(template_folder, target_path, variable_resolved):
    def copy_folder_async_helper():    
        try:
            aps.copy_folder(api, template_folder, target_path)
            rename_folder_entries(target_path, variable_resolved)
            template_utility.remove_gitkeep(target_path)
        except Exception as e:
            ui.show_error("Could not create folder", str(e))
        else:
            ui.show_success("folder Created")
    
    ctx.run_async(copy_folder_async_helper)


def create_folder(template_folder, target_path):
    resolved = template_utility.resolve_variable(os.path.basename(target_path), template_utility.VariableType.INCREMENT, os.path.dirname(target_path))
    target_path = target_path.replace("$", resolved)
    
    if os.path.exists(target_path):
        ui.show_error("Could not create folder", "Folder exists")
    else:
        copy_folder_async(template_folder, target_path, resolved)

if "template_folder" not in ctx.inputs or len(ctx.inputs["template_folder"]) is 0:
    ui.show_error("Could not create folder", f"Variable template_folder not set. Please adapt {ctx.yaml}", duration=6000)
else:
    template_folder = ctx.inputs["template_folder"]
    if not os.path.exists(template_folder):
        template_folder = os.path.join(ctx.yaml_dir, template_folder)

    create_folder(template_folder,  os.path.join(ctx.path, os.path.basename(template_folder)))