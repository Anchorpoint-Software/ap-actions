import re
import anchorpoint as ap
import apsync as aps
import subprocess
import os
import random
import string
import mimetypes
import platform

import ffmpeg_helper

ui = ap.UI()
ctx = ap.get_context()

try:
    filename = ctx.filename.rstrip(string.digits).rstrip("-,.")
    if filename == "":
        filename = ctx.filename
except:
    filename = ctx.filename

is_exr = "exr" in ctx.suffix

def create_random_text():
    ran = "".join(random.choices(string.ascii_uppercase + string.digits, k=10))    
    return str(ran)

def concat_demuxer(selected_files, fps):
    # Create a temporary file for ffmpeg within the directory. 
    # Use a random name so that we do not conflict with any other file
    output = os.path.join(ctx.folder, f"{create_random_text()}.txt")

    # See https://trac.ffmpeg.org/wiki/Concatenate
    file = open(output, "a")
    duration = 1 / int(fps)
    for selected_file in selected_files:
        file.write("file '" + selected_file + f"'\nduration {duration}\n")

    file.close()
    return output

def ffmpeg_seq_to_video(ffmpeg_path, target_folder, fps, selected_files, scale): 
    if len(selected_files) == 1 and mimetypes.guess_type(selected_files[0])[0].startswith('video'):
        progress_infinite = True
        global filename
        filename = ctx.filename
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
            "-vf",scale+" ,pad=ceil(iw/2)*2:ceil(ih/2)*2",
            os.path.join(target_folder,f"{filename}.mp4"),
        ]
    if is_exr:
        arguments.insert(1,"-apply_trc")
        arguments.insert(2,"iec61966_2_1")

    args = {
            "args":arguments, 
            "stdout":subprocess.PIPE,
            "stderr":subprocess.STDOUT,
            "stdin":subprocess.PIPE,
            "bufsize":1,
            "universal_newlines":True
        }

    if platform.system() == "Windows":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW 

        args["startupinfo"] = startupinfo 

    ffmpeg = subprocess.Popen(**args)
    
    # progress bar calculation
    percentage = 0
    drop_frame = 0
    
    # progress bar
    output = ""
    for line in ffmpeg.stdout:   
        output = output + line
        if not output.endswith("\n"):
            output = output + "\n"
            
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
        print(output)
        ui.show_error("Failed to export video", description="Check Anchorpoint Console")
    else:
        ui.show_success("Export Successful", description=f"Created {filename}.mp4")

    # Do some cleanup
    os.remove(concat_file)
    
if len(ctx.selected_files) > 0:
    settings = aps.Settings("ffmpeg_settings")
    
    # get settings from the ffmpeg settings menu
    fps = settings.get("fps")
    if fps == "":
        fps = ctx.inputs["fps"]
    
    path = settings.get("path")
    if path == "":
        path = ctx.folder

    resolution = str(settings.get("resolution"))
    if resolution == "HD (1280x720)":
        scale="scale=w=1280:h=720:force_original_aspect_ratio=decrease"
    elif resolution == "Full HD (1920x1080)":
        scale = "scale=w=1920:h=1080:force_original_aspect_ratio=decrease"
    elif resolution == "2K (2048x1556)":
        scale = "scale=w=2048:h=1556:force_original_aspect_ratio=decrease"
    elif resolution == "4K (4096x3112)":
        scale = "scale=w=4096:h=3112:force_original_aspect_ratio=decrease"
    else:
        scale = "scale=-1:-1"

    ffmpeg_path = ffmpeg_helper.get_ffmpeg_fullpath()
    ffmpeg_helper.guarantee_ffmpeg(ffmpeg_seq_to_video, ffmpeg_path, path, fps, sorted(ctx.selected_files),scale)
