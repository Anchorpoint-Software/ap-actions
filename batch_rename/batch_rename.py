import anchorpoint as ap
import os
import apsync as aps


DIGIT_OPTIONS_MAP = {
    1: ("1 Digit (1, 2, 3)", 1),
    2: ("2 Digits (01, 02, 03)", 2),
    3: ("3 Digits (001, 002, 003)", 3),
    4: ("4 Digits (0001, 0002, 0003)", 4),
    0: ("Variable (no leading zeros)", 0)
}


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


def get_preview_names(base_name, ext, count, digit_count, variable, selected_files):
    preview = []
    for i in range(min(3, count)):
        if variable:
            num = str(i+1)
        else:
            num = str(i+1).zfill(digit_count)
        preview.append(f"{base_name}{num}{ext}")
    return preview


def main():

    ctx = ap.get_context()
    selected_files = ctx.selected_files
    file_count = len(selected_files)
    if file_count == 0:
        ap.show_error("No files selected for renaming.")
        return False

    digit_options = get_digit_options(file_count)
    digit_labels = [opt[0] for opt in digit_options]
    digit_values = [str(opt[1]) for opt in digit_options]

    # Get extension from first file
    first_ext = os.path.splitext(selected_files[0])[1]

    def update_preview(dialog, value):
        base_name = dialog.get_value("base_name_var")
        digits_label = dialog.get_value("digits_var")
        # Map the selected label back to the digit value
        digits = next((opt[1]
                      for opt in digit_options if opt[0] == digits_label), 0)
        variable = digits == 0
        preview = get_preview_names(
            base_name, first_ext, file_count, digits, variable, selected_files)
        preview_text = "\n".join(preview)
        dialog.set_value("preview_var", preview_text)

    dlg = ap.Dialog()
    dlg.title = "Batch Rename Files"
    dlg.add_text("Enter the new base name for the files:")
    dlg.add_input(placeholder="Base name",
                  default="File_", callback=update_preview, var="base_name_var")
    dlg.add_text("Select digit format for numbering:")
    dlg.add_dropdown(digit_labels[0], digit_labels, var="digits_var",
                     callback=update_preview)

    dlg.add_text("Preview:")
    dlg.add_info("", var="preview_var")

    update_preview(dlg, None)

    dlg.show()

    # Example: perform renaming (not implemented here)
    # for idx, file in enumerate(selected_files):
    #     ...


if __name__ == "__main__":
    main()
