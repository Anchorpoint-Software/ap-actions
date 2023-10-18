import anchorpoint as ap
import apsync as aps

import urllib.parse
import base64
import json

def extract_repo_map(data):
    if data.startswith("ap://hook/git/"):
        arg = data.split("git/")[1]
        decoded_arg = urllib.parse.unquote(arg)
        decoded_bytes = base64.b64decode(decoded_arg)

        try:
            decoded_json = json.loads(decoded_bytes.decode('utf-8'))
        except json.JSONDecodeError:
            print("JSONDecodeError")
            return None

        if 'repo' in decoded_json and 'tags' in decoded_json:
            repo = decoded_json['repo']
            tags = decoded_json['tags']
            return {"repo": repo, "tags": tags}
        else:
            return None
    else:
        return None

def on_resolve_deeplink(url: str, ctx: ap.Context):
    map = extract_repo_map(url)

    if map is None:
        return
    
    repo = map['repo']

    projects = aps.get_projects(ctx.workspace_id)

    for project in projects:
        channel = aps.get_timeline_channel(project, "Git")
        if not channel:
            continue
        metadata = channel.metadata
        if "gitRemoteUrl" in metadata:
            url = metadata["gitRemoteUrl"]
            if url == repo:
                ap.UI().navigate_to_project(project.id, in_new_tab=True)
                return

    ap.show_create_project_dialog(remote_url=repo, tags=map['tags'])
