from PySide2.QtWidgets import QApplication
import apsync as aps
import c4d
import sys
import argparse
import os

def get_next_object(op):
    if op == None:
        return None
    if op.GetDown():
        return op.GetDown()
    while not op.GetNext() and op.GetUp():
        op = op.GetUp()
    return op.GetNext()


def get_render_data(doc, name):
    if name == None:
        return doc.GetActiveRenderData()

    renderData = doc.GetFirstRenderData()
    if renderData == None:
        return
    while renderData:
        if renderData.GetName() == name:
            return renderData
        renderData = get_next_object(renderData)


def render(doc, rd):
    bmp = c4d.bitmaps.MultipassBitmap(
        int(rd[c4d.RDATA_XRES]), int(rd[c4d.RDATA_YRES]), c4d.COLORMODE_RGB
    )
    if bmp is None:
        raise RuntimeError("Failed to create the bitmap.")

    # Adds an alpha channel
    bmp.AddChannel(True, True)

    # Renders the document
    if (
        c4d.documents.RenderDocument(doc, rd.GetData(), bmp, c4d.RENDERFLAGS_EXTERNAL)
        != c4d.RENDERRESULT_OK
    ):
        raise RuntimeError("Failed to render the temporary document.")


def command_render_scene(scenePath, settingsName, outputPath):
    c4d.GePrint(
        f"Anchorpoint: Render Scene. Scene: {scenePath} Settings: {settingsName} OutputPath: {outputPath}"
    )
    # Load the document
    doc = c4d.documents.LoadDocument(
        scenePath, c4d.SCENEFILTER_OBJECTS | c4d.SCENEFILTER_MATERIALS
    )
    if doc is None:
        raise RuntimeError("Failed to load document.")

    c4d.documents.InsertBaseDocument(doc)

    rd = get_render_data(doc, settingsName)
    if rd is None:
        raise RuntimeError(f"Failed to load render settings {settingsName}.")

    # Patch output path of requested
    if outputPath != None:
        rd[c4d.RDATA_PATH] = outputPath

    render(doc, rd)
    c4d.documents.KillDocument(doc)


def command_export_fbx(scenePath, outPath):
    c4d.GePrint(f"Anchorpoint: Export FBX. Scene: {scenePath} Out: {outPath}")

    # Load the document
    doc = c4d.documents.LoadDocument(
        scenePath, c4d.SCENEFILTER_OBJECTS | c4d.SCENEFILTER_MATERIALS
    )
    if doc is None:
        raise RuntimeError("Failed to load document.")    

    # See https://plugincafe.maxon.net/topic/11623/fbx-export-plugin-option-setting-with-python/2
    fbxExportId = 1026370
    plug = c4d.plugins.FindPlugin(fbxExportId, c4d.PLUGINTYPE_SCENESAVER)
    if plug is None:
        raise RuntimeError("Failed to retrieve the fbx exporter.")

    data = dict()
    # Sends MSG_RETRIEVEPRIVATEDATA to fbx export plugin
    if not plug.Message(c4d.MSG_RETRIEVEPRIVATEDATA, data):
        raise RuntimeError("Failed to retrieve private data.")

    # BaseList2D object stored in "imexporter" key hold the settings
    fbxExport = data.get("imexporter", None)
    if fbxExport is None:
        raise RuntimeError("Failed to retrieve BaseContainer private data.")

    buildflag = c4d.BUILDFLAGS_NONE if c4d.GetC4DVersion() > 20000 else c4d.BUILDFLAGS_0
    doc.ExecutePasses(None, True, True, True, buildflag)

    # Finally export the document
    if not c4d.documents.SaveDocument(
        doc,
        outPath,
        c4d.SAVEDOCUMENTFLAGS_DONTADDTORECENTLIST,
        fbxExportId,
    ):
        raise RuntimeError("Failed to save the document.")

    c4d.documents.KillDocument(doc)

def handle_command_line(id, data):
    try:
        if id == c4d.C4DPL_COMMANDLINEARGS:
            parser = argparse.ArgumentParser(
                description="Anchorpoint C4D Command Line Bridge."
            )

            parser.add_argument("--ap_export_fbx", help="exports a scene as FBX")
            parser.add_argument("--ap_render", help="renders a scene")
            parser.add_argument(
                "--ap_render_settings", help="overwrites the render settings by name"
            )
            parser.add_argument("--ap_out", help="output file")

            args, unknown = parser.parse_known_args(
                sys.argv[0:]  # c4d skips the first arg for python
            )

            if args.ap_export_fbx and args.ap_out:
                command_export_fbx(args.ap_export_fbx, args.ap_out)
                c4d.GePrint(f"Anchorpoint: Command succeeded.")

            if args.ap_render:
                command_render_scene(
                    args.ap_render, args.ap_render_settings, args.ap_out
                )
                c4d.GePrint(f"Anchorpoint: Command succeeded.")

            return True
        return False
    except Exception as e:
        c4d.GePrint(e)
        return False


def PluginMessage(id, data):
    try:
        return handle_command_line(id, data)
    except Exception as e:
        c4d.GePrint(e)
        return False

def is_doc_saved(doc):
    return doc.GetDocumentPath() != ""

from applugin import ui, publish

class ExampleDialogCommand(c4d.plugins.CommandData):
    def __init__(self):
        super(ExampleDialogCommand, self).__init__()
        self.app = ui.get_qt_application()
        self.dialog = None
        self.api = aps.Api("Cinema 4D")

    def Execute(self, doc):
        if not doc or not is_doc_saved(doc):
            return False
        
        file = doc.GetDocumentPath() + "/" + doc.GetDocumentName()
        self.command = publish.PublishCommand(self.api, file)
        self.command.publish_file()

        return True 

    def GetState(self, doc):
        if not doc or not is_doc_saved(doc):
            return False

        file = doc.GetDocumentPath() + "/" + doc.GetDocumentName()

        # Checks apsync whether or not the folder has version control enabled
        if publish.is_versioning_enabled(self.api, doc.GetDocumentPath()):
            return c4d.CMD_ENABLED
        
        return False

if __name__ == "__main__":
    PLUGIN_ID = 424254
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
                                      help="Publishes the current file to Anchorpoint. Optionally creates a new increment",
                                      dat=ExampleDialogCommand(),
                                      icon=bmp)