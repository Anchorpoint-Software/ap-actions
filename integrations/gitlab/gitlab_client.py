from dataclasses import dataclass
import json
import string
from requests_oauthlib import OAuth2Session
import random
import base64
import re

import apsync as aps

gitlab_api_url = "https://gitlab.com/api/v4"
gitlab_auth_url = "https://gitlab.com/oauth/authorize"
redirect_uri = "https://www.anchorpoint.app/app/integration/auth"
internal_redirect_uri = "ap://integration/auth"
token_url = "https://gitlab.com/oauth/token"
token_refresh_url = "https://gitlab.com/oauth/token"
scope= "api read_user read_repository write_repository profile email" # do not change order

@dataclass
class Group:
    """Represents a user account or an group on GitLab"""
    id: str
    email: str # only for user account
    path: str # only for group
    name: str
    avatar_url: str
    is_user: bool = False

@dataclass
class Project:
    """Represents a project on GitLab"""
    id: str
    name: str
    name_with_namespace: str
    path: str
    path_with_namespace: str
    http_url_to_repo: str
    ssh_url_to_repo: str

class GitlabClient:
    def __init__(self, workspace_id: str, client_id: str, client_secret: str) -> None:
        super().__init__()
        self.workspace_id = workspace_id
        self.client_id = client_id
        self.client_secret = client_secret

    def init(self) -> bool:
        settings = aps.Settings(f"{self.workspace_id}_gitlab")
        token64 = settings.get("token", None)
        if token64:
            token = json.loads(base64.b64decode(token64.encode()).decode())

            extra = {
                'client_id': self.client_id,
                'client_secret': self.client_secret,
            }

            def token_updater(token):
                self._store_token(token)

            self.oauth = OAuth2Session(client_id=self.client_id,
                                        token=token,
                                        auto_refresh_kwargs=extra,
                                        auto_refresh_url=token_refresh_url,
                                        token_updater=token_updater,
                                        scope=scope)
            return True
        return False
    
    def start_auth(self):
        import webbrowser

        self.state = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(32))
        oauth = OAuth2Session(self.client_id, redirect_uri=redirect_uri, scope=scope)

        authorization_url, _ = oauth.authorization_url(gitlab_auth_url, state=self.state)
        print(authorization_url)
        webbrowser.open(authorization_url)

    def oauth2_response(self, response_url: str):  
        if "integration/auth" not in response_url:
            raise Exception("Not an GitLab OAuth2 response") 
        
        self.oauth = OAuth2Session(self.client_id, redirect_uri=redirect_uri,
                           state=self.state, scope=scope)
        
        response_url = response_url.replace(internal_redirect_uri, redirect_uri)
        token = self.oauth.fetch_token(token_url, client_secret=self.client_secret,
                                authorization_response=response_url)
        self._store_token(token)
        self.init()

    def _store_token(self, token):
        t = json.dumps(token)
        settings = aps.Settings(f"{self.workspace_id}_gitlab")
        settings.set("token", base64.b64encode(t.encode()).decode())
        settings.store()

    def is_setup(self) -> bool:
        settings = aps.Settings(f"{self.workspace_id}_gitlab")
        token64 = settings.get("token", None)
        return token64 is not None
    
    def get_current_group(self) -> Group:
        settings = aps.Settings(f"{self.workspace_id}_gitlab")
        org_str = settings.get("group", None)
        if org_str:
            org_map = json.loads(base64.b64decode(org_str.encode()).decode())
            return Group(id=org_map["id"], 
                                email=org_map["email"],
                                path=org_map["path"],
                                name=org_map["name"], 
                                avatar_url=org_map["avatar_url"],
                                is_user=org_map["is_user"])
        return None
    
    def set_current_group(self, group: Group):
        org_map = {
            "id": group.id,
            "email": group.email,
            "path": group.path,
            "name": group.name,
            "avatar_url": group.avatar_url,
            "is_user": group.is_user
        }

        org_str = json.dumps(org_map)
        settings = aps.Settings(f"{self.workspace_id}_gitlab")
        settings.set("group", base64.b64encode(org_str.encode()).decode())
        settings.store()

    def clear_integration(self):
        settings = aps.Settings(f"{self.workspace_id}_gitlab")
        settings.clear()
        settings.store()

    def setup_refresh_token(self):
        success = self.init()
        if not success:
            return success
        try:
            self._get_current_user()
        except Exception:
            return False
        return True
    
    def _get_current_user(self):
        response = self.oauth.get(f"{gitlab_api_url}/user")
        if not response:
            raise Exception("Could not get current user: ", response.text)
        
        data = response.json()
        return Group(id=data["id"], 
                            email=data["email"],
                            path=data["username"],
                            name=data["name"], 
                            avatar_url=data["avatar_url"],
                            is_user=True)
    
    def _get_user_groups(self):
        min_access_level = 40 #Maintainer
        response = self.oauth.get(f"{gitlab_api_url}/groups?min_access_level={min_access_level}")
        if not response:
            raise Exception("Could not get user groups: ", response.text)
        data = response.json()
        groups = []
        if not data:
            return groups
        for group in data:
            groups.append(Group(id=group["id"], 
                                        email="",
                                        path=group["path"],
                                        name=group["name"],
                                        avatar_url=group["avatar_url"], 
                                        is_user=False))
        return groups

    def get_groups(self):
        groups = []
        user = self._get_current_user()
        groups.append(user)
        groups.extend(self._get_user_groups())
        return groups
    
    def generate_gitlab_repo_name(self, name):
        repo_name = name.lower().replace(" ", "-")
        repo_name = re.sub(r"^[^a-zA-Z0-9]+|[^a-zA-Z0-9]+$", "", repo_name)
        repo_name = re.sub(r"[^a-zA-Z0-9]+", "-", repo_name)
        return repo_name
    
    def _get_auto_adjusted_project_name(self, name: str):
        pattern = re.compile(r"_(\d{2})$")  # Match any number at the end of the name
        match = pattern.search(name)
        if match:
            if match.group(1):
                number = int(match.group(1))
                new_number = number + 1
                return name[:match.start()] + "_" + "{:02d}".format(new_number)
            return name + "_01"
        return name + "_01"

    def create_project(self, group: Group, name: str):
        url = f"{gitlab_api_url}/projects"

        data = {
            "name": name,
            "path": self.generate_gitlab_repo_name(name),
            "lfs_enabled": True,
            "visibility": "private",
        }

        if not group.is_user:
            data["namespace_id"] = group.id

        response = self.oauth.post(url, json=data)
        if not response:
            if "has already been taken" in response.text:
                return self.create_project(group, self._get_auto_adjusted_project_name(name))
            raise Exception(f"Could not create repository: {response.text} and status code {response.status_code}")

        project_data = response.json()

        return Project(
            id=project_data["id"],
            name=project_data["name"],
            name_with_namespace=project_data["name_with_namespace"],
            path=project_data["path"],
            path_with_namespace=project_data["path_with_namespace"],
            http_url_to_repo=project_data["http_url_to_repo"],
            ssh_url_to_repo=project_data["ssh_url_to_repo"]
        )
        
    def add_user_to_group(self, group: Group, user_email: str):
        if group.is_user:
            return
        
        url = f"{gitlab_api_url}/groups/{group.id}/invitations"
    
        response = self.oauth.get(url)
        if response.status_code == 200:
            invitations = response.json()
            for invitation in invitations:
                if invitation.get("email") == user_email:
                    print(f"An invitation for {user_email} already exists.")
                    return
        elif response.status_code != 404:
            raise Exception("Error checking existing invitations: ", response.text)

        data = {
            "email": user_email,
            "access_level": 40  # access level maintainer
        }
        response = self.oauth.post(url, json=data)
        if response.status_code == 201:
            print(f"Invitation sent to {user_email} successfully.")
        else:
            raise Exception("Could not invite user to group: ", response.text)
        

    def _email_matches_username(self, email: str, username: str) -> bool:
        email = email.replace('.', '-').replace(' ', '-')
        return email.split("@")[0] == username

    def remove_user_from_group(self, group: Group, user_email: str):
        if group.is_user:
            return
        
        member_url = f"{gitlab_api_url}/groups/{group.id}/members"
        response = self.oauth.get(member_url)

        if response.status_code == 200:
            members = response.json()
            for member in members:
                if self._email_matches_username(user_email, member.get("username")):
                    # Found the user as a member, remove them
                    remove_url = f"{member_url}/{member['id']}"
                    remove_response = self.oauth.delete(remove_url)
                    if remove_response.status_code == 204:
                        print(f"User {user_email} removed from the group successfully.")
                        return
                    else:
                        raise Exception(f"Error removing user from the group: {remove_response.text}")

        elif response.status_code != 404:
            raise Exception("Error checking group members: ", response.text)

        invitation_url = f"{gitlab_api_url}/groups/{group.id}/invitations"
        response = self.oauth.get(invitation_url)

        if response.status_code == 200:
            invitations = response.json()
            for invitation in invitations:
                if invitation.get("email") == user_email:
                    delete_url = f"{invitation_url}/{invitation['id']}"
                    delete_response = self.oauth.delete(delete_url)
                    if delete_response.status_code == 204:
                        print(f"Pending invitation for {user_email} deleted successfully.")
                        return
                    else:
                        raise Exception(f"Error deleting pending invitation: {delete_response.text}")

        elif response.status_code != 404:
            raise Exception("Error checking pending invitations: ", response.text)
        
        raise Exception("Could not remove user from organization: No matching member or invitation found.")
    

    def _get_project_id_by_name(self, project_name, group: Group):
        projects_url = f"{gitlab_api_url}/projects?search={project_name}&membership=true"
        response = self.oauth.get(projects_url)

        if response.status_code == 200:
            projects = response.json()
            for project in projects:
                if project["namespace"]["path"] == group.path and project["name"] == project_name:
                    return project["id"]

        raise Exception("Project not found.")
    
    def _is_user_invited_to_project(self, project_id, user_email):
        invites_url = f"{gitlab_api_url}/projects/{project_id}/invitations"
        response = self.oauth.get(invites_url)

        if response.status_code == 200:
            invites = response.json()
            for invite in invites:
                if invite["invite_email"] == user_email:
                    return True
            return False

        raise Exception("Failed to check project invitations.")
    
    def _invite_user_to_project(self, project_id, user_email):
        invite_url = f"{gitlab_api_url}/projects/{project_id}/invitations"
        data = {
            "email": user_email,
            "access_level": 40  # access level maintainer
        }
        response = self.oauth.post(invite_url, json=data)

        if response.status_code == 201:
            return True
        else:
            raise Exception("Failed to invite user to project.")

    def _remove_invited_user_from_project(self, project_id, user_email):
        remove_invite_url = f"{gitlab_api_url}/projects/{project_id}/invitations/{user_email}"
        response = self.oauth.delete(remove_invite_url)

        if not response:
            raise Exception("Failed to remove user from project.")
        return True

    def add_user_to_project(self, group: Group, user_email: str, name: str):
        project_id = self._get_project_id_by_name(name, group)
        if not self._is_user_invited_to_project(project_id, user_email):
            self._invite_user_to_project(project_id, user_email)

    def remove_user_from_project(self, group: Group, user_email: str, name: str):
        project_id = self._get_project_id_by_name(name, group)
        if self._is_user_invited_to_project(project_id, user_email):
            self._remove_invited_user_from_project(project_id, user_email)
            return

        member_url = f"{gitlab_api_url}/projects/{project_id}/members"
        response = self.oauth.get(member_url)

        if response.status_code == 200:
            members = response.json()
            for member in members:
                if self._email_matches_username(user_email, member.get("username")):
                    # Found the user as a member, remove them
                    remove_url = f"{member_url}/{member['id']}"
                    remove_response = self.oauth.delete(remove_url)
                    if remove_response.status_code == 204:
                        print(f"User {user_email} removed from the group successfully.")
                        return
                    else:
                        raise Exception(f"Error removing user from the group: {remove_response.text}")
        
        raise Exception("No matching member or invitation found.")