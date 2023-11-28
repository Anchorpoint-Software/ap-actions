import os, platform
from vc.apgit.repository import * 
from git_settings import GitProjectSettings
def on_folder_created(folder_path: str, ctx):
    # create an empty hidden .gitkeep file in the folder
    # this will make sure that the folder is tracked by git
    # and will be uploaded to the server

    settings = GitProjectSettings(ctx)
    if not settings.gitkeep_enabled():
        return
    
    if ctx.project_path is None:
        return

    repo = GitRepository.load(ctx.project_path)

    gitkeep_path = os.path.join(folder_path, ".gitkeep").replace("\\","/")
    if repo.is_sparse_checkout_enabled() and repo.is_file_in_tree(gitkeep_path):
         return

    with open(gitkeep_path, "w") as f:
        f.write("")
    
    if platform.system() == "Windows":
        os.system(f'attrib +h "{gitkeep_path}"')
