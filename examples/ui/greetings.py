# This example demonstrates how to create a simple dialog in Anchorpoint
import anchorpoint as ap

# Anchorpoint UI class allows us to show e.g. Toast messages in Anchorpoint
ui = ap.UI()

name_var = "name"
def button_clicked_cb(dialog):
    name = dialog.get_value(name_var)
    ui.show_info(f"Hello {name}")  

# Create a dialog container
dialog = ap.Dialog()

# Set a nice title
dialog.title = "Greetings Dialog"

# Add an input dialog entry so the user can provide a name. 
# Assign a variable to the input entry so that we can identify it later.
dialog.add_input("John Doe", var = name_var)

# Add a button to show the greetings, register a callback when the button is clicked.
dialog.add_button("Show Greetings", callback = button_clicked_cb)

# Present the dialog to the user
dialog.show()