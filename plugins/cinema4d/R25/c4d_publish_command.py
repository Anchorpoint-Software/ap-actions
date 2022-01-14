import sys
import c4d

from applugin import publish, core
import apsync as aps

class PublishCommandData(c4d.plugins.CommandData):
    def __init__(self):
        super(PublishCommandData, self).__init__()
        self.app = core.get_qt_application()
        self.dialog = None
        self.api = aps.Api("Cinema 4D")

    def IsDocSaved(self, doc):
        return doc.GetDocumentPath() != ""

    def NewVersionCreated(self, file: str):
        c4d.documents.LoadFile(file)
        pass

    def SaveDocument(self, doc, path):
        if not c4d.documents.SaveDocument(doc, path, c4d.SAVEDOCUMENTFLAGS_DONTADDTORECENTLIST, format=c4d.FORMAT_C4DEXPORT):
            raise RuntimeError("Failed to save the document.")

    def Execute(self, doc):
        if not doc or not self.IsDocSaved(doc):
            return False
        
        file = doc.GetDocumentPath() + "/" + doc.GetDocumentName()
        self.SaveDocument(doc, file)

        self.command = publish.PublishCommand(self.api, file)
        self.command.publish_file()

        self.command.file_created.connect(self.NewVersionCreated)

        return True 

    def GetState(self, doc):
        if not doc or not self.IsDocSaved(doc):
            return False
        
        return c4d.CMD_ENABLED