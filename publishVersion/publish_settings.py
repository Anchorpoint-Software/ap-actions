from fileinput import filename
import anchorpoint as ap
import apsync as aps
import os, sys

ctx = ap.Context.instance()
project = aps.get_project(ctx.path)
ui = ap.UI()
if project is None:
    ui.show_info("Action only works with projects")
    sys.exit(0)

settings = project.get_metadata()

def store_settings(dialog):
    settings["publish_version_appendix"] = dialog.get_value("appendix_var")
    settings["checkbox"] = str(dialog.get_value("checkbox_var"))
    if(dialog.get_value("checkbox_var") == True):
        settings["publish_file_location"] = dialog.get_value("location_var")
    else:
        settings["publish_file_location"] = ""

    project.update_metadata(settings)
    dialog.close()


def create_dialog():
    def checkBoxChecked(dialog,value):
        dialog.set_enabled("location_var",value)
        pass

    checkbox_default = "False"
    try:
        checkbox_default=settings["checkbox"]
    except:
        pass    

    path = ""
    try: 
        path=settings["publish_file_location"]
    except:
        pass

    appendix = ""
    try: 
        appendix=settings["publish_version_appendix"]
    except:
        pass

    dialog = ap.Dialog()
    dialog.title = "Referenced Model Settings"
    dialog.add_text("Copy into a dedicated Folder").add_checkbox(var="checkbox_var",callback = checkBoxChecked,default=(checkbox_default=="True"))
    dialog.add_text("Folder\t    ").add_input(path,placeholder = "published_versions", browse=ap.BrowseType.Folder,browse_path=project.path, var="location_var", enabled = False)
    dialog.add_text("Appendix\t    ").add_input(appendix,placeholder = "_published",var="appendix_var", enabled = True)
    dialog.add_info("What should follow after the name without increment. E.g. <b>character_rig_v023.blend</b> <br>becomes <b>character_rig_published.blend</b>")

    if ctx.icon:
        dialog.icon = ctx.icon    

    dialog.add_button("Apply", callback=store_settings)
    dialog.show()



create_dialog()