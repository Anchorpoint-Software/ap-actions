import anchorpoint as ap
import apsync as aps
from sys import platform
import subprocess
import random
import string
import os

ui = ap.UI()
ctx = ap.Context.instance()
api = ctx.create_api()

def create_random_text():
    ran = "".join(random.choices(string.ascii_uppercase + string.digits, k=10))    
    return str(ran)

def render_blender(blender_path, selected_files, yaml_dir):
    def render_blender_async():
        # Use a random output path within the Anchorpoint temporary directory
        # so that we do not conflict with any other file
        output = f"{ap.temp_dir()}/blender/{create_random_text()}"
        for file in selected_files:
            subprocess.run(
                [
                    blender_path,
                    "-b", file,
                    "-E", "BLENDER_EEVEE",
                    "-F", "PNG",
                    "-P", f"{yaml_dir}/blender_eevee_settings.py",
                    "-o", f"{output}#",
                    "-f", "0",
                ]
            )
            ui.replace_thumbnail(file, f"{output}0.png")
            
        ui.show_success("Render Successful")

    # Tell the UI that these files are being processed
    for file in selected_files:
        ui.show_busy(file)

    # We don't want to block the Anchorpoint UI, hence we run on a background thread
    ctx.run_async(render_blender_async)

# First, check if the tool can be found on the machine
if "blender" in ctx.inputs:
    blender_path = ctx.inputs["blender"]

    if blender_path.lower().endswith("blender.app"):
        blender_path = os.path.join(blender_path, "Contents/MacOS/Blender")

    if ap.check_application(blender_path, f"Path to Blender is not correct, please try again", "blender"):
        # Render the thumbnail
        render_blender(blender_path, ctx.selected_files, ctx.yaml_dir)
    else:
        # Remove the path to blender from the action settings so that the user must provide it again
        settings = aps.Settings(api)
        if settings:
            settings.remove("blender")
            settings.store()