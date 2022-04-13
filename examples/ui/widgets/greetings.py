# This example works with the Anchorpoint provided anchorpoint and PySide2 module.
# We use QWidgets from PySide2 to display a greetings Dialog to the user.
# Note that Anchorpoint internally uses QML for a nice UX experience. 
# If you want to create a more native looking plugin checkout the QML examples.
import anchorpoint as ap
from PySide2.QtWidgets import QApplication, QDialog, QLineEdit, QPushButton, QVBoxLayout

# Anchorpoint UI class allows us to show e.g. Toast messages in Anchorpoint
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
        # Shows a 'success' toast in anchorpoint. 
        ui.show_info(f"Hello {self.edit.text()}")

        # Close the Dialog
        self.close()

# First, we check if we can access the Anchorpoint provided QApplication instance 
app = QApplication.instance()
if app is None:
    # Ouch, no Anchorpoint QApplication instance, this is not good. 
    # We show a toast in Anchorpoint and create our own QApplication.
    import sys
    ui.show_error("PySide2 hiccup", \
        description="QApplication could not be accessed, please report a bug.")
    app = QApplication(sys.argv)
    dialog = Greetings()
    dialog.show()
    sys.exit(app.exec_())
else:
    # Everything OK, we can just instantiate our shiny QDialog
    dialog = Greetings()

    # And display it to the user
    dialog.show()

