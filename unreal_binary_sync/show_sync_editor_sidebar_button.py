import anchorpoint as ap
import apsync as aps
import os

def on_is_action_enabled(path: str, type: ap.Type, ctx: ap.Context) :
    ctx = ap.get_context()
    project_path = ctx.project_path
    project_contains_editor = (
        os.path.exists(os.path.join(project_path, "Default.uprojectdirs")) and
        os.path.exists(os.path.join(project_path, "setup.bat"))
    )   
    return project_contains_editor