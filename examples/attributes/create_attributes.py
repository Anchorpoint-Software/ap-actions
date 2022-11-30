import anchorpoint as ap
import apsync as aps
import time

ctx = ap.Context.instance()
ui = ap.UI()

selected_files = ctx.selected_files
selected_folders = ctx.selected_folders

def create_attribute(object):
    aps.set_attribute_text(object, "Text", "Hello", workspace_id = ctx.workspace_id)
    aps.set_attribute_link(object, "Link", "https://www.anchorpoint.app", workspace_id = ctx.workspace_id)
    aps.set_attribute_checked(object, "Checkbox", True, workspace_id = ctx.workspace_id)
    aps.set_attribute_date(object, "Date", int(time.time()), workspace_id = ctx.workspace_id)
    aps.set_attribute_rating(object, "Rating", 4, workspace_id = ctx.workspace_id)
    aps.set_attribute_tag(object, "Single Choice Tag", "Python <3", tag_color=aps.TagColor.green, workspace_id = ctx.workspace_id)
    aps.set_attribute_tag(object, "Multiple Choice Tag 1", "Anchorpoint", tag_color=aps.TagColor.blue, type=aps.AttributeType.multiple_choice_tag, workspace_id = ctx.workspace_id)
    aps.set_attribute_tags(object, "Multiple Choice Tag 2", ["JPEG","PNG"], workspace_id = ctx.workspace_id)

    print(aps.get_attribute_text(object, "Text"))
    print(aps.get_attribute_tag(object, "Single Choice Tag").name)


for f in selected_files:
    create_attribute(f)

for f in selected_folders:
    create_attribute(f)

ui.reload()
ui.show_success("Attributes created")