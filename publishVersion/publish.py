import anchorpoint as ap
import apsync as aps
import os
import sys
import re

ctx = ap.Context.instance()
project = aps.get_project(ctx.project_path)
ui = ap.UI()
api = ap.get_api()


def split_name_and_version(filename):
    # This regex matches any number of digits,
    # optionally preceded by 'v' or '_v', and optionally separated by '_'
    # It allows for additional content after the version number
    match = re.search(r'(.*?)(?:_v?(\d+))(?:_|$)', filename, re.IGNORECASE)
    if match:
        return match.group(1), match.group(2)
    
    # If no match with underscore, try matching 'v' followed by digits at the end
    match = re.search(r'(.*?v)(\d+)$', filename, re.IGNORECASE)
    if match:
        return match.group(1), match.group(2)
    
    # If still no match, try matching any digits at the end
    match = re.search(r'(.*?)(\d+)$', filename)
    if match:
        return match.group(1), match.group(2)
    
    return filename, None

def copy(settings):
    if project is None:
        ui.show_info("Action only works with projects")
        sys.exit(0)

    base_name, version = split_name_and_version(ctx.filename)
    
    if version is not None:
        progress = ap.Progress("Publishing", "Creating a copy")

        new_name = base_name

        new_name_appendix = new_name

        try:
            new_name_appendix += settings["publish_version_appendix"]
        except:
            pass

        new_location = ctx.folder

        try:
            if settings["publish_file_location"] != "":
                new_location = settings["publish_file_location"]
        except:
            new_location = ctx.folder

        # possibility to publish in parent folder and adding relative paths
        location_split = new_location.split("../")
        backsteps = len(location_split)
        if backsteps > 1:
            new_location = ctx.folder
            x = range(1, backsteps)
            for i in x:
                new_location = os.path.dirname(new_location)
            appendix = location_split[-1]

            new_location = new_location + "/" + appendix
            # check if folder is correct
            if not os.path.isdir(new_location):
                ui.show_error(
                    "Folder not set correctly",
                    "Please check your output folder in the settings.",
                )
                return

        new_path = os.path.join(new_location, new_name_appendix + "." + ctx.suffix)

        aps.copy_file(ctx.path, new_path, overwrite=True)
        api.attributes.set_attribute_value(new_path, "Source File", ctx.filename, True)

        ui.show_success(
            f"Published {new_name_appendix}", f"Published in {new_location}"
        )
        progress.finish()

    else:
        ui.show_error("Not an increment", "This file has no v001 or similar")
        return

if __name__ == "__main__":
    ctx.run_async(copy,project.get_metadata())

def run_action(ctx,settings):
    ctx.run_async(copy,settings)