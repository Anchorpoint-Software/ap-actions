import re
import anchorpoint as ap
import apsync as aps
from sys import platform
import subprocess
import os
import random
import string
import zipfile
import requests
import shutil
import io

ui = ap.UI()
ctx = ap.Context.instance()
FFMPEG_INSTALL_URL = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"

try:
    filename = ctx.filename.split("_")
    filename.pop()
    filename = "_".join(filename) if len(filename) > 1 else ctx.filename
except:
    filename = ctx.filename

is_exr = "exr" in ctx.suffix

def create_random_text():
    ran = "".join(random.choices(string.ascii_uppercase + string.digits, k=10))    
    return str(ran)

def concat_demuxer(selected_files, fps):
    # Create a file for ffmpeg within Anchorpoints temp directory. 
    # Use a random name so that we do not conflict with any other file
    output = os.path.join(ctx.folder, f"{create_random_text()}.txt")

    # See https://trac.ffmpeg.org/wiki/Concatenate
    file = open(output, "a")
    duration = 1 / int(fps)
    for selected_file in selected_files:
        file.write("file '" + selected_file + f"'\nduration {duration}\n")

    # From the ffmpeg documentation: due to a quirk, the last image has to be specified twice
    file.write("file '" + selected_files[-1] + "'\n")
    file.close()
    return output

def ffmpeg_seq_to_video(ffmpeg_path, selected_files, target_folder, fps):
    # check for ffmpeg.exe and download if missing
    if not os.path.isfile(ctx.inputs["ffmpeg_win"]):
        install_ffmpeg()
        
    # check if its a video (one file)
    p_infinite = False
    
    if len(selected_files) == 1:
        p_infinite = True
        
    # Show Progress
    progress = ap.Progress("FFmpeg", "Converting Sequence to Video", infinite=p_infinite)

    # Provide FFmpeg with the set of selected files through the concat demuxer
    concat_file = concat_demuxer(selected_files, fps)

    arguments = [
            ffmpeg_path,                
            "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", concat_file,
            "-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2",
            "-vsync", "vfr",
            "-pix_fmt", "yuv420p",
            os.path.join(target_folder,f"{filename}.mp4"),
        ]
    if is_exr:
        arguments.insert(1,"-apply_trc")
        arguments.insert(2,"iec61966_2_1")

    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

    ffmpeg = subprocess.Popen(
        args=arguments, 
        startupinfo=startupinfo, 
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        stdin=subprocess.PIPE,
        bufsize=1,
        universal_newlines=True
    )
    
    # progress bar
    for line in ffmpeg.stdout:
        if 'frame=' in line:
            current_frame = re.search(r'\d+', line).group()
            percentage = int(current_frame)/(len(selected_files)+1)
            progress.report_progress(percentage)
        
    # wait for subprocess to terminate
    ffmpeg.communicate()
    
    if ffmpeg.returncode != 0:
        print(ffmpeg.stderr)
        ui.show_error("Failed to export video", description="Check Anchorpoint Console")
    else:
        ui.show_success("Export Successful", description="Created video.mp4")

    # Do some cleanup
    os.remove(concat_file)

def install_ffmpeg(dialog):
    # download zip
    progress = ap.Progress("Loading FFMPEG", infinite = True)
    r = requests.get(FFMPEG_INSTALL_URL)
            
    # open zip file and extract ffmpeg.exe to the right folder
    z = zipfile.ZipFile(io.BytesIO(r.content))
    
    with z.open('ffmpeg-master-latest-win64-gpl/bin/ffmpeg.exe') as source:
        with open(ctx.inputs["ffmpeg_win"], "wb") as target:
            shutil.copyfileobj(source, target)

    progress.finish()
    dialog.close()
    
    ctx.run_async(ffmpeg_seq_to_video, ffmpeg_path, sorted(ctx.selected_files), path, fps)

def ffmpeg_install_dialog():
    dialog = ap.Dialog()
    dialog.title = "Install FFmpeg"
    dialog.add_text("To use Anchorpoint with FFmpeg you have to install FFmpeg.")
    dialog.add_info("When installing FFmpeg you are accepting the <a href=\"https://raw.githubusercontent.com/git-for-windows/git/main/COPYING\">license</a> of the owner.")
    dialog.add_button("Install", callback=install_ffmpeg)
    dialog.show()
    
# First, check if the tool can be found on the machine
ffmpeg_path = None
if platform == "darwin":
    ffmpeg_path = ctx.inputs["ffmpeg_mac"]
elif platform == "win32":
    ffmpeg_path = ctx.inputs["ffmpeg_win"]

if len(ctx.selected_files) > 0:
    settings = aps.Settings("ffmpeg_settings")
    
    # get settings from the ffmpeg settings menu
    fps = settings.get("fps")
    if fps == "":
        fps = ctx.inputs["fps"]
    
    path = settings.get("path")
    if path == "":
        path = ctx.folder
        
    # check for ffmpeg.exe and download if missing
    if not os.path.isfile(ctx.inputs["ffmpeg_win"]):
        ctx.run_async(ffmpeg_install_dialog)
    else:
        # Convert the image sequence to a video
        # We don't want to block the Anchorpoint UI, hence we run on a background thread
        ctx.run_async(ffmpeg_seq_to_video, ffmpeg_path, sorted(ctx.selected_files), path, fps)
