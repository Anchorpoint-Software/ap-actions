from applugin import core
if __name__ == '__main__':
    core.initialize()

from PySide2.QtCore import Slot, Signal, QObject
from PySide2.QtGui import QPixmap
from PySide2.QtWidgets import QCheckBox, QDialog, QGridLayout, QLabel, QLayout, QLineEdit, QMessageBox, QPushButton

import sys
import tempfile
import os

from applugin import screenshot
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

        # Retrieve the next path of the next version that will be created once the user clicks "publish"
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

        # Add button signal to publish_cb slot
        self.publish.clicked.connect(self.publish_cb)

    def __set_comment(self):
        comment = None if len(self.comment.text()) == 0 else self.comment.text()
        aps.comment_version(self.api, self.file, comment)

    def __set_thumbnail(self):
        # First, we save the QPixmap to a temporary directory in high resolution and scaled down for a quick preview
        dir = tempfile.gettempdir()
        detail_thumbnail = os.path.join(dir, "detail.png")
        preview_thumbnail = os.path.join(dir, "preview.png")
        if self.img.save(detail_thumbnail) and self.img.scaledToWidth(256).save(preview_thumbnail):
            # Then, we attach the newly saved images to the file in Anchorpoint. After that, we can cleanup the temporary files
            aps.attach_thumbnails(self.api, self.file, preview_thumbnail, detail_thumbnail)
            os.remove(preview_thumbnail)
            os.remove(detail_thumbnail)

    def __create_next_version(self):
        new_file = aps.create_next_version(self.api, self.file)
        self.file_created.emit(new_file)

    @Slot()
    def publish_cb(self):
        self.__set_comment()
        self.__set_thumbnail()

        if self.nextversion.isChecked:
            self.__create_next_version()

        self.close()
        

class PublishCommand(QObject):
    '''
    The PublishCommand invokes a screenshot tool so that the user can provide a visual indication of what has changed. 
    It allows the user to optionally set a commentary as well. By default, the PublishCommand will create the next version of the file.
    Connect to the file_created signal to get informed when the aforementioned next version has been created.

    Attributes:
        file_created (Signal): Connect to this Signal to get informed when a new version of the file was created. Use this to load the new file in the application

    Example:
        >>> from applugin import publish
        >>> import apsync
        >>> api = apsync.Api("Blender")
        >>> command = publish.PublishCommand(api, path_to_file)
        >>> command.publish_file()
    '''
    file_created = Signal(str)

    def __init__(self, api, file):
        '''
        Args:
            api (apsync.Api): Anchorpoint Api object
            file (str): The (absolute) path to the file that should be published
        '''
        super(PublishCommand, self).__init__()
        self.api = api
        self.file = file

    def is_versioning_enabled(self):
        '''
        Checks whether or not incremental version control is enabled on the target folder
        
        Returns:
            True when version control is enabled, False otherwise
        '''

        import os
        folder = aps.get_folder(self.api, os.path.dirname(self.file))
        if not folder: return False
        return folder.versioning_enabled

    def publish_file(self):
        '''
        Shows a screenshot tool and a Dialog to the user. Publishes the file if the user wants to.
        Informs the user when version control is disabled.
        Emits the file_created Signal when a new version of the file has been created.

        Example:
            >>> command = publish.PublishCommand(api, path_to_file)
            >>> command.file_created.connect(new_file_created_callback)
            >>> command.publish_file()
        '''

        if self.is_versioning_enabled():
            self.screenshot_dialog = screenshot.ScreenshotDialog()
            self.screenshot_dialog.image_captured.connect(self.__show_publish_dialog)
            self.screenshot_dialog.show()
        else:
            message = QMessageBox()
            message.setText("To publish a file to Anchorpoint you have to enable version control in the target folder.")
            message.exec_()

    @Slot()
    def __show_publish_dialog(self, img):
        self.publish_dialog = _PublishDialog(self.api, self.file, img)
        self.publish_dialog.file_created.connect(lambda x: self.file_created.emit(x))
        self.publish_dialog.show()
        pass
    
def file_created_cb(filepath: str):
    print (filepath)

if __name__ == '__main__':
    api = aps.Api("applugin")
    core.initialize()
    app = core.get_qt_application()
    command = PublishCommand(api, "scene.blend")
    command.file_created.connect(file_created_cb)
    command.publish_file()
    sys.exit(app.exec_())