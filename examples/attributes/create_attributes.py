import anchorpoint as ap
import apsync as aps
import time

ctx = ap.Context.instance()
api = ctx.create_api()
ui = ap.UI()

selected_files = ctx.selected_files
selected_folders = ctx.selected_folders

def create_attribute(object):
    aps.set_cell_text(api, object, "Text", "Hello")
    aps.set_cell_link(api, object, "Link", "https://www.anchorpoint.app")
    aps.set_cell_checked(api, object, "Checkbox", True)
    aps.set_cell_date(api, object, "Date", int(time.time()))
    aps.set_cell_rating(api, object, "Rating", 4)
    aps.set_cell_tag(api, object, "Single Choice Tag", "Python <3", tag_color=aps.TagColor.green)
    aps.set_cell_tag(api, object, "Multiple Choice Tag 1", "Anchorpoint", tag_color=aps.TagColor.blue, type=aps.AttributeType.multiple_choice_tag)
    aps.set_cell_tags(api, object, "Multiple Choice Tag 2", ["JPEG","PNG"])

    print(aps.get_cell_text(api, object, "Text"))
    print(aps.get_cell_tag(api, object, "Single Choice Tag").name)

for f in selected_files:
    create_attribute(f)

for f in selected_folders:
    create_attribute(f)

ui.navigate_to_folder(ctx.path)
ui.show_toast("Attributes created")