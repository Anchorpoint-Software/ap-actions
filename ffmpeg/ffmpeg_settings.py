import anchorpoint as ap
import apsync as aps
import os, platform

ctx = ap.get_context()
settings = aps.Settings("ffmpeg_settings")

framerate_var = "25"
location_var = "Same Folder"
path_var = "path"
resolution_var = "Original"

def button_clicked(dialog):
    fps = dialog.get_value(framerate_var)
    location = dialog.get_value(location_var)
    path = dialog.get_value(path_var)
    resolution = dialog.get_value(resolution_var)
    
    if location == "Same Folder":
        settings.remove("path")
    else:
        settings.set("path", path)
    
    settings.set("fps", fps)
    settings.set("location", location)
    settings.set("resolution", resolution)

    settings.store()
    dialog.close()
    
def input_callback(dialog, value):
    dialog.hide_row(path_var, value=="Same Folder")
    
def open_dialog():
    fps = settings.get("fps")
    location = settings.get("location")
    resolution = settings.get("resolution")
    path = settings.get("path")
    location_bool = True
    
    if fps == "":
        fps = ctx.inputs["fps"]
        
    if location == "":
        location = location_var
    elif location == "Custom Folder":
        location_bool = False

    if resolution == "":
        resolution = "Original"
            
    
    if path == "":
        if platform.system() == "Darwin":
            path = os.path.expanduser("~/Desktop")
        else:    
            path = os.path.join(os.environ["HOMEPATH"], "Desktop")
    
    dialog = ap.Dialog()
    input_callback(dialog, location_var)
    dialog.title = "Conversion Settings"
    dialog.add_text("Framerate \t").add_input(fps, var = framerate_var)
    dialog.add_text("Location \t").add_dropdown(location, ["Same Folder", "Custom Folder"], var = location_var, callback=input_callback)
    dialog.add_text("Folder \t").add_input(path, browse=ap.BrowseType.Folder, var = path_var)
    dialog.add_text("Resolution \t").add_dropdown(resolution, ["Original","HD (1280x720)", "Full HD (1920x1080)","2K (2048x1556)","4K (4096x3112)"], var = resolution_var)
    dialog.add_info("Adjusts the video to the smaller height or width")
    dialog.add_button("Apply", callback=button_clicked)
    dialog.hide_row(path_var, location_bool)

    if ctx.icon:
        dialog.icon = ctx.icon   
        
    dialog.show()

open_dialog()