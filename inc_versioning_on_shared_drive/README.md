# Product Viz case

This repository contains tools and scripts to streamline the workflow for creating and publishing new SKUs (product numbers) using Cinema 4D and Anchorpoint.

## Contents

- **cinema_4d_plugin/Anchorpoint/**
  - Contains the Cinema 4D plugin and the publish script (`sn_plugin.pyp`).
  - The plugin adds a menu entry "Anchorpoint/ Publish" abd "Anchorpoint/ Save as Splinter" in Cinema 4D.
  - When selected, it opens a dialog for the user to enter a comment and then publishes the current Cinema 4D file to Anchorpoint, adding relevant attributes and tasks.
  - The actual publishing logic is handled by `sn_create_object.py` in the same folder.

- **sn_project**
  - Creates a new Anchorpoint project type
  - Handles the folder structure from template creation part

- **sn_timeline**
   - Creates timeline entries from the metadata database manages in settings

- **launch_c4d/**
  - Opens Cinema 4D with the latest file version

## Workflow Overview

1. **Open Cinema 4D**
   - Launches Cinema 4D with the latest file version

2. **Publish the Work**
   - After finishing the work in Cinema 4D, use the menu entry "Anchorpoint/ Publish".
   - This triggers the plugin, which opens a dialog for a comment and then runs the publish script.
   - The script adds the necessary attributes and tasks in Anchorpoint for the published file.

3. **Save as Splinter**
   - Creates a new Cinema 4D document for experimental purposes
   - Logs this entry in the timeline

## Installation for the user

1. **Import the Action in the Anchorpoint workspace settings**

2. **Install the Cinema 4D Plugin**
   - Set the path to the `cinema_4d_plugin` folder in your Cinema 4D plugin settings.

3. **Set the Template Location**
   - Configure the template location for both Windows and Mac in the action settings.
   - Make sure that the template has a proper starter file and master file with the correct naming, including initials in the starter file and a "_master" appendix in the master file


## Development tips

Create a main project folder, that will contain the template, the code repository and a test project. Create a testproject in Anchorpoint. For templates, take a look at the template_example.zip

---

For more details, refer to the scripts and comments in each folder.
