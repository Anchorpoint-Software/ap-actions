from dataclasses import dataclass
import json
import string
from typing import Optional
from requests_oauthlib import OAuth2Session
from oauthlib.oauth2 import TokenExpiredError, AccessDeniedError
import random
import base64
import re

import apsync as aps

github_api_url = "https://api.github.com"
github_auth_url = "https://github.com/login/oauth/authorize"
redirect_uri = "https://www.anchorpoint.app/app/integration/auth"
internal_redirect_uri = "ap://integration/auth"
token_url = "https://github.com/login/oauth/access_token"
token_refresh_url = "https://github.com/login/oauth/access_token"
scope= "admin:org,read:user,repo,write:public_key" # do not change order

@dataclass
class Organization:
    """Represents a user account or an organization on GitHub"""
    id: str
    login: str
    name: str
    avatar_url: str
    is_user: bool = False

@dataclass
class RemoteRepository:
    """Represents a repository on GitHub"""
    name: str
    clone_url: str
    ssh_url: str
    repository_id: str

class GitHubClient:
    def __init__(self, workspace_id: str, client_id: str, client_secret: str) -> None:
        super().__init__()
        self.workspace_id = workspace_id
        self.client_id = client_id
        self.client_secret = client_secret

    def init(self) -> bool:
        settings = aps.Settings(f"{self.workspace_id}_github")
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

        extra = {
            'allow_signup': True,
        }

        authorization_url, _ = oauth.authorization_url(github_auth_url, state=self.state, **extra)
        webbrowser.open(authorization_url)

    def oauth2_response(self, response_url: str):  
        if "integration/auth" not in response_url:
            raise Exception("Not an GitHub OAuth2 response") 
        
        self.oauth = OAuth2Session(self.client_id, redirect_uri=redirect_uri,
                           state=self.state, scope=scope)
        
        response_url = response_url.replace(internal_redirect_uri, redirect_uri)
        token = self.oauth.fetch_token(token_url, client_secret=self.client_secret,
                                authorization_response=response_url)
        self._store_token(token)
        self.init()

    def _store_token(self, token):
        t = json.dumps(token)
        settings = aps.Settings(f"{self.workspace_id}_github")
        settings.set("token", base64.b64encode(t.encode()).decode())
        settings.store()

        import sys, os
        script_dir = os.path.join(os.path.dirname(__file__), "..", "..", "versioncontrol")
        sys.path.insert(0, script_dir)
        from vc.apgit.repository import GitRepository
        try:
            GitRepository.store_credentials("github.com", "https", "Personal Access Token", token["access_token"])
        except Exception as e:
            print(f"Could not store credentials: {str(e)}")
        finally:
            if script_dir in sys.path:
                sys.path.remove(script_dir)

    def is_setup(self) -> bool:
        settings = aps.Settings(f"{self.workspace_id}_github")
        token64 = settings.get("token", None)
        return token64 is not None
    
    def get_current_organization(self) -> Organization:
        settings = aps.Settings(f"{self.workspace_id}_github")
        org_str = settings.get("organization", None)
        if org_str:
            org_map = json.loads(base64.b64decode(org_str.encode()).decode())
            return Organization(id=org_map["id"], 
                                login=org_map["login"],
                                name=org_map["name"], 
                                avatar_url=org_map["avatar_url"],
                                is_user=org_map["is_user"])
        return None
    
    def set_current_organization(self, organization: Organization):
        org_map = {
            "id": organization.id,
            "login": organization.login,
            "name": organization.name,
            "avatar_url": organization.avatar_url,
            "is_user": organization.is_user
        }

        org_str = json.dumps(org_map)
        settings = aps.Settings(f"{self.workspace_id}_github")
        settings.set("organization", base64.b64encode(org_str.encode()).decode())
        settings.store()

    def clear_integration(self):
        settings = aps.Settings(f"{self.workspace_id}_github")
        settings.clear()
        settings.store()

        import sys, os
        script_dir = os.path.join(os.path.dirname(__file__), "..", "..", "versioncontrol")
        sys.path.insert(0, script_dir)
        from vc.apgit.repository import GitRepository
        try:
            GitRepository.erase_credentials("github.com", "https")
        except Exception as e:
            print(f"Could not erase credentials: {str(e)}")
        finally:
            if script_dir in sys.path:
                sys.path.remove(script_dir)

    def setup_refresh_token(self):
        success = self.init()
        if not success:
            return success
        try:
            self._get_current_user()
        except Exception as e:
            return False
        return True
    
    def _get_current_user(self):
        response = self.oauth.get(f"{github_api_url}/user")
        if not response:
            raise Exception("Could not get current user: ", response.text)
        
        data = response.json()
        return Organization(id=data["id"], 
                            login=data["login"],
                            name=data["name"] if data["name"] is not None else data["login"],
                            avatar_url=data["avatar_url"],
                            is_user=True)
    
    def _get_user_organizations(self):
        custom_headers = {'Accept': 'application/vnd.github+json'}
        response = self.oauth.get(f"{github_api_url}/user/orgs", headers=custom_headers)
        if not response:
            raise Exception("Could not get user organizations: ", response.text)
        data = response.json()
        orgs = []
        if not data:
            return orgs
        for org in data:
            orgs.append(Organization(id=org["id"], 
                                        login=org["login"],
                                        name=org["title"] if "title" in org else org["login"],
                                        avatar_url=org["avatar_url"], 
                                        is_user=False))
        return orgs

    def get_organizations(self):
        orgs = []
        user = self._get_current_user()
        orgs.append(user)
        orgs.extend(self._get_user_organizations())
        return orgs
    
    def generate_github_project_name(self, name):
        repo_name = name.replace(" ", "-")
        repo_name = re.sub(r"[^a-zA-Z0-9-]", "-", repo_name).lower()
        repo_name = repo_name[:100]
        return repo_name.strip("-")
    
    def _get_auto_adjusted_repository_name(self, name: str):
        pattern = re.compile(r"_(\d{2})$")
        match = pattern.search(name)
        if match:
            if match.group(1):
                number = int(match.group(1))
                new_number = number + 1
                return name[:match.start()] + "_" + "{:02d}".format(new_number)
            return name + "_01"
        return name + "_01"

    def create_repository(self, organization: Organization, name: str):
        if organization.is_user:
            url = f"{github_api_url}/user/repos"
        else:
            url = f"{github_api_url}/orgs/{organization.login}/repos"

        data = {
            "name": name,
            "private": True,
        }

        response = self.oauth.post(url, json=data)
        if not response:
            if "already exists" in response.text:
                return self.create_repository(organization, self._get_auto_adjusted_repository_name(name))
            raise Exception("Could not create repository: ", response.text)
        data = response.json()
        return RemoteRepository(name=data["name"],
                                clone_url=data["clone_url"],
                                ssh_url=data["ssh_url"],
                                repository_id=data["id"])
        
    def add_user_to_organization(self, organization: Organization, user_email: str, role: str = "direct_member"):
        if organization.is_user:
            return
        
        url = f"{github_api_url}/orgs/{organization.login}/invitations"
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
            "role": role
        }
        response = self.oauth.post(url, json=data)
        if not response:
            raise Exception("Could not invite user to organization: ", response.text)

    def remove_user_from_organization(self, organization: Organization, user_email: str):
        if organization.is_user:
            return

        members_url = f"{github_api_url}/orgs/{organization.login}/members"
        members_response = self.oauth.get(members_url)

        if members_response.status_code == 200:
            members = members_response.json()

            for member in members:
                member_email = member.get('email', '')
                member_login = member.get('login', '')

                if member_email == user_email or self._email_matches_username(user_email, member_login):
                    remove_url = f"{github_api_url}/orgs/{organization.login}/members/{member_login}"
                    remove_response = self.oauth.delete(remove_url)

                    if remove_response.status_code == 204:
                        return
                    else:
                        raise Exception("Could not remove member from organization: ", remove_response.text)

        else:
            raise Exception("Could not fetch organization members.")

        invites_url = f"{github_api_url}/orgs/{organization.login}/invitations"
        invites_response = self.oauth.get(invites_url)

        if invites_response.status_code == 200:
            invites = invites_response.json()

            for invite in invites:
                invite_email = invite.get('email', '')
                invite_login = invite.get('login', '')

                if invite_email == user_email or user_email.startswith(invite_login):
                    delete_invite_url = f"{github_api_url}/orgs/{organization.login}/invitations/{invite['id']}"
                    delete_invite_response = self.oauth.delete(delete_invite_url)

                    if delete_invite_response.status_code == 204:
                        return  # Invite removed successfully
                    else:
                        raise Exception("Could not delete invitation: ", delete_invite_response.text)

        else:
            raise Exception("Could not fetch organization invitations.")

        raise Exception("Could not remove user from organization: No matching member or invitation found.")
    
    def _email_matches_username(self, email: str, username: str) -> bool:
        email = email.replace('.', '-').replace(' ', '-')
        return email.split("@")[0] == username

    def add_user_to_repository(self, organization: Organization, user_email: str, name: str, permission: str = "maintain"):
        if organization.is_user:
            raise Exception("Organization is required.")
        
        members_url = f"{github_api_url}/orgs/{organization.login}/members"
        members_response = self.oauth.get(members_url)

        if members_response.status_code == 200:
            members = members_response.json()

            for member in members:
                member_email = member.get('email', '')
                member_login = member.get('login', '')

                if member_email == user_email or self._email_matches_username(user_email, member_login):
                    invite_url = f"{github_api_url}/repos/{organization.login}/{name}/collaborators/{member_login}"
                    data = {
                        "permission": permission
                    }

                    invite_response = self.oauth.put(invite_url, json=data)

                    if invite_response.status_code == 201 or invite_response.status_code == 204:
                        return  # User added to the repository successfully
                    else:
                        raise Exception("Could not add member to repository: ", invite_response.text)

        else:
            raise Exception("Could not get organization members.")

        raise Exception("No matching member found.")

    def remove_user_from_repository(self, organization: str, user_email: str, name: str):
        if organization.is_user:
            raise Exception("Organization is required.")

        members_url = f"{github_api_url}/orgs/{organization.login}/members"
        members_response = self.oauth.get(members_url)

        if members_response.status_code == 200:
            members = members_response.json()

            for member in members:
                member_email = member.get('email', '')
                member_login = member.get('login', '')

                if member_email == user_email or self._email_matches_username(user_email, member_login):
                    remove_url = f"{github_api_url}/repos/{organization.login}/{name}/collaborators/{member_login}"
                    remove_response = self.oauth.delete(remove_url)

                    if remove_response.status_code == 204:
                        return  # User removed from the repository successfully
                    else:
                        raise Exception("Could not delete member from repository: ", remove_response.text)

        else:
            raise Exception("Could not get organization members.")

        raise Exception("No matching member found.")