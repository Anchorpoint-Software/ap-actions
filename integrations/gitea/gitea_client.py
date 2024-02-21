from dataclasses import dataclass
import json
import string
from typing import Optional
from requests_oauthlib import OAuth2Session
import random
import base64
import os
import re

import apsync as aps

gitea_shared_settings_key = "gitea_self_hosted"
gitea_host_url_key = "gitea_host_url"
gitea_client_id_key = "client_id"
gitea_client_secret_key = "client_secret"

redirect_uri = "https://www.anchorpoint.app/app/integration/auth"
internal_redirect_uri = "ap://integration/auth"
scope= "write:organization write:repository write:user" # do not change order

@dataclass
class Organization:
    """Represents a user account or an organization on Gitea"""
    id: str
    email: str # only for user account
    name: str
    avatar_url: str
    is_user: bool = False

@dataclass
class Project:
    """Represents a project on Gitea"""
    id: str
    name: str
    full_name: str
    clone_url: str
    html_url: str

class GiteaClient:
    def __init__(self, workspace_id: str) -> None:
        super().__init__()
        self.workspace_id = workspace_id

    def init(self) -> bool:
        settings = aps.Settings(f"{self.workspace_id}_gitea_self_hosted")
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
                                        auto_refresh_url=f"{self.host_url}/login/oauth/access_token",
                                        token_updater=token_updater,
                                        scope=scope)
            return True
        return False
    
    def is_server_reachable(self, host_url: str) -> bool:
        import requests
        try:
            response = requests.get(host_url)
            return response.status_code == 200
        except Exception:
            return False
        
    def get_host_url(self) -> Optional[str]:
        return self.host_url
    
    def start_auth(self):
        import webbrowser

        self.state = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(32))
        oauth = OAuth2Session(self.client_id, redirect_uri=redirect_uri, scope=scope)
        authorization_url, _ = oauth.authorization_url(f"{self.host_url}/login/oauth/authorize", state=self.state, verify=False)
        webbrowser.open(authorization_url)

    def oauth2_response(self, response_url: str):  
        if "integration/auth" not in response_url:
            raise Exception("Not an Gitea OAuth2 response") 
        
        self.oauth = OAuth2Session(self.client_id, redirect_uri=redirect_uri,
                           state=self.state, scope=scope)
        
        response_url = response_url.replace(internal_redirect_uri, redirect_uri)
        token = self.oauth.fetch_token(f"{self.host_url}/login/oauth/access_token",
                                authorization_response=response_url, client_secret=self.client_secret, state=self.state, verify=False)
        self._store_token(token)
        self.init()

    def _store_token(self, token):
        t = json.dumps(token)
        settings = aps.Settings(f"{self.workspace_id}_gitea_self_hosted")
        settings.set("token", base64.b64encode(t.encode()).decode())
        settings.store()

    def store_for_workspace(self, host_url: str, client_id: str, client_secret: str):
        sharedSettings = aps.SharedSettings(self.workspace_id, gitea_shared_settings_key)
        host_url = host_url.rstrip('/')
        sharedSettings.set(gitea_host_url_key, base64.b64encode(host_url.encode()).decode())
        sharedSettings.set(gitea_client_id_key, base64.b64encode(client_id.encode()).decode())
        sharedSettings.set(gitea_client_secret_key, base64.b64encode(client_secret.encode()).decode())
        sharedSettings.store()

    def setup_workspace_settings(self):
        sharedSettings = aps.SharedSettings(self.workspace_id, gitea_shared_settings_key)
        host_url = sharedSettings.get(gitea_host_url_key, None)
        if host_url:
            self.host_url = base64.b64decode(host_url.encode()).decode()
            if self.host_url.startswith("http://"):
                os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
        client_id = sharedSettings.get(gitea_client_id_key, None)
        if client_id:
            self.client_id = base64.b64decode(client_id.encode()).decode()
        client_secret = sharedSettings.get(gitea_client_secret_key, None)
        if client_secret:
            self.client_secret = base64.b64decode(client_secret.encode()).decode()

    def is_setup_for_workspace(self) -> bool:
        sharedSettings = aps.SharedSettings(self.workspace_id, gitea_shared_settings_key)
        if sharedSettings.get(gitea_host_url_key, None) is None:
            return False
        if sharedSettings.get(gitea_client_id_key, None) is None:
            return False
        if sharedSettings.get(gitea_client_secret_key, None) is None:
            return False
        return True

    def is_setup(self) -> bool:
        if not self.is_setup_for_workspace():
            return False
        settings = aps.Settings(f"{self.workspace_id}_gitea_self_hosted")
        token64 = settings.get("token", None)
        return token64 is not None
    
    def get_current_organization(self) -> Organization:
        settings = aps.Settings(f"{self.workspace_id}_gitea_self_hosted")
        org_str = settings.get("organization", None)
        if org_str:
            org_map = json.loads(base64.b64decode(org_str.encode()).decode())
            return Organization(id=org_map["id"], 
                                email=org_map["email"],
                                name=org_map["name"], 
                                avatar_url=org_map["avatar_url"],
                                is_user=org_map["is_user"])
        return None
    
    def set_current_organization(self, org: Organization):
        org_map = {
            "id": org.id,
            "email": org.email,
            "name": org.name,
            "avatar_url": org.avatar_url,
            "is_user": org.is_user
        }

        org_str = json.dumps(org_map)
        settings = aps.Settings(f"{self.workspace_id}_gitea_self_hosted")
        settings.set("organization", base64.b64encode(org_str.encode()).decode())
        settings.store()

    def clear_integration(self, clear_workspace_settings: bool = False):
        settings = aps.Settings(f"{self.workspace_id}_gitea_self_hosted")
        settings.clear()
        settings.store()
        if clear_workspace_settings:
            sharedSettings = aps.SharedSettings(self.workspace_id, gitea_shared_settings_key)
            sharedSettings.clear()
            self.host_url = None
            self.client_id = None
            self.client_secret = None

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
        response = self.oauth.get(f"{self.host_url}/api/v1/user")
        if not response:
            raise Exception("Could not get current user: ", response.text)
        
        data = response.json()
        return Organization(id=data["id"], 
                            email=data["email"],
                            name=data["login_name"] if data["login_name"] is not None and data["login_name"] != '' else data["login"],
                            avatar_url=data["avatar_url"],
                            is_user=True)
    
    def _get_user_organizations(self):
        response = self.oauth.get(f"{self.host_url}/api/v1/user/orgs")
        if not response:
            raise Exception("Could not get user organizations: ", response.text)
        data = response.json()
        orgs = []
        if not data:
            return orgs
        for org in data:
            orgs.append(Organization(id=org["id"], 
                                        email="",
                                        name=org["name"],
                                        avatar_url=org["avatar_url"], 
                                        is_user=False))
        return orgs

    def get_organizations(self):
        orgs = []
        user = self._get_current_user()
        orgs.append(user)
        orgs.extend(self._get_user_organizations())
        return orgs
    
    def generate_gitea_repo_name(self, name):
        repo_name = name.lower().replace(" ", "_")
        repo_name = re.sub(r"^[^a-zA-Z0-9]+|[^a-zA-Z0-9]+$", "", repo_name)
        repo_name = re.sub(r"[^a-zA-Z0-9]+", "_", repo_name)
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

    def create_project(self, org: Organization, name: str):
        if org.is_user:
            url = f"{self.host_url}/api/v1/user/repos"
        else:
            url = f"{self.host_url}/api/v1/org/{org.name}/repos"

        data = {
            "name": self.generate_gitea_repo_name(name),
            "description": "Project created from Anchorpoint",
            "private": True,
            "auto_init": False,
            "readme": "",
            "issue_labels": "",
        }

        response = self.oauth.post(url, json=data)
        if not response:
            if "already exists" in response.text:
                return self.create_project(org, self._get_auto_adjusted_project_name(name))
            raise Exception("Could not create repository: ", response.text)

        project_data = response.json()

        return Project(
            id=project_data["id"],
            name=project_data["name"],
            full_name=project_data["full_name"],
            clone_url=project_data["clone_url"],
            html_url=project_data["html_url"]
        )
    
    def _get_username_from_email(self, email: str) -> str:
        email = email.replace(' ', '-')
        return email.split("@")[0]
    
    def _email_matches_username(self, email: str, username: str) -> bool:
        return self._get_username_from_email(email) == username
        
    def add_user_to_organization(self, org: Organization, user_email: str):
        if org.is_user:
            return
        
        url = f"{self.host_url}/api/v1/orgs/{org.name}/teams?limit=100"
    
        response = self.oauth.get(url)
        if response.status_code != 200:
            raise Exception("Could not get teams: ", response.text)
    
        team_id = None
        teams = response.json()
        for team in teams:
            if team.get("name") == "Owners":
                team_id = team.get("id")
            
        if not team_id:
            raise Exception(f"Could not find Owners team for {org.name}.")
        
        url = f"{self.host_url}/api/v1/teams/{team_id}/members?=limit=1000"

        response = self.oauth.get(url)
        if response.status_code != 200:
            raise Exception("Could not get team members: ", response.text)
        
        members = response.json()
        for member in members:
            if member.get("email") == user_email or self._email_matches_username(user_email, member.get("login")):
                return
        
        user_name = self._get_username_from_email(user_email)

        url = f"{self.host_url}/api/v1/teams/{team_id}/members/{user_name}"
        response = self.oauth.put(url)
        if response.status_code != 204:
            raise Exception("Could not add user to team: ", response.text)

    def _email_matches_username(self, email: str, username: str) -> bool:
        email = email.replace('.', '-').replace(' ', '-')
        return email.split("@")[0] == username

    def remove_user_from_organization(self, org: Organization, user_email: str):
        if org.is_user:
            return
        
        url = f"{self.host_url}/api/v1/orgs/{org.name}/teams?limit=100"
    
        response = self.oauth.get(url)
        if response.status_code != 200:
            raise Exception("Could not get teams: ", response.text)
    
        team_id = None
        teams = response.json()
        for team in teams:
            if team.get("name") == "Owners":
                team_id = team.get("id")
            
        if not team_id:
            raise Exception(f"Could not find Owners team for {org.name}.")
        
        url = f"{self.host_url}/api/v1/teams/{team_id}/members?=limit=1000"

        response = self.oauth.get(url)
        if response.status_code != 200:
            raise Exception("Could not get team members: ", response.text)
        
        members = response.json()
        for member in members:
            if member.get("email") == user_email or self._email_matches_username(user_email, member.get("login")):
                url = f"{self.host_url}/api/v1/teams/{team_id}/members/{member.get('login')}"
                response = self.oauth.delete(url)
                if response.status_code != 204:
                    raise Exception("Could not remove user from team: ", response.text)
                return
        
        raise Exception(f"Could not find user {user_email} in organization {org.name}.")

    def add_user_to_repository(self, org: Organization, user_email: str, name: str):
        owner = org.name
        repo = self.generate_gitea_repo_name(name)
        username = self._get_username_from_email(user_email)

        url = f"{self.host_url}/api/v1/repos/{owner}/{repo}/collaborators/{username}"

        body = {
            "permission": "2"
        }
        response = self.oauth.put(url, data=body)
        if response.status_code != 204:
            raise Exception("Could not add user to repository: ", response.text)
        

    def remove_user_from_repository(self, org: Organization, user_email: str, name: str):
        owner = org.name
        repo = self.generate_gitea_repo_name(name)
        username = self._get_username_from_email(user_email)

        url = f"{self.host_url}/api/v1/repos/{owner}/{repo}/collaborators/{username}"
        response = self.oauth.delete(url)
        if response.status_code != 204:
            raise Exception("Could not remove user from repository: ", response.text)