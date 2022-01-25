try:
    from applugin import core
except:
    import sys, os
    sys.path.insert(0, os.path.dirname(__file__) + "/..")
    from applugin import core
    
from PySide2.QtCore import Slot, Signal, QObject, Qt
from PySide2.QtGui import QPixmap, QIcon
from PySide2.QtWidgets import QCheckBox, QDialog, QGridLayout, QLabel, QLayout, QTextEdit, QMessageBox, QPushButton

import sys
import tempfile
import os
from typing import Optional

from applugin import screenshot
import apsync as aps

class _PublishDialog(QDialog):
    file_created = Signal(str)

    def __init__(self, file: str, img: QPixmap, stylesheet: Optional[str]=None, parent=None):
        super(_PublishDialog, self).__init__(parent)        

        self.file = file

        if stylesheet:
            self.setStyleSheet(stylesheet)

        filename = os.path.split(self.file)[-1]
        dir = os.path.dirname(__file__)

        self.setWindowTitle("Publish to Anchorpoint - ["+filename+"]")   
        self.setWindowIcon(QIcon(os.path.join(dir, "res", "app_icon.ico")))    
        self.setWindowFlags(Qt.WindowCloseButtonHint)

        self.img = img
        self.imglabel = QLabel()
        self.imglabel.setPixmap(img.scaledToWidth(480))
        self.imglabel.setMaximumSize(480, 480)

        # Retrieve the next path of the next version that will be created once the user clicks "publish"
        self.nextfile = aps.get_next_version_path(self.file)

        self.nextversion = QCheckBox("Create new Version")
        self.nextversion.setChecked(True)
        self.nextversion.setToolTip("Saves the current file under the new name and opens the new file in the application")

        self.comment = QTextEdit()
        self.comment.setPlaceholderText("Enter a comment (optional)")
        self.comment.setMinimumWidth(250)
        self.comment.setMaximumHeight(80)

        self.publish = QPushButton("Publish")

        # Create layout and add widgets
        layout = QGridLayout()
        layout.addWidget(self.imglabel, 1, 0, 1, 2)
        layout.addWidget(self.comment, 2, 0, 1, 2)
        layout.addWidget(self.nextversion, 3, 0)
        layout.addWidget(self.publish, 4, 0, 1, 2)

        layout.setSizeConstraint(QLayout.SetFixedSize)

        # Set dialog layout
        self.setLayout(layout)

        # Add button signal to publish_cb slot
        self.publish.clicked.connect(self.publish_cb)

    def __set_comment(self):
        text = self.comment.toPlainText()
        comment = None if len(text) == 0 else text
        aps.comment_version(self.file, comment)

    def __set_thumbnail(self):
        # First, we save the QPixmap to a temporary directory in high resolution and scaled down for a quick preview
        dir = tempfile.gettempdir()
        detail_thumbnail = os.path.join(dir, "detail.png")
        preview_thumbnail = os.path.join(dir, "preview.png")
        if self.img.save(detail_thumbnail) and self.img.scaledToWidth(256).save(preview_thumbnail):
            # Then, we attach the newly saved images to the file in Anchorpoint. After that, we can cleanup the temporary files
            aps.attach_thumbnails(self.file, preview_thumbnail, detail_thumbnail)
            os.remove(preview_thumbnail)
            os.remove(detail_thumbnail)

    def __create_next_version(self):
        new_file = aps.create_next_version(self.file)
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
        >>> command = publish.PublishCommand(path_to_file)
        >>> command.publish_file()
    '''
    file_created = Signal(str)

    def __init__(self, file, stylesheet:Optional[str]=None):
        '''
        Args:
            file (str): The (absolute) path to the file that should be published
        '''
        super(PublishCommand, self).__init__()
        self.file = file
        self.stylesheet = stylesheet

    def is_versioning_enabled(self):
        '''
        Checks whether or not incremental version control is enabled on the target folder
        
        Returns:
            True when version control is enabled, False otherwise
        '''

        import os
        folder = aps.get_folder(os.path.dirname(self.file))
        if not folder: return False
        return folder.versioning_enabled

    def publish_file(self):
        '''
        Shows a screenshot tool and a Dialog to the user. Publishes the file if the user wants to.
        Informs the user when version control is disabled.
        Emits the file_created Signal when a new version of the file has been created.

        Example:
            >>> command = publish.PublishCommand(path_to_file)
            >>> command.file_created.connect(new_file_created_callback)
            >>> command.publish_file()
        '''

        if self.is_versioning_enabled():
            self.screenshot_dialog = screenshot.ScreenshotDialog()
            self.screenshot_dialog.image_captured.connect(self.__show_publish_dialog)
            self.screenshot_dialog.show()
            return True
        else:
            message = QMessageBox()
            message.setText("To publish a file to Anchorpoint you have to enable version control in the target folder.")
            
            dir = os.path.dirname(__file__)
            filename = os.path.split(self.file)[-1]

            message.setWindowTitle("Publish to Anchorpoint - ["+filename+"]")   
            message.setWindowIcon(QIcon(os.path.join(dir, "res", "app_icon.ico")))   
            if self.stylesheet:
                message.setStyleSheet(self.stylesheet)
            message.exec_()
            return False

    @Slot()
    def __show_publish_dialog(self, img):
        self.publish_dialog = _PublishDialog(self.file, img, self.stylesheet)
        self.publish_dialog.file_created.connect(lambda x: self.file_created.emit(x))
        self.publish_dialog.show()
        pass
    
def file_created_cb(filepath: str):
    print (filepath)

if __name__ == '__main__':
    scene = input("Enter path to scene file:")
    app = core.get_qt_application()
    style = core.load_stylesheet(os.path.dirname(__file__) + "/../../cinema4d/R25/style/stylesheet.qss")
    command = PublishCommand(scene, style)
    command.file_created.connect(file_created_cb)
    if command.publish_file():
        sys.exit(app.exec_())