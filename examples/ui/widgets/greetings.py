import anchorpoint as ap
from PySide2.QtWidgets import QApplication, QDialog, QLineEdit, QPushButton, QVBoxLayout

ui = ap.UI()

class Greetings(QDialog):

    def __init__(self, parent=None):
        super(Greetings, self).__init__(parent)

        # Create widgets
        self.edit = QLineEdit("John Doe")
        self.button = QPushButton("Show Greetings")
        # Create layout and add widgets
        layout = QVBoxLayout()
        layout.addWidget(self.edit)
        layout.addWidget(self.button)
        # Set dialog layout
        self.setLayout(layout)
        # Add button signal to greetings slot
        self.button.clicked.connect(self.greetings)
    
    def greetings(self):
        ui.showToast("Hello {}".format(self.edit.text()))
        self.close()

app = QApplication.instance()
if app is None:
    import sys
    ui.showToast("PySide2 hiccup", \
        ap.UI.ToastType.Info, \
        description="QApplication could not be accessed, please report a bug.")
    app = QApplication(sys.argv)
    dialog = Greetings()
    dialog.show()
    sys.exit(app.exec_())
else:
    dialog = Greetings()
    dialog.show()

