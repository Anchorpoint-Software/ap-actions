import anchorpoint as ap
import apsync as aps
import os, sys

ctx = ap.Context.instance()
project = aps.get_project(ctx.project_path)
ui = ap.UI()

if project is None:
    ui.show_info("Action only works with projects")
    sys.exit(0)
    
settings = project.get_metadata()

def contains_number(value):
    for character in value:
        if character.isdigit():
            return True
    return False

def copy():
    splitted_name = ctx.filename.split("_")
    lastSplitPart = splitted_name[len(splitted_name)-1]
    if(contains_number(lastSplitPart)):
        progress = ap.Progress("Publishing", "Creating a copy")
        splitted_name.pop()

        new_name = ""
        for i in splitted_name:
            new_name+=i
            new_name+="_"
        new_name = new_name[:-1]
        
        new_name_appendix = new_name

        try:
            new_name_appendix+=settings["publish_version_appendix"]
        except:
            pass

        new_location = ctx.folder

        try:
            if(settings["publish_file_location"] != ""):
                new_location=settings["publish_file_location"]
        except:
            new_location = ctx.folder        

        new_path = os.path.join(new_location,new_name_appendix+"."+ctx.suffix)

        aps.copy_file(ctx.path,new_path,overwrite=True)
        aps.set_attribute_text(new_path,"Source File",ctx.filename)
        
        ui.show_success(f"Published {new_name_appendix}",f"Published in {new_location}")
        progress.finish()

    else:
        ui.show_error("Not an increment","This file has no v001 or similar")
        return
    
ctx.run_async(copy) 
