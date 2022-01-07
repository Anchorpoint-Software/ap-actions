from .ui import get_qt_application, get_style

from PySide2.QtWidgets import QDialog, QLineEdit, QPushButton, QVBoxLayout
import sys

class PublishDialog(QDialog):
    def __init__(self, parent=None):
        super(PublishDialog, self).__init__(parent)
        self.setWindowTitle("Publish File")

        self.edit = QLineEdit("Enter a comment")
        self.button = QPushButton("Publish")

        # Create layout and add widgets
        layout = QVBoxLayout()
        layout.addWidget(self.edit)
        layout.addWidget(self.button)
        # Set dialog layout
        self.setLayout(layout)

        # Add button signal to greetings slot
        self.button.clicked.connect(self.greetings)

    def greetings(self):
        print ("Hello %s" % self.edit.text())

def publish_file(app):
    form = PublishDialog()
    form.show()

    # Run the main Qt loop
    return app.exec_()

if __name__ == '__main__':
    app = get_qt_application(get_style())
    sys.exit(publish_file(app))