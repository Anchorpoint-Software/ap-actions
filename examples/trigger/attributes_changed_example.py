import anchorpoint as ap

def on_attributes_changed(parent_path: str, attributes: list[ap.AttributeChange], ctx: ap.Context):
    ap.UI().show_console()
    print(f"{len(attributes)} Attribute(s) Changed in: {[parent_path]}")
    for change in attributes:
        print(f"Attribute Changed Python Trigger:  {change.path} {change.name}: {change.old_value} -> {change.value}")