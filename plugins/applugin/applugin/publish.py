from PySide2.QtCore import QRect
from applugin import screenshot, ui

from PySide2.QtWidgets import QCheckBox, QDialog, QGridLayout, QLabel, QLayout, QLineEdit, QPushButton, QVBoxLayout
import sys

import apsync as aps

class PublishDialog(QDialog):
    def __init__(self, api, file, parent=None):
        super(PublishDialog, self).__init__(parent)

        self.api = api
        self.file = file

        self.setWindowTitle("Publish File")

        self.info = QLabel("Publish the File: " + file)
        self.saveinc = QCheckBox("Create new version")
        self.saveinc.setChecked(True)

        self.comment = QLineEdit("Enter a comment (optional)")
        self.comment.setMinimumWidth(250)

        self.publish = QPushButton("Publish")

        # Create layout and add widgets
        layout = QGridLayout()
        layout.addWidget(self.info, 0, 0)
        layout.addWidget(self.comment, 1, 0)
        layout.addWidget(self.saveinc, 2, 0)
        layout.addWidget(self.publish, 3, 0)

        layout.setSizeConstraint(QLayout.SetFixedSize)

        # Set dialog layout
        self.setLayout(layout)

        # Add button signal to greetings slot
        self.publish.clicked.connect(self.publish_cb)

    def publish_cb(self):
        print ("Hello %s" % self.publish.text())

def is_versioning_enabled(api, folderpath):
    folder = aps.get_folder(api, folderpath)
    if not folder: return False
    return folder.properties.versioning_enabled

def publish_file(api, file):
    sst = screenshot.ScreenshotWindow()
    sst.show()
    return sst
    #screenshot_tool.imagecaptured.connect(store_screenshot)

    dialog = PublishDialog(api, file)
    dialog.show()
    return dialog

if __name__ == '__main__':
    api = aps.Api("applugin")
    app = ui.get_qt_application()
    dialog = publish_file(api, "cube.c4d")
    sys.exit(app.exec_())