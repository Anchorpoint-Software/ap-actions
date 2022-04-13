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
- [Actions Overview](https://docs.anchorpoint.app/docs/5-Actions/1-Intro)
- [YAML Reference](https://docs.anchorpoint.app/docs/5-Actions/4-YAML)
- [Python Reference](https://docs.anchorpoint.app/docs/5-Actions/5-Python)
- [Quick Tutorial](https://docs.anchorpoint.app/docs/5-Actions/Tutorials/1-Image-Conversion)


## Getting Started
Download this repository and navigate to the global action directory. 

![Action GIF](https://raw.githubusercontent.com/Anchorpoint-Software/ap-actions-data/main/gif/installActions.gif)

1. in Anchorpoint, click on the three dots in the upper right corner and select Preferences.
2. go to Actions and click on Actions Folder
3. you are now in the folder where scripts can be placed. Put the files you unzipped in there.
4. open the Context menu, you should see a list of actions. 

If you don't want all actions to show up in the context menu, disable an action in the respective YAML file. 

```yaml
category: examples/input
type: python
enable: false # Don't show this action at all
```

## Table of contents
- [High resolution thumbnails for Blender files](blender)
- [Turn any folder to a drive to solve the issue with absolute file paths](drives)
- [Use .gitignore templates for Unity, Unreal or Godot](git/ignore%20files)
- [Create a folder template with options from a UI](template)
- [Understand how to build a custom UI and set Attributes](examples)
- [Coding utilities that are helpful when creating your own actions for Anchorpoint](coding)


## Want to contribute?
Do you have scripts that you use in your workflow and think that they could be valuable for other users? Share them via a pull request. If you need any help feel free to contact us directly.
You can talk to us on our [Discord](https://discord.com/invite/ZPyPzvx) server or via [Email](mailto:support@anchorpoint.app). You can also create an issue on [GitHub](https://github.com/Anchorpoint-Software/ap-actions/issues).


