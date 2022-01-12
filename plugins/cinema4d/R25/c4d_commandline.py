import c4d
import argparse
import sys

class CommandLineHandler:
    def Execute(self, id, data):
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

                args, _ = parser.parse_known_args(
                    sys.argv[0:]  # c4d skips the first arg for python
                )

                if args.ap_export_fbx and args.ap_out:
                    self._CommandExportFbx(args.ap_export_fbx, args.ap_out)
                    c4d.GePrint(f"Anchorpoint: Command succeeded.")

                if args.ap_render:
                    self._CommandRenderScene(
                        args.ap_render, args.ap_render_settings, args.ap_out
                    )
                    c4d.GePrint(f"Anchorpoint: Command succeeded.")

                return True
            return False
        except Exception as e:
            c4d.GePrint(e)
            return False

    def _GetNextObject(self, op):
        if op == None:
            return None
        if op.GetDown():
            return op.GetDown()
        while not op.GetNext() and op.GetUp():
            op = op.GetUp()
        return op.GetNext()


    def _GetRenderData(self, doc, name):
        if name == None:
            return doc.GetActiveRenderData()

        renderData = doc.GetFirstRenderData()
        if renderData == None:
            return
        while renderData:
            if renderData.GetName() == name:
                return renderData
            renderData = self._GetNextObject(renderData)


    def _Render(self, doc, rd):
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


    def _CommandRenderScene(self, scenePath, settingsName, outputPath):
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

        rd = self._GetRenderData(doc, settingsName)
        if rd is None:
            raise RuntimeError(f"Failed to load render settings {settingsName}.")

        # Patch output path of requested
        if outputPath != None:
            rd[c4d.RDATA_PATH] = outputPath

        self._Render(doc, rd)
        c4d.documents.KillDocument(doc)


    def _CommandExportFbx(self, scenePath, outPath):
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