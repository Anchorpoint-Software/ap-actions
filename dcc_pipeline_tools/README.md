# Publish from DCCs workflow

This action contains tools and scripts to streamline the workflow for creating and publishing new assets using DCCs like Cinema 4D. It's used for product visualization or asset creation workflows and allows to perform versioning on a shared drive such as a NAS, Dropbox or Google Drive.

## How it works
When enabling the Action in the Action Settings, it will:
- Add a new project type to the list
- Add the DCC integrations, so that users can install the Anchorpoint plugin to their DCC (e.g. Cinema 4D)

When creating a new project, the new project type has to be chosen. It can only be used if files are on a shared drive and is not compatible with Git. The project type, has also an option to use a folder template. The template has to be configured in the Action Settings.

### Templates
Folder structures from Templates can be created when the Anchorpoint project is created. Templates have to be placed on a folder, that is accessible for all team members. The file path to macOS and Windows have to be set in the Action Settings. Furthermore, tokens can be also specified. A token is a placeholder, that can replace a name on a file or folder.

For example, a file that is stored as `[customer]_model_v001.psd` can be automatically renamed to `ACME_model_v001.psd` if a token `customer` has been set in the Action Settings. Then, the user will get an input field where the actual name of the customer has to be entered.

### The publish process
Publishing means to mark a file as "ready" for the next step. In most cases publishes follow a review process by another team member. Publishing can be either done from a context menu entry, that will show a popup where the user can enter a message or via DCC plugins. Currently, publishing allows also to create a "master" file, which is basically a copy of the working file version without the increment appendix (v_001).

You can also trigger a webhook at the end of the publish process to e.g. connect to web based project management applications.


## Adjusting this workflow for your own pipeline
This workflow can be completely customized for your own needs. The recommended way is to copy and paste this code to a new Git repository, that you then import in Anchorpoint in the Action Settings. Before you start, make sure that you understand the [development of Actions](https://docs.anchorpoint.app/docs/actions/create-actions/) in Anchorpoint.

1. Create a new public Git repository on GitHub
2. Copy and paste the content from this folder to your new repository and push it to GitHub
3. In Anchorpoint, go to Workspace Settings / Actions and import your new created repository
4. Disable the default "DCC Pipeline Tools" Action that comes with Anchorpoint
5. Restart Anchorpoint
6. To use the DCC plugin (e.g. Cinema 4D) you have to go to Workspace Settings / Integrations to see where your plugin will be located as it's part of the code that you can modify. It's recommended to point (add a new plugin folder) Cinema 4D or other DCCs to the plugin rather than copying it to your plugins directory. This should be also done by every member in your team. Once you make plugin updates, they are automatically read by the DCC and don't need to be manually copied over again.

Then you can start developing. 

## Action content and structure

Metadata (the version history) is stored using the shared_settings module. The timeline content is stored as a JSON representation. The publish class (publish.py) is adding new entries, while the inc_timeline class is reading and displaying these entries in the Anchorpoint timeline UI.

**publish_from_ui**
Allows to create a timeline entry by opening a dialog in the Anchorpoint context menu. This is a fallback if other DCC files are published than the ones that have plugins.

### inc_project
This folder contains the code to display the new project entry and the timeline entries in that project. The project settings and the timeline entries are only read if the timeline channel (a way to manage project types) is set to `inc-vc-basic`. The project settings entry are also only displayed it the project has that timeline channel, to prevent them displaying on Git projects.

**inc_project**
- Creates a new Anchorpoint project type
- Handles the folder structure from template creation part

**inc_timeline**
Creates timeline entries from the metadata database manages in settings

**project_settings**
Controls whether a master file should be created

### cinema_4d
Includes the display of the Cinema 4D integration in Anchorpoint and the plugin that connects to the Anchorpoint CLI to send commands.

**c4d_to_ap**
Converts the data from the plugin and triggers `publish.py` which creates a new timeline entry. The Cinema 4D plugin triggers the Anchorpoint CLI (ap.exe) with arguments. One of the argument is to pass the `c4d_to_ap.py` script with other arguments. This script can then use the Anchorpoint python modules to e.g. access the Anchorpoint metadata. This would not be possible to write in the Cinema 4D python plugin on it's own.

**cinema_4d_integration**
This covers only the display of the Cinema 4D plugin in the Workspace Settings / Integration section.

**plugin/Anchorpoint**
This folder is the actual Cinema 4D plugin that has to be added to Cinema 4D if you develop your own integration. When you are using the default Action, that comes with Anchorpoint, copy and paste the plugin folder to your Cinema 4D plugin directory. It will then always point to the Anchorpoint installation path, including the default Actions.

