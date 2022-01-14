import c4d
import os
import sys

directory, _ = os.path.split(__file__)
sys.path.insert(0, directory)

from c4d_commandline import CommandLineHandler
from c4d_publish_command import PublishCommandData

def PluginMessage(id, data):
    commandline = CommandLineHandler()
    return commandline.Execute(id, data)

if __name__ == "__main__":
    PLUGIN_ID = 1058846
    directory, _ = os.path.split(__file__)
    fn = os.path.join(directory, "res", "app_icon.ico")

    bmp = c4d.bitmaps.BaseBitmap()
    if bmp is None:
        raise MemoryError("Failed to create a BaseBitmap.")

    # Init the BaseBitmap with the icon
    if bmp.InitWith(fn)[0] != c4d.IMAGERESULT_OK:
        raise MemoryError("Failed to initialize the BaseBitmap.")


    c4d.plugins.RegisterCommandPlugin(id=PLUGIN_ID,
                                      str="Publish File to Anchorpoint",
                                      info=0,
                                      help="Saves the current scene, starts the screenshot tool and publishes the file to Anchorpoint. Optionally creates a new increment.",
                                      dat=PublishCommandData(),
                                      icon=bmp)