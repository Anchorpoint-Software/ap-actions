import anchorpoint as ap
import apsync as aps
import os

ctx = ap.Context.instance()
settings = aps.Settings("ffmpeg_settings")

framerate_var = "25"
dropdown_var = "Same Folder"
path_var = "path"

def button_clicked(dialog):
    fps = dialog.get_value(framerate_var)
    dropdown = dialog.get_value(dropdown_var)
    path = dialog.get_value(path_var)
    
    if dropdown == "Same Folder":
        settings.remove("path")
    else:
        settings.set("path", path)
    
    settings.set("fps", fps)
    settings.store()
    dialog.close()
    
def input_callback(dialog, value):
    dialog.hide_row(path_var, value=="Same Folder")
    
def open_dialog():
    fps = settings.get("fps")
    path = settings.get("path")
    
    if fps == "":
        fps = ctx.inputs["fps"]
    
    if path == "":
        path = os.path.join(os.environ["HOMEPATH"], "Desktop")
    
    dialog = ap.Dialog()
    input_callback(dialog, dropdown_var)
    dialog.title = "Conversion Settings"
    dialog.add_text("Framerate \t").add_input(fps, var = framerate_var)
    dialog.add_text("Location \t").add_dropdown("Same Folder", ["Same Folder", "Custom Folder"], var = dropdown_var, callback=input_callback)
    dialog.add_text("Folder \t").add_input(path, browse=ap.BrowseType.Folder, var = path_var)
    dialog.add_button("Apply", callback=button_clicked)
    dialog.hide_row(path_var, True)

    if ctx.icon:
        dialog.icon = ctx.icon   
        
    dialog.show()

open_dialog()