import anchorpoint as ap
import apsync as aps
from sys import platform
import subprocess
import tempfile
import random
import string

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
blender_path = None
if platform == "darwin":
    blender_path = ctx.inputs["blender_mac"]
elif platform == "win32":
    blender_path = ctx.inputs["blender_win"]

if (ap.check_application(blender_path, f"Could not find blender! Make sure blender is set up correctly in {ctx.yaml}")):
    # Render the thumbnail
    render_blender(blender_path, ctx.selected_files, ctx.yaml_dir)