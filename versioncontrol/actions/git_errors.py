from subprocess import call
import anchorpoint as ap
import platform, sys, os

script_dir = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, script_dir)
import vc.apgit.utility as utility
sys.path.remove(script_dir)

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

def _get_file_from_error(error_message: str):
    import re
    try:
        matches = re.findall(r"(?<=\s')[^']+(?=')", error_message)
        for match in matches:
            if "error" in match or "warning" in match:
                continue
            return match
    except:
        return None

def handle_error(e: Exception):
    try:
        message = e.stderr
    except:
        message = str(e)

    if "warning: failed to remove" in message or "error: unable to unlink" in message:
        print(message)
        file = _get_file_from_error(message)
        application = None
        if file:
            application = utility.get_locking_application(file)

        d = ap.Dialog()
        d.title = "Git: Could not Change Files"
        d.icon = ":/icons/versioncontrol.svg"

        if application:
            user_error = f"The file <b>{file}</b><br> could not be removed or changed becausethey are opened by the application <b>{application})</b>.<br>Please close the {application} and try again."
        else:
            user_error = f"The file <b>{file}</b><br> could not be removed or changed because you don't have permissions to write the file.<br>Please fix the permissions and try again."

        d.add_text(user_error)
        if platform.system() == "Darwin":
            d.add_info("See more details in the Python console <b>(CMD+SHIFT+P)</b>")
        else:
            d.add_info("See more details in the Python console <b>(CTRL+SHIFT+P)</b>")

        d.add_button("OK", callback=lambda d: d.close())
        d.show()

        return True

    if "Stash on branch" in message:
        ap.UI().show_info("You already have shelved files", "Commit your changed files and then try again", duration=10000)
        return True

    if "The following untracked working tree files would be overwritten by" in message:
        ap.UI().show_info("Files would be deleted", "This operation would delete files and we are not sure if this is intended. To clean your repository use the \"revert\" command instead.")
        return True
    
    return False