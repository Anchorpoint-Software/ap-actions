import anchorpoint as ap
import apsync as aps
import os

ctx = ap.get_context()
ui = ap.UI()

project_folder = os.path.join(ctx.path, "python_example_project")

# First, we check if the folder already exists
if os.path.exists(project_folder):
    # Too bad, tell the user about the already existing folder
    ui.show_error("Project Example Error", "The directory already exists.")
else:
    # OK, let's create a new project at the current location. This will create a new folder and will convert it to an Anchorpoint project called "Python Example"
    project = ctx.create_project(os.path.join(ctx.path, "python_example_project"), "Python Example", ctx.workspace_id)

    # Let's print the name of the project
    print("The project name is: " + project.name)

    # A project can store additional metadata that is not shown as attributes. 
    # This is useful for setting up technical information about a project such as a client name or the general aspect ratio
    metadata = project.get_metadata()

    # Metadata of a project is just a python dict[str,str]
    metadata["Project_Name"] = "Anchorpoint"
    metadata["Aspect_Ratio"] = "16:9"

    # Update the projects metadata so that all actions can use them
    # Note that only the creator of a project can update the metadata. Reading metadata is generally possible.
    project.update_metadata(metadata)

    # When working with an existing project, you can always look up the active project for any given path (file or folder)
    other_project = aps.get_project(project_folder)

    # Let's print the project metadata
    print("The project metadata is: " + str(other_project.get_metadata()))

    ui.show_success("Project Created")
