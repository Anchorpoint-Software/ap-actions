import re
import anchorpoint as ap
import apsync as aps
import subprocess
import os
import random
import string
import mimetypes
import platform
import tempfile

import ffmpeg_helper

ui = ap.UI()
ctx = ap.get_context()


def create_random_text():
    ran = "".join(random.choices(string.ascii_uppercase + string.digits, k=10))
    return str(ran)

def concat_demuxer(selected_files, fps):
    # Create a temporary file for ffmpeg
    temp_dir = tempfile.gettempdir()
    output = os.path.join(temp_dir, f"{create_random_text()}.txt")

    # See https://trac.ffmpeg.org/wiki/Concatenate
    with open(output, "a", encoding="utf-8") as file:
        duration = 1 / int(fps)
        for selected_file in selected_files:
            file.write(f"file '{selected_file}'\nduration {duration}\n")

    return output

def ffmpeg_seq_to_video(ffmpeg_path, target_folder, fps, selected_files, scale, audio_path=None):
    if len(selected_files) == 1 and mimetypes.guess_type(selected_files[0])[
        0
    ].startswith("video"):
        progress_infinite = True
        global filename
        filename = ctx.filename
    else:
        progress_infinite = False

    # Show Progress
    progress = ap.Progress(
        "Images to Video", "Preparing...", infinite=progress_infinite, cancelable=True
    )

    # Provide FFmpeg with the set of selected files through the concat demuxer
    concat_file = concat_demuxer(selected_files, fps)

    arguments = [
        ffmpeg_path,
        "-r", fps,
        "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", concat_file,
    ]

    if audio_path:
        arguments.extend(["-i", audio_path])

    arguments.extend([
        "-hide_banner",
        "-fps_mode", "vfr",
        "-pix_fmt", "yuv420p",
        "-vf", scale + ",pad=ceil(iw/2)*2:ceil(ih/2)*2",
    ])

    if audio_path:
        arguments.extend(["-c:a", "aac", "-shortest"])

    arguments.append(os.path.join(target_folder, f"{filename}.mp4"))

    is_exr = "exr" in ctx.suffix

    if is_exr:
        arguments.insert(1, "-apply_trc")
        arguments.insert(2, "iec61966_2_1")

    args = {
        "args": arguments,
        "stdout": subprocess.PIPE,
        "stderr": subprocess.PIPE,
        "stdin": subprocess.PIPE,
        "bufsize": 1,
        "universal_newlines": True,
    }

    if platform.system() == "Windows":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        args["startupinfo"] = startupinfo

    ffmpeg = subprocess.Popen(**args, encoding="utf-8")

    # progress bar calculation
    percentage = 0
    drop_frame = 0

    # progress bar
    output = ""
    for line in ffmpeg.stderr:
        output += line
        if not output.endswith("\n"):
            output += "\n"

        if "Error opening input file" in line and audio_path in line:
            print(line)
            ui.show_error("Unsupported Audio File", description="The specified audio file could not be opened. Please check the file path and format.")
            ffmpeg.terminate()
            ffmpeg.wait()
            os.remove(concat_file)
            return

        if "drop_frames=" in line:
            drop_frame = re.search(r"(\d+)", line).group()

        if "frame=" in line and not progress_infinite:
            current_frame = re.search(r"(\d+)", line).group()
            percentage = (int(current_frame) + int(drop_frame)) / (
                len(selected_files) + 1
            )
            progress.report_progress(percentage)
            progress.set_text(f"{int(percentage*100)}% encoded")

        if progress.canceled:
            ui.show_info("Canceled")
            ffmpeg.terminate()
            ffmpeg.wait()
            os.remove(concat_file)
            return

    ffmpeg.wait()

    if ffmpeg.returncode != 0:
        if "Error opening input files: Invalid data found when processing input" in output:
            ui.show_error("Unsupported Image or Audio File", description="The specified files could not be processed. Try another something else.")
        else:
            print(output)
            ui.show_error("Failed to export video", description="Check Anchorpoint Console")
    else:
        ui.show_success("Export Successful", description=f"Created {filename}.mp4")

    # Do some cleanup
    os.remove(concat_file)

def get_filename():
    try:
        filename = ctx.filename.rstrip(string.digits).rstrip("-,.")
        if filename == "":
            filename = ctx.filename
    except:
        filename = ctx.filename
    return filename

def main():
    global filename
    filename = get_filename()

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
            scale = "scale=w=1280:h=720:force_original_aspect_ratio=decrease"
        elif resolution == "Full HD (1920x1080)":
            scale = "scale=w=1920:h=1080:force_original_aspect_ratio=decrease"
        elif resolution == "2K (2048x1556)":
            scale = "scale=w=2048:h=1556:force_original_aspect_ratio=decrease"
        elif resolution == "4K (4096x3112)":
            scale = "scale=w=4096:h=3112:force_original_aspect_ratio=decrease"
        else:
            scale = "scale=-1:-1"

        ffmpeg_path = ffmpeg_helper.get_ffmpeg_fullpath()
        
        # Get audio track from settings
        add_audio = settings.get("add_audio", False)
        audio_path = settings.get("audio_track", "") if add_audio else None
        
        ffmpeg_helper.guarantee_ffmpeg(
            ffmpeg_seq_to_video, ffmpeg_path, path, fps, sorted(ctx.selected_files), scale, audio_path
        )

def run_action(ext_ctx,ext_ui):
    global ctx 
    ctx = ext_ctx
    global ui
    ui = ext_ui
    main()

if __name__ == "__main__":
    main()
