# This example demonstrates how to create and control a more complex dialog in Anchorpoint

import anchorpoint as ap
import apsync as aps
import os

ctx = ap.get_context()
ui = ap.UI()

current_folder = ctx.path

# Dialog Entry Variables
# Use them to identify a dialog entry
# so that you can read the value of the dialog within a callback
folder_name_var = "name"
folder_count_var = "count"
folder_cap_var = "cap"
button_var = "button"
attr_wip_var = "wip"
attr_link_var = "link"

# Dialog Callbacks
# The changed challback is called whenever the item has changed (e.g. when the user types something in the text input)
# The first paramter is the dialog itself, the second parameter is the changed value
def cb_name_changed(dialog, value):
    # Toggle the enable state on the button when the content of the name input field changes
    enable = len(value) != 0
    dialog.set_enabled(button_var, enable)
    print(f"button enable: {enable}")

# The button pressed callback takes only one parameter: the dialog itself
def button_pressed(dialog):
    # First, retrieve all the input fields from the dialog that we are interested in by using the variables declared above
    folder_name = dialog.get_value(folder_name_var)
    capitalize = dialog.get_value(folder_cap_var)
    set_wip = dialog.get_value(attr_wip_var)
    set_link = dialog.get_value(attr_link_var)

    # The count field is a string, so we have to re-interpret it as a number
    count = int(dialog.get_value(folder_count_var))

    if capitalize:
        # CAPITALIZE IT
        folder_name = folder_name.upper()

    create_folders(current_folder, folder_name, count, set_wip, set_link)

    dialog.close()
    ui.reload()


# This callback is called whenever the dialog is closed
def cb_closed(dialog):
    print("dialog closed")


# Other Functions used to control the behavior of our action
# This functions creates attributes and sets values to the corresponding folder
def set_attributes(folder, set_wip, set_link):
    if set_wip:
        # Adds a new single choice tag attribute called "Status" and assigns a yellow tag called "WIP" to the folder
        aps.set_attribute_tag(folder, "Status", "WIP", tag_color=aps.TagColor.yellow)
    if set_link:
        # Adds a new link attribute called "Link" and assigns the best homepage in the world to it
        aps.set_attribute_link(folder, "Link", "https://www.anchorpoint.app")


# This function does the heavy lifting: It creates the "count" number of folders on the filesystem
def create_folders(folder, folder_name, count, set_wip, set_link):
    # We are interacting with the file system which is a danger zone.
    # Better play safe by using the try-except-else paradigm of python.
    # By that we can capture exceptions and report them to the user.
    try:
        for i in range(count):
            # Create all the fancy folders
            prefix = str((i + 1) * 10)
            current_folder = os.path.join(folder, f"{prefix}_{folder_name}")
            os.mkdir(current_folder)

            # And set the attributes, if asked for
            set_attributes(current_folder, set_wip, set_link)

    except Exception as e:
        # Yikes, something went wrong! Tell the user about it
        ui.show_error("Failed to create folders", description=str(e))
    else:
        ui.show_success("Folders created successfully")


# Defines and shows the complex dialog
def showDialog():
    dialog = ap.Dialog()
    dialog.title = "Create Folders"

    # Set the icon hat is used by our dialog
    if ctx.icon:
        dialog.icon = ctx.icon
    if ctx.icon_color:
        dialog.icon_color = ctx.icon_color

    dialog.callback_closed = cb_closed

    dialog.add_text("Name:\t").add_input(
        placeholder="provide a folder name", var=folder_name_var, callback=cb_name_changed
    )
    dialog.add_text("Count:\t").add_input("2", var=folder_count_var)
    dialog.add_separator()

    dialog.start_section("Advanced", folded=True)
    dialog.add_checkbox(var=folder_cap_var).add_text("Capitalize")
    dialog.add_info("This will <b>capitalize</b> all folders")
    dialog.add_empty()

    dialog.start_section("Attributes", foldable=False)
    dialog.add_checkbox(True, var=attr_wip_var).add_text("Set WIP")
    dialog.add_checkbox(False, var=attr_link_var).add_text("Set Link")
    dialog.add_info("Enable the checkboxes to set attributes on the folders")
    dialog.end_section()

    dialog.end_section()

    dialog.add_button("Create", button_pressed, var=button_var, enabled=False)

    dialog.show()


showDialog()
