import anchorpoint as ap
import apsync as aps

ctx = ap.get_context()
api = ap.get_api()
ui = ap.UI()

selected_files = ctx.selected_files
selected_folders = ctx.selected_folders

def create_attribute_example():
    # This example shows how to access attributes and update the set of tags
    attribute = api.attributes.get_attribute("Python Example")
    if not attribute:
        attribute = api.attributes.create_attribute("Python Example", aps.AttributeType.single_choice_tag)

    new_tag_name = f"Example Tag {len(attribute.tags) + 1}"
    tags = attribute.tags
    tags.append(aps.AttributeTag(new_tag_name, "blue"))
    api.attributes.set_attribute_tags(attribute, tags)

    return attribute

def create_attribute(object, example_attribute):
    # We can either use the attribute that we have created before ...
    latest_tag = example_attribute.tags[-1]
    api.attributes.set_attribute_value(object, example_attribute, latest_tag)
    print(api.attributes.get_attribute_value(object, example_attribute))

    # ... or create / use attributes described by their title
    api.attributes.set_attribute_value(object, "Message", "Hello from Python")
    print(api.attributes.get_attribute_value(object, "Message"))

    # To set a date, use datetime.dateime or a unix timestamp
    from datetime import datetime
    api.attributes.set_attribute_value(object, "Created At", datetime.now())
    print(api.attributes.get_attribute_value(object, "Created At"))

attribute = create_attribute_example()

for f in selected_files:
    create_attribute(f, attribute)

for f in selected_folders:
    create_attribute(f, attribute)
    aps.set_folder_icon(aps.Icon("qrc:/icons/multimedia/microphone (3).svg", "green"))

ui.show_success("Attributes created")