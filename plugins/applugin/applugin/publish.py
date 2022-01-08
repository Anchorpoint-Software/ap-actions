from PySide2.QtCore import Slot
from PySide2.QtGui import QPixmap
from applugin import screenshot, ui

from PySide2.QtWidgets import QCheckBox, QDialog, QGridLayout, QLabel, QLayout, QLineEdit, QPushButton, QSizePolicy
import sys

import apsync as aps

class PublishDialog(QDialog):
    def __init__(self, api, file, img: QPixmap, parent=None):
        super(PublishDialog, self).__init__(parent)

        self.api = api
        self.file = file
        
        self.setWindowTitle("Publish File")

        self.img = QLabel()
        self.img.setPixmap(img.scaledToWidth(500))
        self.img.setMaximumSize(500, 500)

        self.info = QLabel("Publish the File: " + file)
        self.saveinc = QCheckBox("Create new version")
        self.saveinc.setChecked(True)

        self.comment = QLineEdit()
        self.comment.setPlaceholderText("Enter a comment (optional)")
        self.comment.setMinimumWidth(250)

        self.publish = QPushButton("Publish")

        # Create layout and add widgets
        layout = QGridLayout()
        layout.addWidget(self.info, 0, 0)
        layout.addWidget(self.img, 1, 0)
        layout.addWidget(self.comment, 2, 0)
        layout.addWidget(self.saveinc, 3, 0)
        layout.addWidget(self.publish, 4, 0)

        layout.setSizeConstraint(QLayout.SetFixedSize)

        # Set dialog layout
        self.setLayout(layout)

        # Add button signal to greetings slot
        self.publish.clicked.connect(self.publish_cb)

    def publish_cb(self):
        print ("Hello %s" % self.publish.text())

class PublishCommand:
    def __init__(self, api, file):
        super(PublishCommand, self).__init__()
        self.api = api
        self.file = file

    @Slot()
    def __show_publish_dialog(self, img):
        self.publish_dialog = PublishDialog(self.api, self.file, img)
        self.publish_dialog.show()
        pass

    def publish_file(self):
        self.screenshot_dialog = screenshot.ScreenshotDialog()
        self.screenshot_dialog.show()
        self.screenshot_dialog.imagecaptured.connect(self.__show_publish_dialog)


def is_versioning_enabled(api, folderpath):
    folder = aps.get_folder(api, folderpath)
    if not folder: return False
    return folder.properties.versioning_enabled


if __name__ == '__main__':
    api = aps.Api("applugin")
    app = ui.get_qt_application()
    command = PublishCommand(api, "cube.c4d")
    command.publish_file()
    sys.exit(app.exec_())