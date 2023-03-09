import anchorpoint as ap
import apsync as aps

ctx = ap.get_context()
ui = ap.UI()

def set_settings(settings, setting_name, increment):
    # Get a setting with a default value. Each Setting is identified by a name, here "my setting".
    # The default parameter is optional. If a setting cannot be found and no default is provided, None is returned.
    value = settings.get(setting_name, default = 0)
    
    # Do some changes
    value = value + increment

    # Update the settings object
    settings.set(setting_name, value)

    # You can remove a single setting with
    # settings.remove(setting_name)

    # You can also remove all settings with
    # settings.clear()

    # Finally, store the settings on disk
    settings.store()

    # Print the setting to the console
    print(f"Setting \"{setting_name}\" has new value: {value}")
    

def action_settings():
    # Create a Settings object for this python script
    settings = aps.Settings(__file__)
    set_settings(settings, "my action setting", 1)
    
def user_settings():
    # Create a Settings object for the current user
    settings = aps.Settings()
    set_settings(settings, "my user setting", 2)

def named_settings():
    # Create a Settings object with a name
    settings = aps.Settings("my named settings")
    set_settings(settings, "my named setting", 3)

def workspace_settings():
    # Get the current project
    project = aps.get_project(ctx.path)
    if not project:
        print("Skipped workspace settings example: No active Project")
        return 

    # Create a Settings object and identify it with the current active workspace
    settings = aps.Settings(identifier = project.workspace_id)
    set_settings(settings, "my workspace setting", 4)


def project_settings():
    # Get the current project
    project = aps.get_project(ctx.path)
    if not project:
        print("Skipped project settings example: No active Project")
        return 

    # Create a Settings object and identify it with the current active workspace
    settings = aps.Settings(identifier = project.id)
    set_settings(settings, "my project setting", 5)


# Note: All settings demonstrated here are stored locally per user account. 
# They are not shared through the cloud with your teammates
# When signing out from your account, another user will not overwrite your settings.

# Demonstrates how to store settings for this specific action script so that the settings are unique for *this* action
action_settings()

# Demonstrates how to store settings for the current user
user_settings()

# Demonstrates how to store settings with a name so that they can be written and read from any action
named_settings()

# Demonstrates how to store settings so that they are shared for all actions within a workspace (current user only)
workspace_settings()

# Demonstrates how to store settings so that they are shared for all actions within a project (current user only)
project_settings()

# Displays the action console in Anchorpoint
ui.show_console()