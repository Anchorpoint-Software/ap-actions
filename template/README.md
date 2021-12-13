# Template Actions

A collection of useful actions that create folder structures and instantiates files from given templates.

## New Shot / New Folder

This action creates a new folder (e.g. a new shot) based on a template. It also increments the shot number automatically by replacing each variable \$ within the folder (including files).

### Add Template Files
If you want to add a template file, just go ahead and create it within the template folder like so, for example:

**/templates/shot_$/02_assets/main_shot_$.c4d**

so that when firing up the action, the file will be created as:

**shot_50/02_assets/main_shot_50.c4d**

### Add Other Folder Templates

The action uses the *new_folder_incremental.py* script. 
The *new_shot.yaml* points to the **templates/shot_$** folder that is located in this directory. So you can simply add new folder templates by creating actions based on the *new_shot.yaml*

![Action GIF](https://raw.githubusercontent.com/Anchorpoint-Software/ap-actions-data/main/gif/new_shot.gif)


## New folder from Template

This action shows a more advanced case of template folders. It opens up a dialog that lets you configure a template folder based on a variable set of variables.
Each \$ within the folder name is a variable that resolves to the current date or to the current user initials, for example.

![Action GIF](https://raw.githubusercontent.com/Anchorpoint-Software/ap-actions-data/main/gif/new_folder_from_template.gif)

