# This example demonstrates how to show progress on a dialog in Anchorpoint

import anchorpoint as ap


def add_progress(d):
    progress = d.get_value("progress") + 10
    print(f"Current Progress: {progress}")
    d.set_value("progress", progress)
    d.set_value("progress", f"Showing progress: {progress}%")
    d.set_enabled("-", True)
    if progress == 100:
        d.set_enabled("+", False)


def reduce_progress(d):
    progress = d.get_value("progress") - 10
    print(f"Current Progress: {progress}")
    d.set_value("progress", progress)
    d.set_enabled("+", True)
    if progress == 0:
        d.set_value("progress", "Showing an infinite progress indicator")
        d.set_enabled("-", False)
    else:
        d.set_value("progress", f"Showing progress: {progress}%")


# Defines and shows the pages dialog
def show_dialog():
    dialog = ap.Dialog()
    dialog.title = "Show Progress"

    dialog.add_button(
        "(-) Remove Progress", var="-", callback=reduce_progress, enabled=False
    ).add_button("(+) Add Progress", var="+", callback=add_progress)

    dialog.add_progress(
        "Creating Awesome Experience...",
        "Showing an infinite progress indicator",
        var="progress",
    )

    dialog.show()


show_dialog()
