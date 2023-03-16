import platform
import anchorpoint as ap
import apsync as aps
import os
import ffmpeg_helper
import subprocess

ctx = ap.get_context()
ui = ap.UI()

input_path = ctx.path
input_folder = ctx.folder
input_filename = ctx.filename
input_suffix = ctx.suffix

def get_newpath():
    input_filename_no_version = input_filename
    version_string = ""
    
    for c in reversed(input_filename_no_version):
        if c.isnumeric():
            version_string = c + version_string
        else:
            break

    version = 1
    number_of_version_digits = len(version_string)
    if number_of_version_digits > 0:
        input_filename_no_version = input_filename_no_version[0:-number_of_version_digits]
        if input_filename_no_version.endswith("v"):
            input_filename_no_version = input_filename_no_version[0:-1]

        if input_filename_no_version.endswith("_"):
            input_filename_no_version = input_filename_no_version[0:-1]

        try:
            version = int(version_string)
            version = version + 1
        except:
            pass
    else:
        number_of_version_digits = 3

    while True:
        new_path = os.path.join(input_folder, f"{input_filename_no_version}_v{str(version).zfill(number_of_version_digits)}.{input_suffix}")
        if not os.path.exists(new_path): 
            return new_path
        else:
            version = version + 1

def get_filename_text():
    new_path = get_newpath()
    new_filename = os.path.basename(new_path)
    return f"This will create a new file: <b>{new_filename}</b>"

def update_dialog(dialog: ap.Dialog, value = None):
    remove = dialog.get_value("remove")
    dialog.hide_row("newaudiotext", remove)
    dialog.hide_row("newaudioinfo", remove)
    dialog.hide_row("longest", remove)
    dialog.hide_row("longestinfo", remove)
    dialog.set_value("filename", get_filename_text())

def run_ffmpeg(arguments, remove_audio):
    ui.show_busy(input_path)
    platform_args = {}
    if platform.system() == "Windows":
        from subprocess import CREATE_NO_WINDOW
        platform_args = {"creationflags":CREATE_NO_WINDOW}
        
    try:
        subprocess.check_call(arguments, **platform_args)
        if remove_audio:
            ui.show_success("Audio Removed")
        else:
            ui.show_success("Audio Changed")
    except Exception as e:
        if remove_audio:
            ui.show_error("Could not remove audio")
        else:
            ui.show_error("Could not change audio", "Make sure you have selected a valid audio file")
    finally:
        ui.finish_busy(input_path)

def convert(dialog: ap.Dialog):
    remove_audio = dialog.get_value("remove")
    longest = dialog.get_value("longest")
    audio = dialog.get_value("newaudioinput")
    ffmpeg_path = ffmpeg_helper.get_ffmpeg_fullpath()
    new_path = get_newpath()

    if remove_audio:
        arguments = [
            ffmpeg_path,                
            "-i", input_path,
            "-c", "copy",
            "-map", "0:v:0",
            new_path
        ]
    else:
        arguments = [
            ffmpeg_path,                
            "-i", input_path,
            "-i", audio,
            "-map", "0:v:0",
            "-map", "1:a:0"
        ]

        if input_suffix == "mp4":
            arguments.append("-c:v")
            arguments.append("copy")
            arguments.append("-c:a")
            arguments.append("aac")
        else:
            arguments.append("-c")
            arguments.append("copy")

        if not longest:
            arguments.append("-shortest")

        arguments.append(new_path)

    dialog.close()
    ctx.run_async(run_ffmpeg, arguments, remove_audio)

def create_dialog():
    settings = aps.Settings("audiovideo")
    remove_audio = settings.get("remove", False)
    settings.remove("filename")

    dialog = ap.Dialog()
    dialog.title = "Change Audio"
    dialog.icon = os.path.join(ctx.yaml_dir, "icons/audio.svg")
    dialog.add_text(get_filename_text(), var="filename")
    dialog.add_switch(var="remove", default=remove_audio, callback=update_dialog).add_text("Remove Audio")
    dialog.add_info("Remove the audio channels from the video, or replace the existing audio with new tunes")
    dialog.add_text("New Audio", var="newaudiotext").add_input(browse=ap.BrowseType.File, var="newaudioinput", browse_path=input_folder).hide_row(hide=remove_audio)
    dialog.add_info("Select an audio file (e.g. wav) that will become the new audio of the video file", var="newaudioinfo").hide_row(hide=remove_audio)
    dialog.add_checkbox(var="longest", default=True, callback=update_dialog).add_text("Take longest length").hide_row(hide=remove_audio)
    dialog.add_info("Fits the final result to the longer file (video or audio). Otherwise it cuts off the rest", var="longestinfo").hide_row(hide=remove_audio)

    dialog.add_button("Convert", callback=convert)

    dialog.show(settings)

ffmpeg_helper.guarantee_ffmpeg(create_dialog)