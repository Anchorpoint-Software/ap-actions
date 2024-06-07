import anchorpoint as ap
import apsync as aps
import csv
import os
from datetime import datetime
import dateutil.parser

ctx = ap.get_context()
ui = ap.UI()
settings = aps.Settings()
api = ap.get_api()
csv_headers = []
object_type = ctx.inputs["type"]

# Define attribute types with beautified labels
ATTRIBUTE_TYPES = ["No Attribute", "Single Choice Tag", "Multiple Choice Tag",
                   "Textfield", "Rating", "Link", "Members", "Date", "Checkbox"]


def create_attribute(attribute_type, name):
    attribute = api.attributes.get_attribute(name)
    if attribute:
        return attribute
    if attribute_type == "Single Choice Tag":
        attribute = api.attributes.create_attribute(
            name, aps.AttributeType.single_choice_tag)
    if attribute_type == "Multiple Choice Tag":
        attribute = api.attributes.create_attribute(
            name, aps.AttributeType.multiple_choice_tag)
    if attribute_type == "Textfield":
        attribute = api.attributes.create_attribute(
            name, aps.AttributeType.text)
    if attribute_type == "Rating":
        attribute = api.attributes.create_attribute(
            name, aps.AttributeType.rating)
    if attribute_type == "Link":
        attribute = api.attributes.create_attribute(
            name, aps.AttributeType.hyperlink)
    if attribute_type == "Members":
        attribute = api.attributes.create_attribute(
            name, aps.AttributeType.user)
    if attribute_type == "Date":
        attribute = api.attributes.create_attribute(
            name, aps.AttributeType.date)
    if attribute_type == "Checkbox":
        attribute = api.attributes.create_attribute(
            name, aps.AttributeType.checkbox)
    return attribute


def convert_attribute_value(attribute_type, value):
    if attribute_type == "Date":
        if (not value):
            return ""
        # Parsing the date string to a datetime object
        date_obj = dateutil.parser.parse(value)
        return date_obj

    return value


def show_dialog():
    last_folder = settings.get("last_csv_folder", "")
    dialog = ap.Dialog()
    dialog.title = f"{object_type.capitalize()}s from CSV"
    dialog.add_text("CSV File Path:").add_input(browse=ap.BrowseType.File,
                                                browse_path=last_folder, var="csv_path", callback=on_file_selected, placeholder="todos.csv")
    dialog.show()


def on_file_selected(dialog, value):
    dialog = ap.Dialog()
    dialog.title = os.path.basename(value)
    csv_path = value
    if not csv_path or not os.path.isfile(csv_path):
        ap.UI().show_error("Invalid File", "Please select a valid CSV file.")
        return

    settings.set("last_csv_folder", os.path.dirname(csv_path))
    settings.store()

    with open(csv_path, newline='', encoding='utf-8-sig') as csvfile:
        reader = csv.reader(csvfile)
        csv_headers = next(reader)

    dialog.add_text("Match Names ").add_dropdown(
        csv_headers[0], csv_headers, var="object_name")
    dialog.add_info(f"Which column to display the {object_type} name")
    dialog.add_text("<b>Match Attributes</b>")
    dialog.add_info(
        "Pick for which column an Attribute should be created. Leave it to <br><b>No Attribute</b> if you want to skip it.")

    for header in csv_headers:
        default_value = settings.get(f"{header}_dropdown", "No Attribute")
        dialog.add_text(header).add_dropdown(
            default_value, ATTRIBUTE_TYPES, var=f"{header}_dropdown")

    dialog.add_checkbox(
        text="Overwrite existing Attribute Values", var="overwrite")
    dialog.add_button("Create Tasks", callback=lambda dialog: create_objects_async(dialog, csv_path),
                      var="create_objects_btn", enabled=True)
    dialog.show(settings)


def create_objects_async(dialog, csv_path):

    dialog.close()
    ctx.run_async(create_objects, dialog, csv_path)


def create_objects(dialog, csv_path):
    name_column = dialog.get_value("object_name")

    if not csv_path or not os.path.isfile(csv_path):
        ui.show_error("Invalid File", "Please select a valid CSV file.")
        return

    if not name_column:
        ui.show_error("No Task Name", "Please select a task name column.")
        return

    if (object_type == "task"):
        task_list_name = os.path.basename(csv_path)

        task_list = api.tasks.get_task_list(ctx.path, task_list_name)

        if not task_list:
            task_list = api.tasks.create_task_list(
                ctx.path, task_list_name)

    progress = ap.Progress(
        f"Creating {object_type.capitalize()}s", infinite=False)
    progress.set_cancelable(True)
    progress.report_progress(0.0)

    created_object_count = 0

    with open(csv_path, newline='', encoding='utf-8-sig') as csvfile:
        reader = csv.DictReader(csvfile)
        rows = list(reader)
        total_rows = len(rows)
        for index, row in enumerate(rows):
            if progress.canceled:
                break

            object_name = row[name_column]

            if (object_type == "task"):
                object_item = api.tasks.get_task(task_list, object_name)
                if not object_item:
                    object_item = api.tasks.create_task(task_list, object_name)

            if (object_type == "folder"):
                object_item = os.path.join(ctx.path, str(object_name))
                if not os.path.exists(object_item):
                    os.makedirs(object_item)

            created_object_count += 1

            for header in row.keys():
                attribute_type = dialog.get_value(f"{header}_dropdown")
                if attribute_type != "No Attribute":
                    if (row[header]):
                        attribute = api.attributes.get_attribute_value(
                            object_item, header)
                        if not attribute or dialog.get_value("overwrite"):
                            api.attributes.set_attribute_value(object_item, create_attribute(
                                attribute_type, header), convert_attribute_value(attribute_type, row[header]))

            progress.report_progress((index + 1) / total_rows)

    progress.finish()
    ui.show_success(f"{object_type}s created",
                    f"{created_object_count} {object_type}s created using column '{name_column}'.")


def main():
    show_dialog()


if __name__ == "__main__":
    main()
