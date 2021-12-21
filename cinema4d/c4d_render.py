import anchorpoint as ap
import apsync as aps
import subprocess
import os
from sys import platform

ctx = ap.Context.instance()
ui = ap.UI()
api = ctx.create_api()

scene = ctx.path
out = os.path.join(ctx.inputs["targetFolder"], ctx.filename + ".mp4")
set_attributes = "setAttributes" in ctx.inputs and ctx.inputs["setAttributes"]
render_settings = ctx.inputs["renderSettings"]

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
    aps.set_attribute_link(api, scene, "Rendering", out)
    aps.set_attribute_link(api, out, "Source", scene)

def render():
    ui.show_busy(scene)
    c4d = None
    if c4d_username is not "" and c4d_password is not "":
        c4d = subprocess.run(
            [
                c4d_path,
                f"g_licenseUsername={c4d_username}",
                f"g_licensePassword={c4d_password}",
                f"--ap_render={scene}",
                f"--ap_render_settings={render_settings}",
                f"--ap_out={out}",
            ], capture_output=True
        )
    else:
        c4d = subprocess.run(
            [
                c4d_path,
                f"--ap_render={scene}",
                f"--ap_render_settings={render_settings}",
                f"--ap_out={out}",
            ], capture_output=True
        )

    ui.finish_busy(scene)
    
    if c4d.returncode is not 0:
        print(c4d.stderr)
        ui.show_error("Failed to Render!", description="Check Anchorpoint Console")
    else:
        print(c4d.stdout)
        set_all_attributes()
        ui.show_success("Render Successful")
        ui.reload()


if (ap.check_application(c4d_path, f"Path to Cinema 4D's commandline tool is not correct. It is called Commandline.exe / Commandline.app. Please try again", "commandline")):
    ctx.run_async(render)
else:
    # Remove the path to c4d from the action settings so that the user must provide it again
    settings = aps.Settings(api)
    if settings:
        settings.remove("c4d")
        settings.store()
