# Publish workflows

This repository contains tools and scripts to streamline the workflow for creating and publishing new assets using Cinema 4D and Anchorpoint.

## Contents

- **cinema_4d_plugin/Anchorpoint/**
  - Contains the Cinema 4D plugin and the publish script (`plugin.pyp`).
  - The plugin adds a menu entry "Anchorpoint/ Publish" in Cinema 4D.
  - When selected, it opens a dialog for the user to enter a comment and then publishes the current Cinema 4D file to Anchorpoint, adding relevant attributes and tasks.
  - `anchorpoint_connector.py`converts the data from the plugin and triggers `inc_publish.py` which creates a new timeline entry and a master file with attributes

- **inc_project**
  - Creates a new Anchorpoint project type
  - Handles the folder structure from template creation part

- **inc_timeline**
   Creates timeline entries from the metadata database manages in settings

- **project_settings**
   Controls whether a master file should be created

- **publish_from_ui**
   Allows to create a timeline entry by opening a dialog in the Anchorpoint context menu. This is a fallback if other DCC files are published than the ones that have plugins.

## Installation for the user

1. **Enable the action in the workspace settings**

2. **Install the Cinema 4D Plugin**
   - Set the path to the `cinema_4d_plugin` folder in your Cinema 4D plugin settings.

3. **Set the Template Location**
   - Configure the template location for both Windows and Mac in the action settings.