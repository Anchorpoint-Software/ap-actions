from PySide2.QtCore import Slot, Signal, QObject
from PySide2.QtGui import QPixmap
from PySide2.QtWidgets import QCheckBox, QDialog, QGridLayout, QLabel, QLayout, QLineEdit, QMessageBox, QPushButton

import sys
import tempfile
import os

from applugin import screenshot, ui
import apsync as aps

class _PublishDialog(QDialog):
    file_created = Signal(str)

    def __init__(self, api, file: str, img: QPixmap, parent=None):
        super(_PublishDialog, self).__init__(parent)

        self.api = api
        self.file = file
        
        self.setWindowTitle("Publish File")

        self.img = img
        self.imglabel = QLabel()
        self.imglabel.setPixmap(img.scaledToWidth(500))
        self.imglabel.setMaximumSize(500, 500)

        self.nextfile = aps.get_next_version_path(self.api, self.file)
        filename = os.path.split(self.file)[-1]
        nextfilename = os.path.split(self.nextfile)[-1]

        self.info = QLabel("Publish the file: " + filename)
        self.info.setToolTip(self.file)

        self.nextversion = QCheckBox("Create new version")
        self.nextversion.setChecked(True)
        self.nextversion.setToolTip("Saves the current file under the new name and opens the new file in the application")

        self.nextversionpreview = QLabel("Preview: " + nextfilename)
        self.nextversionpreview.setToolTip(self.nextfile)

        self.comment = QLineEdit()
        self.comment.setPlaceholderText("Enter a comment (optional)")
        self.comment.setMinimumWidth(250)

        self.publish = QPushButton("Publish")

        # Create layout and add widgets
        layout = QGridLayout()
        layout.addWidget(self.info, 0, 0, 1, 2)
        layout.addWidget(self.imglabel, 1, 0, 1, 2)
        layout.addWidget(self.comment, 2, 0, 1, 2)
        layout.addWidget(self.nextversion, 3, 0)
        layout.addWidget(self.nextversionpreview, 3, 1)
        layout.addWidget(self.publish, 4, 0, 1, 2)

        layout.setSizeConstraint(QLayout.SetFixedSize)

        # Set dialog layout
        self.setLayout(layout)

        # Add button signal to greetings slot
        self.publish.clicked.connect(self.publish_cb)

    def __set_comment(self):
        comment = None if len(self.comment.text()) == 0 else self.comment.text()
        aps.comment_version(self.api, self.file, comment)

    def __set_thumbnail(self):
        dir = tempfile.gettempdir()
        detail_thumbnail = os.path.join(dir, "detail.png")
        preview_thumbnail = os.path.join(dir, "preview.png")
        if self.img.save(detail_thumbnail) and self.img.scaledToWidth(256).save(preview_thumbnail):
            aps.attach_thumbnails(self.api, self.file, preview_thumbnail, detail_thumbnail)
            os.remove(preview_thumbnail)
            os.remove(detail_thumbnail)

    def __create_next_version(self):
        new_file = aps.create_next_version(self.api, self.file)
        self.file_created.emit(new_file)

    def publish_cb(self):
        self.__set_comment()
        self.__set_thumbnail()

        if self.nextversion.isChecked:
            self.__create_next_version()

        self.close()
        

class PublishCommand(QObject):
    file_created = Signal(str)

    def __init__(self, api, file):
        super(PublishCommand, self).__init__()
        self.api = api
        self.file = file

    @Slot()
    def __show_publish_dialog(self, img):
        self.publish_dialog = _PublishDialog(self.api, self.file, img)
        self.publish_dialog.file_created.connect(lambda x: self.file_created.emit(x))
        self.publish_dialog.show()
        pass

    def is_versioning_enabled(self):
        import os
        folder = aps.get_folder(self.api, os.path.dirname(self.file))
        if not folder: return False
        return folder.versioning_enabled

    def publish_file(self):
        if self.is_versioning_enabled():
            self.screenshot_dialog = screenshot.ScreenshotDialog()
            self.screenshot_dialog.image_captured.connect(self.__show_publish_dialog)
            self.screenshot_dialog.show()
        else:
            message = QMessageBox()
            message.setText("To publish a file to Anchorpoint you have to enable version control in the target folder.")
            message.exec_()
    
def file_created_cb(filepath: str):
    print (filepath)

if __name__ == '__main__':
    api = aps.Api("applugin")
    app = ui.get_qt_application()
    command = PublishCommand(api, "/Users/jochenhunz/Documents/Anchorpoint/scenes/Artist Sculpting/Scene_v0004.c4d")
    command.file_created.connect(file_created_cb)
    command.publish_file()
    sys.exit(app.exec_())