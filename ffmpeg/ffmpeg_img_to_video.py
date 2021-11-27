import anchorpoint as ap
import apsync as aps
from sys import platform
import subprocess
import os
import random
import string


ui = ap.UI()
ctx = ap.Context.instance()
api = ctx.create_api()

def create_random_text():
    ran = "".join(random.choices(string.ascii_uppercase + string.digits, k=10))    
    return str(ran)

def concat_demuxer(selected_files, fps):
    # Create a file for ffmpeg within Anchorpoints temp directory. 
    # Use a random name so that we do not conflict with any other file
    output = os.path.join(ap.temp_dir(), f"{create_random_text()}.txt")

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
    def ffmpeg_seq_to_video_async():
        # Provide FFmpeg with the set of selected files through the concat demuxer
        concat_file = concat_demuxer(selected_files, fps)
        ffmpeg = subprocess.run(
            [
                ffmpeg_path,
                "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", concat_file,
                "-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2",
                "-vsync", "vfr",
                "-pix_fmt", "yuv420p",
                os.path.join(target_folder,"video.mp4"),
            ], capture_output=True
        )
        if ffmpeg.returncode is not 0:
            print(ffmpeg.stderr)
            ui.show_error("Failed to export video", description="Check Anchorpoint Console")
        else:
            ui.show_success("Export Successful", description="Created video.mp4")

        # Do some cleanup
        os.remove(concat_file)

    # We don't want to block the Anchorpoint UI, hence we run on a background thread
    ctx.run_async(ffmpeg_seq_to_video_async)

# First, check if the tool can be found on the machine
ffmpeg_path = None
if platform == "darwin":
    ffmpeg_path = ctx.inputs["ffmpeg_mac"]
elif platform == "win32":
    ffmpeg_path = ctx.inputs["ffmpeg_win"]

if (ap.check_application(ffmpeg_path, f"Could not find ffmpeg! Make sure ffmpeg is set up correctly in {ctx.yaml}")):
    if len(ctx.selected_files) > 0:
        # Convert the image sequence to a video
        ffmpeg_seq_to_video(ffmpeg_path, ctx.selected_files, ctx.folder, ctx.inputs["fps"])