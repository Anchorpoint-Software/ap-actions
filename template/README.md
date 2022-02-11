# Template Actions

For a visual quickstart [check out this video how to use the template actions!](https://www.loom.com/share/87c1c0909f444af69833bec8ce621635)

Template actions allow you to create folder structures, projects, and files with the click of a button.

To create your own custom templates, just add a new folder to the provided template folders:

* __File Templates__: add a new entry in [file_templates](file_templates)
* __Folder Templates__: add a new entry in [folder_templates](folder_templates)
* __Project Templates__: add a new entry in [project_templates](project_templates)

## Tokens

Use tokens, such as __[Client_Name]__, within your files and folders. Based on user input, the tokens will be replaced when instantiating the template.
When using tokens on a project template, the tokens will be stored on the project so that when using file and folder templates, the tokens will be reused. 

## Custom Actions

Adding a custom action is super simple.
To add a new action "Create new Briefing", copy & paste the [folder.yaml](folder.yaml) and name it __briefing.yaml__. You can adjust the action name and description - but most importantly, change the id and the template_dir so that your new action knows where to find the templates.
