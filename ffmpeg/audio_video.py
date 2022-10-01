import platform
import anchorpoint as ap
import apsync as aps
import os
import ffmpeg_helper
import subprocess

ctx = ap.Context.instance()
ui = ap.UI()

input_path = ctx.path
input_folder = ctx.folder
input_filename = ctx.filename
input_suffix = ctx.suffix

def get_newpath():
    version = 1
    while True:
        new_path = os.path.join(input_folder, f"{input_filename}_v{str(version).zfill(3)}.{input_suffix}")
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
    dialog.hide_row("normalize", remove)
    dialog.hide_row("normalizeinfo", remove)
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
    normalize = dialog.get_value("normalize")
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

        if normalize:
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

    dialog.add_text(get_filename_text(), var="filename")
    dialog.add_switch(var="remove", default=remove_audio, callback=update_dialog).add_text("Remove Audio")
    dialog.add_info("Remove the audio channels from the video, or replace the existing audio with new tunes")
    dialog.add_text("New Audio", var="newaudiotext").add_input(browse=ap.BrowseType.File, var="newaudioinput", browse_path=input_folder).hide_row(hide=remove_audio)
    dialog.add_info("Select an audio file (e.g. wav) that will become the new audio of the video file", var="newaudioinfo").hide_row(hide=remove_audio)
    dialog.add_checkbox(var="normalize", default=True, callback=update_dialog).add_text("Normalize Length").hide_row(hide=remove_audio)
    dialog.add_info("When turned off, the length of the video can exceed the length of the audio and vice versa.", var="normalizeinfo").hide_row(hide=remove_audio)

    dialog.add_button("Convert", callback=convert)

    dialog.show(settings)

ffmpeg_helper.guarantee_ffmpeg(create_dialog)