# Anchorpoint Actions
Actions allows you to save time and stress by automating your workflow. You don't need to have great software development skills. A basic knowledge of Python and scripting in general is enough to code your own actions from these examples. 

## What can you build with Actions?
Everything where you have to do a lot of manual work (renaming files, copying files, constantly opening the DCC to load files and save them again or bugging your teammates to put data in the right place) you can automate with Actions.

This includes
- Batch conversion to other file formats
- Batch rename
- Create thumbnails to find your projects faster
- Build custom UIs
- Build integrations to your DCCs
- Connect to render farms and cloud providers
- Reroute drives

Basically anything that will save a tremendous amount of time and hassle in your day to day life.

## Documentation
- [Actions Overview](https://docs.anchorpoint.app/Actions/Intro)
- [YAML Reference](https://docs.anchorpoint.app/API-Reference/YAML)
- [Quick Tutorial](https://docs.anchorpoint.app/Actions/Tutorials/Image-Conversion)


## Getting Started
Download this repository and navigate to the global action directory. 

![Action GIF](https://raw.githubusercontent.com/Anchorpoint-Software/ap-actions-data/main/gif/installActions.gif)

1. in Anchorpoint, click on the three dots in the upper right corner and select Preferences.
2. go to Actions and click on Actions Folder
3. you are now in the folder where scripts can be placed. Put the files you unzipped in there.
4. open the Context menu and there you should see a list of actions. 

If you don't want to show all actions there you can disable actions in the respective YAML file. 
Go to the point "register" and set the option "enabled" to "false".

```yaml
#Where should the action be shown
register:
    #Action will be shown in the folder context menu
    folder:
      #Action is enabled
      enable: true
```

## Table of contents
- [High resolution thumbnails for Blender files](/tree/main/blender)
- [Export FBX from Cinema 4D files](/tree/main/cinema4d)
- [Render playblast from Cinema 4D files](/tree/main/cinema4d)
- [Turn any folder to a drive to solve the issue with absolute file paths](/tree/main/drives)
- [Turn image sequences to a video](/tree/main/ffmpeg)
- [Turn a video to a GIF](/tree/main/ffmpeg)
- [Use .gitignore templates for Unity, Unreal or Godot](/tree/main/git/ignore%20files)
- [Create a folder template with options from a UI](/tree/main/template)
- [Understand how to build a custom UI and set Attributes](/tree/main/tutorials)
- [A template for quickly building new Actions](/tree/main/utility)


## Want to contribute
Do you have scripts that you use in your workflow and think that they could be valuable for other users? Share them via a pull request. If you need any help feel free to contact us directly.
You can talk to us on our [Discord](https://discord.com/invite/ZPyPzvx) server or via [Email](mailto:support@anchorpoint.app).


