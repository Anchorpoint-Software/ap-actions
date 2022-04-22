from distutils import extension
import anchorpoint as ap
import apsync as aps
import os
import mimetypes

import sys, os, importlib
sys.path.insert(0, os.path.join(os.path.split(__file__)[0], ".."))

importlib.invalidate_caches()
from vc.apgit.repository import * 

ctx = ap.Context.instance()
ui = ap.UI()
path = ctx.path

def is_not_lfs_extension(extension: str):
    return extension in [".svg", ".xml"]


def collect_binary_extensions(dir: str) -> set[str]:
    collected_files = set()
    for root, _, files in os.walk(dir, topdown=False):
        if ".git" in root: continue
        for name in files:
            filepath = os.path.join(root, name)
            type = mimetypes.guess_type(filepath)
            split = os.path.splitext(filepath)
            if len(split) < 2: continue
            extension = split[1]
            if is_not_lfs_extension(extension) == False and type and isinstance(type[0],str) and "text" not in type[0]:                
                collected_files.add(extension)

    return collected_files

def lfs_track_all_files():
    repo = GitRepository.load(path)
    if repo == None: return
    extensions = collect_binary_extensions(repo.get_root_path())
    repo.track_lfs(extensions)
    print("Tracking extensions:", extensions)
    ui.show_success("LFS tracks binaries of your project")

ctx.run_async(lfs_track_all_files)