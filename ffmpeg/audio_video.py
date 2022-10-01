import anchorpoint as ap
import apsync as aps
import os
import ffmpeg_helper

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
    dialog.set_value("filename", get_filename_text())

    
def create_dialog():
    settings = aps.Settings("audiovideo")
    remove_audio = settings.get("remove", False)
    settings.remove("filename")

    dialog = ap.Dialog()
    dialog.title = "Change Audio"

    dialog.add_text(get_filename_text(), var="filename")
    dialog.add_switch(var="remove", default=remove_audio, callback=update_dialog).add_text("Remove Audio")
    dialog.add_info("Remove the audio channels from the video, or replace the existing audio with new tunes")
    dialog.add_text("New Audio", var="newaudiotext").add_input(browse=ap.BrowseType.File, var="newaudioinput").hide_row(hide=remove_audio)
    dialog.add_info("Select an audio file (e.g. wav) that will become the new audio of the video file", var="newaudioinfo").hide_row(hide=remove_audio)

    dialog.add_button("Convert")

    dialog.show(settings)

ffmpeg_helper.guarantee_ffmpeg(create_dialog)