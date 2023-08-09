from git import GitCommandError
import anchorpoint as ap
import apsync as aps
import git_errors

import sys, os, importlib
script_dir = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, script_dir)

from vc.apgit.repository import * 
from vc.models import ConflictResolveState
if script_dir in sys.path: sys.path.remove(script_dir)

def resolve_conflicts(channel_id):
    ap.vc_resolve_conflicts(channel_id)

def on_timeline_channel_action(channel_id: str, action_id: str, ctx):
    if action_id == "gitcancelrebase":
        from git_conflicts import cancel_merge
        ctx.run_async(cancel_merge, channel_id, ctx.project_path)
        return True
    if action_id == "gitrebaseresolveconflicts": 
        ctx.run_async(resolve_conflicts, channel_id)
        return True
    return False