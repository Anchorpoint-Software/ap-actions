import anchorpoint as ap
import apsync as aps
import subprocess
import os
import time
from sys import platform

ctx = ap.Context.instance()
ui = ap.UI()
api = ctx.create_api()

scene = ctx.path
target_folder = ctx.inputs["targetFolder"]
out = target_folder+"/"+ctx.filename
outFile = target_folder+"/"+ctx.filename + ".fbx"
set_attributes = "setAttributes" in ctx.inputs and ctx.inputs["setAttributes"]

if "c4d" in ctx.inputs:
    c4d_path = ctx.inputs["c4d"]
    if c4d_path.lower().endswith("commandline.app"):
        c4d_path = os.path.join(c4d_path, "Contents/MacOS/Commandline")

c4d_username = ""
c4d_password = ""
if "c4dUsername" in ctx.inputs and len(ctx.inputs["c4dUsername"]) > 0:
    c4d_username = ctx.inputs["c4dUsername"] 
if "c4dPassword" in ctx.inputs and len(ctx.inputs["c4dPassword"]) > 0:
    c4d_password = ctx.inputs["c4dPassword"]

def set_all_attributes():
    if set_attributes == False:
        return
    aps.set_attribute_date(api, scene, "Exported Date", int(time.time()))
    aps.set_attribute_link(api, scene, "FBX", outFile)
    aps.set_attribute_link(api, outFile, "Source", scene)


def export_fbx():
    ui.show_busy(scene)
    if not os.path.exists(target_folder):
        os.makedirs(target_folder)
    
    c4d = None
    if c4d_username != "" and c4d_password != "":
        c4d = subprocess.run(
            [
                c4d_path,
                f"g_licenseUsername={c4d_username}",
                f"g_licensePassword={c4d_password}",
                f"--ap_export_fbx={scene}",
                f"--ap_out={out}",
            ], capture_output=True
        )
    else:
        c4d = subprocess.run(
            [
                c4d_path,
                f"--ap_export_fbx={scene}",
                f"--ap_out={out}",
            ], capture_output=True
        )
    
    ui.finish_busy(scene)
    
    if c4d.returncode != 0:
        print(c4d.stderr)
        ui.show_error("Failed to Export!", "Check Anchorpoint Console")
    else:
        print(c4d.stdout)
        set_all_attributes()
        ui.show_success("Export Successful")
        ui.reload()

if (ap.check_application(c4d_path, f"Path to Cinema 4D's commandline tool is not correct. It is called Commandline.exe / Commandline.app. Please try again", "commandline")):
    ctx.run_async(export_fbx)
else:
    # Remove the path to c4d from the action settings so that the user must provide it again
    settings = aps.Settings(api)
    if settings:
        settings.remove("c4d")
        settings.store()
