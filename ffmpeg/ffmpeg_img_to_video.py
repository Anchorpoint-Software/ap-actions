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
import mimetypes

ui = ap.UI()
ctx = ap.Context.instance()
FFMPEG_INSTALL_URL = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
ffmpeg_folder_path = "~/Documents/Anchorpoint/actions/ffmpeg"

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
    if len(selected_files) == 1 and mimetypes.guess_type(selected_files[0])[0].startswith('video'):
        progress_infinite = True
    else:
        progress_infinite = False

    # Show Progress
    progress = ap.Progress("Images to Video","Preparing...", infinite=progress_infinite, cancelable=True)

    # Provide FFmpeg with the set of selected files through the concat demuxer
    concat_file = concat_demuxer(selected_files, fps)

    arguments = [
            ffmpeg_path,                
            "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", concat_file,
            "-hide_banner",
            "-progress", "pipe:{self.pipe_write}",
            "-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2",
            "-fps_mode", "vfr",
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
    
    # progress bar calculation
    percentage = 0
    drop_frame = 0
    
    # progress bar
    for line in ffmpeg.stdout:   
        if 'drop_frames=' in line: 
            drop_frame = re.search('(\d+)', line).group()
             
        if 'frame=' in line and progress_infinite==False:
            current_frame = re.search('(\d+)', line).group()
            percentage = (int(current_frame)+int(drop_frame))/(len(selected_files)+1)
            progress.report_progress(percentage)
            progress.set_text(f"{int(percentage*100)}% encoded")
            
        if progress.canceled:
            ui.show_info("Canceled")
            os.system("taskkill /PID {}".format(ffmpeg.pid))
            # wait until subprocess terminates, then delete txt file
            ffmpeg.communicate()
            os.remove(concat_file)
            return
        
    # wait for subprocess to terminate
    ffmpeg.communicate()
    
    if ffmpeg.returncode != 0:
        print(ffmpeg.stderr)
        ui.show_error("Failed to export video", description="Check Anchorpoint Console")
    else:
        ui.show_success("Export Successful", description=f"Created {filename}.mp4")

    # Do some cleanup
    os.remove(concat_file)

def _install_ffmpeg_async():
    if not os.path.isdir(os.path.expanduser(ffmpeg_folder_path)):
        os.mkdir(os.path.expanduser(ffmpeg_folder_path))
    
    # download zip
    progress = ap.Progress("Installing FFMPEG", infinite = True)
    r = requests.get(FFMPEG_INSTALL_URL)
            
    # open zip file and extract ffmpeg.exe to the right folder
    z = zipfile.ZipFile(io.BytesIO(r.content))
    
    with z.open('ffmpeg-master-latest-win64-gpl/bin/ffmpeg.exe') as source:
        with open(_get_ffmpeg_cmddir(), "wb") as target:
            shutil.copyfileobj(source, target)

    progress.finish()
    ctx.run_async(ffmpeg_seq_to_video, ffmpeg_path, sorted(ctx.selected_files), path, fps)

def _install_ffmpeg(dialog):
    ctx.run_async(_install_ffmpeg_async)
    dialog.close()

def ffmpeg_install_dialog():
    dialog = ap.Dialog()
    dialog.title = "Install Conversion Tools"
    dialog.add_text("Anchorpoint's video conversion tools are based on FFmpeg.")
    dialog.add_info("When installing <a href=\"http://ffmpeg.org\">FFmpeg</a> you are accepting the <a href=\"http://www.gnu.org/licenses/old-licenses/lgpl-2.1.html\">license</a> of the owner.")
    dialog.add_button("Install", callback=_install_ffmpeg)
    dialog.show()
    
def _get_ffmpeg_cmddir():
    dir = os.path.expanduser(ffmpeg_folder_path)
    dir = os.path.join(dir, "ffmpeg.exe")
    return os.path.normpath(dir)
    
# First, check if the tool can be found on the machine
ffmpeg_path = None
if platform == "darwin":
    ffmpeg_path = ctx.inputs["ffmpeg_mac"]
elif platform == "win32":
    ffmpeg_path = _get_ffmpeg_cmddir()

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
    if not os.path.isfile(_get_ffmpeg_cmddir()):
        ctx.run_async(ffmpeg_install_dialog)
    else:
        # Convert the image sequence to a video
        # We don't want to block the Anchorpoint UI, hence we run on a background thread
        ctx.run_async(ffmpeg_seq_to_video, ffmpeg_path, sorted(ctx.selected_files), path, fps)
