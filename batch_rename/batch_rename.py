import anchorpoint as ap
import os
import apsync as aps

# Set the option that will be shown in the dropdown and map it to the number of digits
# 0 means variable, so no leading zeros
DIGIT_OPTIONS_MAP = {
    1: ("1 Digit (1, 2, 3)", 1),
    2: ("2 Digits (01, 02, 03)", 2),
    3: ("3 Digits (001, 002, 003)", 3),
    4: ("4 Digits (0001, 0002, 0003)", 4),
    0: ("Variable (no leading zeros)", 0)
}
# The default base name that will be shown in the input field
DEFAULT_BASENAME = "File_"


# Limit the options that can be chosen based on the number of selected files. E.g. if you have 15 files selected, you cannot pick 1 digit
def get_digit_options(file_count):
    options = []
    if file_count <= 9:
        options.append(DIGIT_OPTIONS_MAP[1])
    if file_count <= 99:
        options.append(DIGIT_OPTIONS_MAP[2])
    if file_count <= 999:
        options.append(DIGIT_OPTIONS_MAP[3])
    if file_count <= 9999:
        options.append(DIGIT_OPTIONS_MAP[4])
    options.append(DIGIT_OPTIONS_MAP[0])
    return options

# Generate a preview string based on the current settings


def get_preview_names(base_name, ext, count, digit_count, variable, selected_files):
    preview = ""
    for i in range(min(3, count)):
        if variable:
            num = str(i+1)
        else:
            num = str(i+1).zfill(digit_count)
        preview += (f"{base_name}{num}{ext},")
    return preview+"..."

# Update the preview text in the dialog when user changes input


def update_preview(dialog, value):
    ctx = ap.get_context()
    selected_files = ctx.selected_files
    file_count = len(selected_files)
    # Get extension from first file
    first_ext = os.path.splitext(selected_files[0])[1]
    base_name = dialog.get_value("base_name_var")
    digits_label = dialog.get_value("digits_var")
    # Map the selected label back to the digit value
    digits = get_digits(digits_label)
    variable = digits == 0

    preview = get_preview_names(
        base_name, first_ext, file_count, digits, variable, selected_files)

    dialog.set_value("preview_var", preview)

# get the number of digits (int) based on that the user chose in the dropdown


def get_digits(digits_label):
    for label, value in DIGIT_OPTIONS_MAP.values():
        if label == digits_label:
            return value
    return 0

# prepare the rename options and start the async process


def init_rename(dialog):
    ctx = ap.get_context()
    selected_files = ctx.selected_files
    base_name = dialog.get_value("base_name_var")
    digits_label = dialog.get_value("digits_var")
    digits = get_digits(digits_label)
    variable = digits == 0

    # Start the async rename process to not block the UI
    ctx.run_async(rename, selected_files, variable, digits, base_name)

    dialog.close()


def rename(files, variable, digits, base_name):
    # Set the progress that will be displayed in the top right corner of the desktop application
    progress = ap.Progress("Renaming Files", infinite=False)
    progress.set_cancelable(True)  # allow the user to cancel the progress
    for file in files:
        if progress.canceled:  # Check if the user canceled the operation
            break
        idx = files.index(file)
        # Report progress to the desktop application
        progress.report_progress(idx / len(files))
        ext = os.path.splitext(file)[1]
        if variable:  # no leading zeros because no digits have been picked in the dropdown
            num = str(idx + 1)
        else:
            num = str(idx + 1).zfill(digits)
        new_name = f"{base_name}{num}{ext}"

        dir_path = os.path.dirname(file)
        new_path = os.path.join(dir_path, new_name)
        if file != new_path:
            os.rename(file, new_path)
        pass

    progress.finish()
    ap.UI().show_success("Batch Rename", "Files have been renamed.")


def main():

    # Get the current context from the desktop application
    ctx = ap.get_context()
    selected_files = ctx.selected_files
    file_count = len(selected_files)
    # Calculate the available digit options, that will be options ins the dropdown based on the number of selected files
    digit_options = get_digit_options(file_count)
    digit_labels = [opt[0] for opt in digit_options]

    # Build the dialog with all it's interface building blocks
    dlg = ap.Dialog()
    dlg.title = "Batch Rename Files"
    if ctx.icon:
        dlg.icon = ctx.icon  # take the icon from the YAML file
    dlg.add_input(placeholder="Base name",
                  default=DEFAULT_BASENAME, callback=update_preview, var="base_name_var").add_dropdown(digit_labels[0], digit_labels, var="digits_var",
                                                                                                       callback=update_preview)

    dlg.add_text("<b>Preview</b>")
    dlg.add_info("", var="preview_var")
    dlg.add_button("Rename", callback=init_rename)

    # set the preview based on the default values
    update_preview(dlg, None)

    dlg.show()


if __name__ == "__main__":
    main()
