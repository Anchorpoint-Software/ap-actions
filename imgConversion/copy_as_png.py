# This example demonstrates how to create a simple dialog in Anchorpoint
import anchorpoint as ap
import apsync as aps
import os 
import tempfile
import subprocess

def win_copy_image_to_clipboard(image_path):

    # adjust the path so that powershell understands it
    path = image_path.replace("\\","\\\\").replace("/","\\\\")

    # build your PowerShell command
    cmd = f'Get-ChildItem "{path}" | Set-Clipboard'

    # execute the command
    completed = subprocess.run(["powershell", "-Command",cmd], capture_output=True)
    return completed


def get_image(workspace_id,input_path):
    # start progress
    progress = ap.Progress("Copying image", "Processing", infinite=True)
    # create temporary folder
    output_folder = create_temp_directory()

    # generate the thumbnail which is a png file and put it in the temporary directory
    aps.generate_thumbnails([input_path],  output_folder, with_detail = False, with_preview = True, workspace_id = workspace_id)    

    # get the proper filename, rename it because the generated PNG file has a _pt appendix
    file_name = os.path.basename(input_path).split(".")[0]
    image_path = os.path.join(output_folder,file_name+str("_pt")+str(".png"))
    renamed_image_path = os.path.join(output_folder,file_name+str(".png"))
    os.rename(image_path,renamed_image_path)    

    # trigger the copy to clipboard function
    copy = win_copy_image_to_clipboard(renamed_image_path)
    
    if copy.returncode != 0:
        print("An error occured: %s", copy.stderr)
    else:
        ui = ap.UI()
        ui.show_success("Image copied to clipboard","Paste it as a PNG file") 

    progress.finish()

def create_temp_directory():
    # Create a temporary directory
    temp_dir = tempfile.mkdtemp()
    return temp_dir

ctx = ap.get_context()
ctx.run_async(get_image, ctx.workspace_id,ctx.path) 
