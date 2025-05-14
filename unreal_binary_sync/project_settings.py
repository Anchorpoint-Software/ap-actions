import anchorpoint as ap
import apsync as aps
import os

class UnrealProjectSettings(ap.AnchorpointSettings):
    def __init__(self, ctx: ap.Context):
        super().__init__()

        if ctx.project_id is None or ctx.project_id == "":
            raise Exception(
                "Unreal Binary settings can only be used in the context of a project"
            )

        no_project_label = "No Project"

        # Check if it's an Unreal project based on located .uproject files
        uproject_files = self.find_uproject_files(ctx.project_path)
        uproject_display_names = [os.path.splitext(os.path.basename(uproject_file))[0] for uproject_file in uproject_files]
        uproject_display_names.append(no_project_label)

        self.ctx = ctx        
        project_path = ctx.project_path
        project_id = ctx.project_id
        workspace_id = ctx.workspace_id
        access_level = aps.get_workspace_access(workspace_id)

        # Get local and shared settings
        local_settings = aps.Settings()
        binary_source = local_settings.get(project_path+"_binary_source", "")
        sync_dependencies = local_settings.get(project_path+"_sync_dependencies", False)
        launch_project_display_name = local_settings.get(project_path+"_launch_project_display_name", no_project_label) 
        dry_run = local_settings.get(project_path+"_dry_run", False)
        
        shared_settings = aps.SharedSettings(project_id,workspace_id,"unreal")
        tag_pattern = shared_settings.get("_tag_pattern", "")

        self.dialog = ap.Dialog()

        # Display local settings for all users
        self.dialog.add_text("<b>Local Settings</b>")

        self.dialog.add_text("ZIP Location",width = 100).add_input(
            placeholder="Select folder containing binaries...",
            browse=ap.BrowseType.Folder,
            var="binary_source",
            default=binary_source,
            width = 246,
            callback = self.store_local_settings
        )
        self.dialog.add_info("The folder containing all the ZIP files named with commit IDs. Learn how to<br>properly <a href='https://docs.anchorpoint.app/docs/version-control/features/binary-sync/' >setup binary syncing</a>.")
        
        self.dialog.add_checkbox(
            text="Sync Setup Dependencies",
            var="sync_dependencies",
            default=sync_dependencies,
            callback = self.store_local_settings
        )
        self.dialog.add_info("Note that you have to accept a Windows Control Popup for UE Prerequisites")  
        
        self.dialog.add_text("Launch Project",width = 100).add_dropdown(
            default=launch_project_display_name,
            values=uproject_display_names,
            var="launch_project_display_name",
            callback = self.store_local_settings
        )  
        self.dialog.add_info("Launch the Unreal Editor when the sync is complete")  

        self.dialog.add_checkbox(text="Debug Mode",var="dry_run",default=dry_run,callback = self.store_local_settings)
        self.dialog.add_info("Runs in dry run mode by only displaying prints instead of executing the real<br>synchronisation")  

        # Display shared settings only when you are an admin
        if (access_level is not aps.AccessLevel.Member):
            self.dialog.add_empty()
            self.dialog.add_text("<b>Shared Settings</b>")
            self.dialog.add_text("Tag Pattern",width = 100).add_input(
                placeholder="Editor",
                var="tag_pattern",
                default=tag_pattern,
                width = 344,
                callback = self.store_shared_settings
            )
            self.dialog.add_info("Specify a pattern for Git tags that tells Anchorpoint that there is a binary<br>attached to a commit. E.g. use <b>Editor</b> if your tag is named <b>Editor-1</b>.") 


    def get_dialog(self):
        return self.dialog
    
    def find_uproject_files(self,project_path):
    
        uproject_files = []
        depth = 3 # only dive in 3 subfolder levels
        
        # Get all directories at the specified depth (currently set to depth levels)
        for root, dirs, files in os.walk(project_path, topdown=True):
            # Skip Engine and Templates folders
            if 'Engine' in dirs:
                dirs.remove('Engine')
            if 'Templates' in dirs:
                dirs.remove('Templates')
                
            # Only process up to depth levels deep
            rel_path = os.path.relpath(root, project_path)
            if rel_path == '.' or rel_path.count(os.sep) <= depth:
                # Look for .uproject files in current directory
                for file in files:
                    if file.endswith('.uproject'):
                        full_path = os.path.join(root, file)
                        rel_path = os.path.relpath(full_path, project_path)
                        uproject_files.append(rel_path)
            
            # Stop walking deeper than depth levels
            if rel_path.count(os.sep) >= depth:
                dirs.clear()
        
        return uproject_files

    def store_shared_settings(self,dialog,value):

        ctx = ap.get_context()
        project_id = ctx.project_id
        workspace_id = ctx.workspace_id

        tag_pattern = dialog.get_value("tag_pattern")
        shared_settings = aps.SharedSettings(project_id,workspace_id,"unreal")
        shared_settings.set("_tag_pattern", tag_pattern)
        shared_settings.store()        
        return
    
    def store_local_settings(self,dialog,value):

        ctx = ap.get_context()
        project_path = ctx.project_path

        source_path = dialog.get_value("binary_source")
        sync_dependencies = dialog.get_value("sync_dependencies")
        launch_project_display_name = dialog.get_value("launch_project_display_name")  
        dry_run = dialog.get_value("dry_run")  
        
        # Store the settings for next time
        local_settings = aps.Settings()
        local_settings.set(project_path+"_binary_source", source_path)
        local_settings.set(project_path+"_sync_dependencies", sync_dependencies)
        local_settings.set(project_path+"_launch_project_display_name", launch_project_display_name)
        local_settings.set(project_path+"_dry_run", dry_run)
        local_settings.store()
        return

def on_show_project_preferences(settings_list, ctx: ap.Context):
    project = aps.get_project_by_id(ctx.project_id, ctx.workspace_id)
    if not project:
        return

    unrealSettings = UnrealProjectSettings(ctx)
    unrealSettings.name = "Unreal"
    unrealSettings.priority = 90
    unrealSettings.icon = ":/icons/organizations-and-products/unrealEngine.svg"
    settings_list.add(unrealSettings)
    