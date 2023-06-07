# This example demonstrates how to show a system notification from Anchorpoint
import anchorpoint as ap

# Anchorpoint UI class allows us to show e.g. system notification from Anchorpoint
ui = ap.UI()

title_var = "title"
message_var = "message"

def notification_clicked_cb():
    ui.show_info(f"Hello from Notification click") 

def button_clicked_cb(dialog):
    title = dialog.get_value(title_var)
    message = dialog.get_value(message_var)

    # Show a system notification with title, message and register a callback when the notification is clicked.
    ui.show_system_notification(title, message, callback = notification_clicked_cb)
    dialog.close()

# Create a dialog container
dialog = ap.Dialog()

# Set a nice title
dialog.title = "Notification Dialog"

# Add an input dialog entry so the user can provide a title for the notification. 
# Assign a variable to the input entry so that we can identify it later.
dialog.add_text("Notification Title")
dialog.add_input("From Anchorpoint", var = title_var)

# Add an input dialog entry so the user can provide a message for the notification. 
# Assign a variable to the input entry so that we can identify it later.
dialog.add_text("Notification Message")
dialog.add_input("Click me to open Anchorpoint", var = message_var)

# Add a button to show the greetings, register a callback when the button is clicked.
dialog.add_button("Show Notification", callback = button_clicked_cb)

# Present the dialog to the user
dialog.show()