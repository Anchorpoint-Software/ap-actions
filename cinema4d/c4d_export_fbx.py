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

c4d_path = ctx.inputs["c4dPathMac"] if platform == "darwin" else ctx.inputs["c4dPathWindows"]

c4d_username = ""
c4d_password = ""
if "c4dUsername" in ctx.inputs and len(ctx.inputs["c4dUsername"]) > 0:
    c4d_username = ctx.inputs["c4dUsername"] 
if "c4dPassword" in ctx.inputs and len(ctx.inputs["c4dPassword"]) > 0:
    c4d_password = ctx.inputs["c4dPassword"]

def set_all_attributes():
    if set_attributes == False:
        return
    aps.set_cell_date(api, scene, "Exported Date", int(time.time()))
    aps.set_cell_link(api, scene, "FBX", outFile)
    aps.set_cell_link(api, outFile, "Source", scene)


def export_fbx():
    ui.show_busy(scene)
    if not os.path.exists(target_folder):
        os.makedirs(target_folder)
    
    c4d = None
    if c4d_username is not "" and c4d_password is not "":
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
    
    if c4d.returncode is not 0:
        print(c4d.stderr)
        ui.show_toast("Failed to Export!", description="Check Anchorpoint Console", type=ap.UI.ToastType.Fail)
    else:
        print(c4d.stdout)
        set_all_attributes()
        ui.show_toast("Export Successful")
        ui.navigate_to_folder(scene)

if (ap.check_application(c4d_path, f"Could not find Cinema 4D! Make sure it is set up correctly in {ctx.yaml}")):
    ctx.run_async(export_fbx)
