from typing import cast
import anchorpoint as ap
import apsync as aps
import os
import platform
import ffmpeg_img_to_video

ctx = ap.get_context()
settings = aps.Settings("ffmpeg_settings")
project = aps.get_project(ctx.path)

framerate_var = "25"
location_var = "Same Folder"
path_var = "path"
resolution_var = "Original"
audio_track_var = "audio_track"
add_audio_switch_var = "add_audio_switch"


def button_clicked(dialog):
    fps = dialog.get_value(framerate_var)
    location = dialog.get_value(location_var)
    path = dialog.get_value(path_var)
    resolution = dialog.get_value(resolution_var)
    audio_track = dialog.get_value(audio_track_var)
    add_audio = dialog.get_value(add_audio_switch_var)

    if location == "Same Folder":
        settings.remove("path")
    else:
        settings.set("path", path)

    settings.set("fps", fps)
    settings.set("location", location)
    settings.set("resolution", resolution)
    settings.set("audio_track", audio_track)
    settings.set("add_audio", add_audio)

    settings.store()
    dialog.close()
    ffmpeg_img_to_video.run_action(ctx,ap.UI())


def input_callback(dialog, value):
    dialog.hide_row(path_var, value == "Same Folder")


def add_audio_callback(dialog, value):
    dialog.set_enabled(audio_track_var, value)


def open_dialog():
    fps = settings.get("fps")
    location = settings.get("location")
    resolution = settings.get("resolution")
    path = settings.get("path")
    audio_track = cast(str, settings.get("audio_track"))
    add_audio = settings.get("add_audio", False)
    location_bool = True

    if fps == "":
        fps = ctx.inputs["fps"]

    if location == "":
        location = location_var
    elif location == "Custom Folder":
        location_bool = False

    if resolution == "":
        resolution = "Original"

    if path == "":
        if platform.system() == "Darwin":
            path = os.path.expanduser("~/Desktop")
        else:
            path = os.path.join(os.environ["HOMEPATH"], "Desktop")

    if audio_track == "":
        audio_track = ""

    dialog = ap.Dialog()
    input_callback(dialog, location_var)
    dialog.title = "Conversion Settings"
    dialog.add_text("Framerate", width=88).add_input(fps, var=framerate_var, width=320)
    dialog.add_text("Location", width=88).add_dropdown(
        location,
        ["Same Folder", "Custom Folder"],
        var=location_var,
        callback=input_callback,
        width=320
    )
    dialog.add_text("Folder", width=88).add_input(
        path, browse=ap.BrowseType.Folder, var=path_var
    )
    dialog.add_text("Resolution", width=88).add_dropdown(
        resolution,
        [
            "Original",
            "HD (1280x720)",
            "Full HD (1920x1080)",
            "2K (2048x1556)",
            "4K (4096x3112)",
        ],
        var=resolution_var,
        width=320
    )
    dialog.add_info("Adjusts the video to the smaller height or width")
    dialog.add_switch(
        text="Add Audio Track",
        var=add_audio_switch_var,
        default=add_audio,
        callback=add_audio_callback
    )

    project_path = ""
    if audio_track:
        project_path = os.path.dirname(audio_track)
    elif project:
        project_path = project.path

    dialog.add_text("Audio Track", width=88).add_input(
        audio_track, placeholder=".../audio/shot_0010.wav", browse=ap.BrowseType.File,
        browse_path=project_path, var=audio_track_var, enabled=add_audio, width=223
    )
    
    dialog.add_info("Adds an audio track and adjusts it to the length of the sequence")
    dialog.add_button("Convert", callback=button_clicked)
    dialog.hide_row(path_var, location_bool)

    if ctx.icon:
        dialog.icon = ctx.icon

    dialog.show()

def main():  
    open_dialog()

if __name__ == "__main__":
    main()