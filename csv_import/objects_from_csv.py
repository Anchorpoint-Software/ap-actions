"""
CHAT GPT PROMPT (Use it only for guidance. It will not create you a perfect working Action)

Create an action, that imports a CSV file and creates either a task list or a set of folders based on a dedicated column from the CSV file.
It should read all the columns in the CSV, list then out and the user can pick a dedicated Attribute in Anchorpoint, that will display the content of the column.
Include also an Option to either overwrite existing Attributes in Anchorpoint or ignore them.

The info whether to create folders or tasks, will come from the YAML file via the input parameter. You can read this input parameter in python via anchorpoint.get_context().inputs["INPUTNAME_IN_YAML"]
Anchorpoint has the following Attribute types: "Single Choice Tag", "Multiple Choice Tag", "Textfield", "Rating", "Link", "Members", "Date", "Checkbox"

The first thing the action should do, is to create a dialog, named "Task/Folder from CSV". There, add a input field, with a browse button where the user can browse to the csv file on the hard drive.
Remember the latest browse path, so if the user presses the browse button again, the browser dialog starts at the same folder where it was closed before.
After the user has added a csv file, create a new dialog, which will overwrite the first one. This dialog should also store the input settings.
In the new dialog, use the name of the csv file as the dialog name. Check all the columns in the csv, because you will need them for matching the folder/task name and the attributes.
Add a dropdown with a label "Match Names". In the dropdown, list all possible columns from the csv. Take the first one as a default. 
Below that, add an info description named "Which column to display the task/folder name"
Then, add a set of dropdowns with labels, based on the columns in the csv file. Each label should be the exact same name like the column. In the attributes,
list all anchorpoint attributes and add a "No Attribute" entry on top. This should be also the default. 
Below that, add a description named "Pick for which column an Attribute should be created. Leave it to <br><b>No Attribute</b> if you want to skip it.")
Below that, add a checkbox, named "Overwrite existing Attribute Values".
Finally, add a button named "Create Tasks/Folders"

When the user presses the button, start an asynchronous process with a process indicator that creates the tasks/folders with the attributes.
For tasks, put them in a task list. This task list should have the same name as the csv file. If the task lists with this name exists, add all the tasks there, if not create a new one.
Folders and the task list should be created in the folder, where the action is executed. You can access the current folder path via anchorpoint.get_context().path
If the taskname/foldername does not exist, create a new task/folder. If the attributes of that task/folder already exist, check if the checkbox "Overwrite existing Attribute Values" is checked. 
If it's enabled, overwrite the attribute value from the csv, if it's not enabled, skip the attribute.
Only create the attributes, that the user has chosen in the dialog. 
Show a success message when the operation is complete.

"""

from typing import cast
import anchorpoint as ap
import apsync as aps
import csv
import os
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

def get_csv_delimiter(csv_path):
    try:
        with open(csv_path, 'r', encoding='utf-8-sig') as csvfile:
            first_line = csvfile.readline()
            delimiter = ';' if ';' in first_line else ','
        return delimiter
    except UnicodeDecodeError:
        # Try alternative encodings
        try:
            with open(csv_path, 'r', encoding='latin-1') as csvfile:
                first_line = csvfile.readline()
                delimiter = ';' if ';' in first_line else ','
            return delimiter
        except Exception:
            ui.show_error("Encoding Error", "Cannot read the CSV file. Please save it with UTF-8 encoding and try again.")
            return None

def remove_empty_entries(array):
    return [entry for entry in array if entry]

def convert_attribute_value(attribute_type, value):
    if attribute_type == "Date":
        if (not value):
            return ""
        # Parsing the date string to a datetime object
        date_obj = dateutil.parser.parse(value)
        return date_obj
    if attribute_type == "Members":
        user = ""
        if "[" in value and "]" in value:
            user = value.replace("[", "").replace("]", "")
        else:
            user = value

        if (not user):
            return ""

        if "@" not in user:
            project = aps.get_project_by_id(ctx.project_id, ctx.workspace_id)
            users = aps.get_users(ctx.workspace_id, project)
            for u in users:
                if u.name.strip() == user.strip():
                    return u.email
            return ""
        else:
            return user

    return value


def show_dialog():
    last_csv_file = cast(str, settings.get("last_csv_file", ""))
    dialog = ap.Dialog()
    dialog.title = f"{object_type.capitalize()}s from CSV"
    dialog.icon = ctx.icon
    dialog.add_text("CSV File").add_input(browse=ap.BrowseType.File,
                                          browse_path=os.path.dirname(last_csv_file), var="csv_path", callback=on_file_selected, placeholder="todos.csv")
    dialog.show()


def on_file_selected(dialog, value):
    dialog = ap.Dialog()
    dialog.title = os.path.basename(value)
    dialog.icon = ctx.icon
    csv_path = value
    if not csv_path or not os.path.isfile(csv_path) or not csv_path.lower().endswith('.csv'):
        ui.show_error("Not a CSV File", "Please select a valid CSV file.")
        return

    if settings.get("last_csv_file", "") != csv_path:
        settings.clear()
    settings.set("last_csv_file", csv_path)
    settings.store()

    delimiter = get_csv_delimiter(csv_path)
    if delimiter is None:  # Handle encoding error
        return

    try:
        with open(csv_path, newline='', encoding='utf-8-sig') as csvfile:
            reader = csv.reader(csvfile, delimiter=delimiter)
            csv_headers = next(reader)
            csv_headers = remove_empty_entries(csv_headers)
    except UnicodeDecodeError as e:
        ui.show_error("Issue with the CSV file", "This file cannot be opened. Re-export it and open it again.")
        return
    
    dialog.add_text("<b>Match Names</b>")
    dialog.add_dropdown(
        csv_headers[0], csv_headers, var="object_name", width=160).add_text("⮕").add_text(f"{object_type.capitalize()} Name", width=224)
    dialog.add_info(f"Which column should display the {object_type} name")
    dialog.add_text("<b>Match Attributes</b>")

    for header in csv_headers:
        default_value = settings.get(f"{header}_dropdown", "No Attribute")
        dialog.add_text(header, width=160).add_text("⮕").add_dropdown(
            default_value, ATTRIBUTE_TYPES, var=f"{header}_dropdown", width=224)
    dialog.add_info("Pick for which column an Attribute should be created. Leave it to<br><b>No Attribute</b> if you want to skip it.")

    dialog.add_checkbox(
        text="Overwrite existing Attribute Values", var="overwrite")
    dialog.add_info(f"Existing {object_type}s will be merged with new ones. If you override existing <br>Attributes, it will use the Attribute values from the csv file. <a href='https://docs.anchorpoint.app/assets/utilities/import-csv/'>Learn more</a>")

    dialog.add_button(f"Create {object_type.capitalize()}s", callback=lambda dialog: create_objects_async(dialog, csv_path),
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
        block_id = ctx.block_id
        if block_id:
            task_list = api.tasks.get_task_list_by_id(ctx.block_id)
        else:
            task_list = api.tasks.get_task_list(ctx.path, task_list_name)

        if not task_list:
            task_list = api.tasks.create_task_list(
                ctx.path, task_list_name)

    progress = ap.Progress(
        f"Creating {object_type.capitalize()}s", infinite=False)
    progress.set_cancelable(True)
    progress.report_progress(0.0)

    created_object_count = 0
    delimiter = get_csv_delimiter(csv_path)

    with open(csv_path, newline='', encoding='utf-8-sig') as csvfile:
        reader = csv.DictReader(csvfile,delimiter=delimiter)
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
