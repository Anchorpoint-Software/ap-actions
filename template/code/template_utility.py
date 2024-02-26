import os


def get_template_dir(project_path: str):
    hidden_template_location = os.path.join(project_path, ".ap/templates")
    if os.path.exists(hidden_template_location):
        return hidden_template_location
    else:
        return os.path.join(project_path, "anchorpoint/templates")


def get_template_callbacks(template_dir: str):
    return os.path.join(template_dir, "template_action_events.py")
