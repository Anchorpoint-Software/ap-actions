# This example demonstrates how to create and control a more complex dialog in Anchorpoint that creates multiple pages

import anchorpoint as ap
import os

ctx = ap.get_context()
path = ctx.path


def create_file(dialog):
    file_name = dialog.get_value("file_name")
    content = dialog.get_value("content")
    with open(os.path.join(path, file_name), "w") as f:
        f.write(content)

    dialog.close()
    ap.UI().show_success(f"File {file_name} created")


# Defines and shows the pages dialog
def show_dialog():
    dialog = ap.Dialog()
    dialog.title = "Create Example File"

    dialog.add_text("This dialog will create a new file in the current folder.")
    dialog.add_text("Filename: ").add_input(placeholder="File Name", var="file_name")

    dialog.add_button("Next", callback=lambda dialog: dialog.next_page())

    dialog.start_page("content")
    dialog.add_text("Content: ").add_input(placeholder="Content", var="content")

    dialog.add_button(
        "Back", callback=lambda dialog: dialog.prev_page(), primary=False
    ).add_button("Create", callback=create_file)

    dialog.show()


show_dialog()
