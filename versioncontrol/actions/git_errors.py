from subprocess import call
import anchorpoint as ap
import platform

def _guess_application(error_message: str):
    known_applications = {
        ".uasset": "Unreal Engine",
        ".umap": "Unreal Engine",
        
        ".meta": "Unity3D",
        ".unity": "Unity3D",
        ".unitypackage": "Unity3D",
        ".prefab": "Unity3D",
        
        ".blend": "Blender",
        ".c4d": "Cinema 4D",
        ".psd": "Photoshop"
    }

    for ext in known_applications:
        if ext in error_message:
            return known_applications[ext]
    return None

def handle_error(e: Exception):
    try:
        message = e.stderr
    except:
        message = str(e)

    if "warning: failed to remove" in message or "error: unable to unlink" in message:
        application = _guess_application(message)
        d = ap.Dialog()
        d.title = "Git: Could not Change Files"
        d.icon = ":/icons/versioncontrol.svg"

        if application:
            user_error = f"Some files could not be removed or changed because they are opened<br>by another application <i>(probably: {application})</i>.<br>Please close the application and try again."
        else:
            user_error ="Some files could not be removed or changed because they are opened by another application.<br>Please close the application and try again."

        d.add_text(user_error)
        if platform.system() == "Darwin":
            d.add_info("See more details in the Python console <b>(CMD+SHIFT+P)</b>")
        else:
            d.add_info("See more details in the Python console <b>(CTRL+SHIFT+P)</b>")

        d.add_button("OK", callback=lambda d: d.close())
        d.show()

        return True

    if "The following untracked working tree files would be overwritten by" in message:
        ap.UI().show_info("Files would be deleted", "This operation would delete files and we are not sure if this is intended. To clean your repository use the \"revert\" command instead.")
        return True
    
    return False