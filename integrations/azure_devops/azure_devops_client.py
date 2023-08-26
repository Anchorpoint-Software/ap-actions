from dataclasses import dataclass
import json
import time
from typing import Optional
from requests_oauthlib import OAuth2Session
from oauthlib.oauth2 import TokenExpiredError, AccessDeniedError
import requests
from urllib.parse import urlparse
from urllib.parse import parse_qs
import base64

import apsync as aps
import urllib

client_id = "46AC92C5-16D1-4BB8-9CB4-A5BBDFD9AF52"
redirect_uri = "https://www.anchorpoint.app/app/azure/auth"
scope = ["vso.identity_manage", "vso.graph_manage", "vso.code_full", "vso.code_status", "vso.memberentitlementmanagement_write", "vso.profile_write", "vso.project_manage", "vso.tokenadministration", "vso.tokens"]
azure_url = "https://app.vssps.visualstudio.com/oauth2/authorize"
client_secret = "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsIng1dCI6Im9PdmN6NU1fN3AtSGpJS2xGWHo5M3VfVjBabyJ9.eyJjaWQiOiI0NmFjOTJjNS0xNmQxLTRiYjgtOWNiNC1hNWJiZGZkOWFmNTIiLCJjc2kiOiJmODVhMjdhZC1lODZmLTQyYjItOWM0MS05MTVjYmEwNzlkYWYiLCJuYW1laWQiOiI2NDIxMTgzYi0zNWIzLTYyNWUtYTQ0NS0wYWIxZGY1OTRkNjQiLCJpc3MiOiJhcHAudnN0b2tlbi52aXN1YWxzdHVkaW8uY29tIiwiYXVkIjoiYXBwLnZzdG9rZW4udmlzdWFsc3R1ZGlvLmNvbSIsIm5iZiI6MTY3MzExNDk1NSwiZXhwIjoxODMwODgxMzU1fQ.Va39WTNEQQ3qtj4b-nV-_L8-twviVKbm6SxMRQRIBPWyuylzLRBk9d-ez6ho2m9pwrs9g3nm588Chlog-VoGmpsg3DwVDIPQDDN5Xc4cqQ9MsNu7u_64yemZMLliSxkSOp53MDeaIIVbGSV3WN5XkM828-xRAHRDJ3_QFbbD5FxiTdxTpY7a0pB-Jsv6BIDmCY0-c3HNl38ZLzFm8nBfXIc56jqmvOIxikgwj2pW-fJNIkiCCMnkwq4QedhvzTworw1_uHVKahJseaP_u8gtPBPKa89-apTsuKXJ-IJgW9DlnGXNKYQ84YOW0E9UCU6ihD1xzGE66pTYifucHtdGPQ"
token_url = "https://app.vssps.visualstudio.com/oauth2/token"
token_refresh_url = "https://app.vssps.visualstudio.com/oauth2/token"
state = "GitPython"

@dataclass
class UserProfile:
    """Represents a user profile e.g. on Azure DevOps"""
    display_name: str
    user_id: str
    email: str

@dataclass
class RemoteRepository:
    """Represents a repository e.g. on Azure DevOps"""
    display_name: str
    https_url: str
    ssh_url: Optional[str]
    project_id: str
    repository_id: str

class AzureDevOpsClient:
    def __init__(self, workspace_id: str, clear = False) -> None:
        super().__init__()
        self.workspace_id = workspace_id
        self.oauth = None
        
    def init(self) -> bool:
        settings = aps.Settings(f"{self.workspace_id}_azure_devops")
        token64 = settings.get("token", None)
        if token64:
            token = json.loads(base64.b64decode(token64.encode()).decode())
            self.oauth = OAuth2Session(client_id, redirect_uri=redirect_uri, scope=scope, token=token)
            return True
        return False
    
    def start_auth(self):
        import webbrowser
        
        oauth = OAuth2Session(client_id, redirect_uri=redirect_uri, scope=scope)
        authorization_url, _ = oauth.authorization_url(azure_url, state=state)
        webbrowser.open(authorization_url)

    def oauth2_response(self, response_url: str):  
        if "azure/auth" not in response_url:
            raise Exception("Not an Azure OAuth2 response") 
        
        authorization_response_url = parse_qs(urlparse(response_url).query)
        try:
            code = authorization_response_url["code"][0]
            state_result = authorization_response_url["state"][0]
        except:
            raise Exception("Not Authorized")

        if state_result != state:
            raise Exception("OAuth2 state is wrong")

        body = {
            "client_assertion_type": "urn:ietf:params:oauth:client-assertion-type:jwt-bearer",
            "client_assertion": client_secret,
            "assertion": code,
            "redirect_uri": redirect_uri,
            "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer"
        }

        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }

        response = requests.post(token_url, headers=headers, data=body)
        if not response:
            raise Exception("Token could not be requested: ", response.text)

        self._store_token(response.json())
        self.init()

    def _store_token(self, token):
        if token["token_type"] == "jwt-bearer":
            token["token_type"] = "bearer"

        t = json.dumps(token)
        settings = aps.Settings(f"{self.workspace_id}_azure_devops")
        settings.set("token", base64.b64encode(t.encode()).decode())
        settings.store()

    def is_setup(self) -> bool:
        settings = aps.Settings(f"{self.workspace_id}_azure_devops")
        token64 = settings.get("token", None)
        return token64 is not None
    
    def get_current_organization(self) -> str:
        settings = aps.Settings(f"{self.workspace_id}_azure_devops")
        return settings.get("organization", None)
    
    def set_current_organization(self, organization: str):
        settings = aps.Settings(f"{self.workspace_id}_azure_devops")
        settings.set("organization", organization)
        settings.store()

    def clear_integration(self):
        settings = aps.Settings(f"{self.workspace_id}_azure_devops")
        settings.clear()
        settings.store()

    def setup_refresh_token(self):
        self.init()
        body = {
            "client_assertion_type": "urn:ietf:params:oauth:client-assertion-type:jwt-bearer",
            "client_assertion": client_secret,
            "assertion": self.oauth.token["refresh_token"],
            "redirect_uri": redirect_uri,
            "grant_type": "refresh_token"
        }

        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }

        response = requests.post(token_url, headers=headers, data=body)
        if not response:
            if response.status_code == 401:
                return False
            return False
        
        self._store_token(response.json())
        return self.init()

    def _request_with_refresh(self, func, *args, **kwargs):
        def refresh_token():
            body = {
                "client_assertion_type": "urn:ietf:params:oauth:client-assertion-type:jwt-bearer",
                "client_assertion": client_secret,
                "assertion": self.oauth.token["refresh_token"],
                "redirect_uri": redirect_uri,
                "grant_type": "refresh_token"
            }

            headers = {
                "Content-Type": "application/x-www-form-urlencoded"
            }

            response = requests.post(token_url, headers=headers, data=body)
            
            if not response:
                if response.status_code == 401:
                    raise AccessDeniedError
                raise TokenExpiredError
            
            self._store_token(response.json())
            self.init()
            return func(*args, **kwargs)

        try:
            response = func(*args, **kwargs)
            if response.status_code == 203:
                raise TokenExpiredError

            if response.status_code == 401:
                print("Access denied from refresh token")
                raise AccessDeniedError

            if response.status_code != 200:
                print(response.status_code, response.reason)

            return response
        except TokenExpiredError as e:
            refresh_token()   

    def user_is_admin(self, organization: str, user: UserProfile):
        response = self._request_with_refresh(self.oauth.get, f"https://vssps.dev.azure.com/{organization}/_apis/identities?searchFilter=General&filterValue=Project+Collection+Administrators&queryMembership=direct&api-version=7.0")
        if not response:
            raise Exception("Could not check if user is admin: ", response.text)

        try:
            json = response.json()
            groups_json = json["value"]
            for group_json in groups_json:
                member_ids = group_json["memberIds"]
                return user.user_id in member_ids 
        except:
            return False


    def get_user(self) -> UserProfile:
        response = self._request_with_refresh(self.oauth.get, f"https://app.vssps.visualstudio.com/_apis/profile/profiles/me?api-version=7.0")
       
        if not response:
            raise Exception("Could not get user account: ", response.text)
        json = response.json()
        
        return UserProfile(json["displayName"], json["publicAlias"], json["emailAddress"])

    # def can_create_projects(self, organization:str, user: UserProfile):
    #     response = self._request_with_refresh(self.oauth.get, f"https://vssps.dev.azure.com/{organization}/_apis/graph/groups?scopeDescriptor={project_descriptor}&api-version=7.0-preview.1")
          
    #     if not response:
    #         raise Exception("Could not get groups of project: ", response.text)

    #     group_descriptor = None
    #     for group_json in response.json()["value"]:
    #         if group_json["principalName"] == f"[{project_name}]\\Contributors":
    #             group_descriptor = group_json["descriptor"]

    #     if not group_descriptor:
    #         raise Exception("No group descriptor found")
        
    #     user_id = self._get_user_id_by_email(organization, user_email)
    #     user_descriptor = self._get_graph_descriptor(user_id)

    #     response = self._request_with_refresh(self.oauth.delete, f"https://vssps.dev.azure.com/{organization}/_apis/graph/memberships/{user_descriptor}/{group_descriptor}?api-version=7.0-preview.1")

    #     if not response:
    #         raise Exception("Could not remove user from project: ", response.text)


    #     response = self._request_with_refresh(self.oauth.get, f"https://vsaex.dev.azure.com/{organization}/_apis/userentitlements/{user.user_id}?api-version=7.0")
    #     if not response:
    #         raise Exception("Could not check if user is admin: ", response.text)
    #     json = response.json()
    #     accessLevel = json["accessLevel"]



    def get_organizations(self, user: UserProfile):
        response = self._request_with_refresh(self.oauth.get, f"https://app.vssps.visualstudio.com/_apis/accounts?memberId={user.user_id}&api-version=7.0")
        if not response:
            raise Exception("Could not get user organizations: ", response.text)
        
        organizations_json = response.json()["value"]
        organizations = []
        for organization_json in organizations_json:
            organizations.append(organization_json["accountName"])

        return organizations

    def get_repositories(self, organization: str) -> list[RemoteRepository]:
        response = self._request_with_refresh(self.oauth.get, f"https://dev.azure.com/{organization}/_apis/projects?api-version=7.0")
        if not response:
            raise Exception("Could not get projects for organization: ", response.text)

        projects_json = response.json()
        repositories = []

        for project_json in projects_json["value"]:
            project_id = project_json["id"]
            response = self._request_with_refresh(self.oauth.get, f"https://dev.azure.com/{organization}/{project_id}/_apis/git/repositories?includeAllUrls=true&api-version=7.0")
            if not response:
                print("Could not get projects for organization: ", response.text)
                continue
            
            repositories_json = response.json()
            for repository_json in repositories_json["value"]:
                repository = RemoteRepository(repository_json["name"], repository_json["remoteUrl"], None, project_id, repository_json["id"])
                if "sshUrl" in repository_json:
                    repository.ssh_url = repository_json["sshUrl"]

                repositories.append(repository)

        return repositories

    def get_project_by_name(self, organization: str, project_name: str) -> RemoteRepository:
        repos = self.get_repositories(organization)
        for repo in repos:
            if repo.display_name == project_name:
                return repo

        raise Exception("Project could not be found")

    def create_project_and_repository(self, organization: str, name: str):
        body = {
            "name": name,
            "visibility": "private",
            "capabilities": {
                "versioncontrol": {
                "sourceControlType": "Git"
                },
                "processTemplate": {
                    "templateTypeId": "6b724908-ef14-45cf-84f8-768b5384da45"
                },
            }
        }

        response = self._request_with_refresh(self.oauth.post, f"https://dev.azure.com/{organization}/_apis/projects?api-version=7.0", json=body)
        if not response:
            raise Exception("Could not create project: ", response.text)

        operations_json = response.json()
        if operations_json["status"] in ["queued", "notSet"]:
            url = operations_json["url"]
            
            start_time = time.time()
            while True:
                if (time.time() - start_time > 180):
                    raise Exception("Project creation on Azure DevOps takes very long")
                
                time.sleep(2)

                response = self._request_with_refresh(self.oauth.get, url)
                if not response: 
                    raise Exception("Could not check project status: ", response.text)
                operation_status = response.json()["status"]
                if operation_status in ["cancelled, failed"]:
                    raise Exception("Could not create project", response.text)
                if operation_status == "succeeded":
                    repos = self.get_repositories(organization)
                    for repo in repos:
                        if repo.display_name == name:
                            return repo
                    return None

    def add_user_to_organization(self, organization: str, user_email: str):
        body = {
            "accessLevel": {
                "accountLicenseType": "express" #basic
            },
            "user": {
                "principalName": user_email,
                "subjectKind": "user"
            },
        }
        
        response = self._request_with_refresh(self.oauth.post, f"https://vsaex.dev.azure.com/{organization}/_apis/userentitlements?api-version=7.0", json=body)
        if not response:
            raise Exception("Could not add user to organization: ", response.text)

        group_name = "Project Collection Administrators"
        group_descriptor = self._get_group_descriptor_by_name(organization, group_name)        
        user_descriptor = self._get_user_descriptor_by_email(organization, user_email)
        self._add_user_to_group(organization, user_descriptor, group_descriptor, group_name)

    def add_user_to_project(self, organization: str, user_email: str, project_id: str):
        body = {
            "accessLevel": {
                "accountLicenseType": "express" #basic
            },
            "user": {
                "principalName": user_email,
                "subjectKind": "user"
            },
            "projectEntitlements": [
                {
                    "group": {
                        "groupType": "projectContributor"
                    },
                    "projectRef": {
                        "id": project_id
                    }
                }
            ]
        }
        
        response = self._request_with_refresh(self.oauth.post, f"https://vsaex.dev.azure.com/{organization}/_apis/userentitlements?api-version=7.0", json=body)
        print(f"Add user to project: {response}")
        if not response:
            raise Exception("Could not add user to repository: ", response.text)


    def remove_user_from_organization(self, organization: str, user_email: str):    
        user_id = self._get_user_id_by_email(organization, user_email)
        response = self._request_with_refresh(self.oauth.delete, f"https://vsaex.dev.azure.com/{organization}/_apis/userentitlements/{user_id}?api-version=7.0")
        print(f"Remove user from organization: {response}")
        if not response:
            raise Exception("Could not add user to repository: ", response.text) 

    def _get_graph_descriptor(self, organization: str, id: str):
        response = self._request_with_refresh(self.oauth.get, f"https://vssps.dev.azure.com/{organization}/_apis/graph/descriptors/{id}?api-version=7.0")
        if not response:
            raise Exception("Descriptor could not be found: ", response.text)

        return response.json()["value"]

    def _get_user_id_by_email(self, organization: str, user_email: str):
        response = self._request_with_refresh(self.oauth.get, f"https://vsaex.dev.azure.com/{organization}/_apis/userentitlements?$filter=name+eq+'{urllib.parse.quote(user_email)}'+and+licenseId+eq+'Account-Express'&api-version=7.0")
        if not response:
            raise Exception("Could not find user in project: ", response.text)
        
        members_json = response.json()["members"]
        for member_json in members_json:
            user_json = member_json["user"]
            if user_json["mailAddress"] == user_email:
                return member_json["id"]
        
        raise Exception("Could not find user in organization")
    
    def _get_user_descriptor_by_email(self, organization: str, user_email: str):
        users_response = self._request_with_refresh(self.oauth.get,f"https://vssps.dev.azure.com/{organization}/_apis/graph/users?api-version=7.0-preview.1")
        if not users_response or users_response.status_code != 200:
            raise Exception(f"Could not load users of {organization}: ", users_response.text)
        users_data = users_response.json()["value"];
        for user in users_data:
            if user["mailAddress"] == user_email:
                return user["descriptor"]
            
        raise Exception(f"Could not find user {user_email}")
    
    def _get_group_descriptor_by_name(self, organization: str, group_name: str):
        groups_response = self._request_with_refresh(self.oauth.get, (f"https://vssps.dev.azure.com/{organization}/_apis/graph/groups?api-version=7.0-preview.1"))
        if not groups_response or groups_response.status_code != 200:
            raise Exception(f"Could not load groups of {organization}: ", groups_response.text)
        groups_data = groups_response.json()["value"];
        for group in groups_data:
            if group["displayName"] == group_name:
                return group["descriptor"]
        
        raise Exception(f"Could not find group {group_name}")
    
    def _add_user_to_group(self, organization: str, user_descriptor: str, group_descriptor: str, group_name: str):
        membership_check_response = self._request_with_refresh(self.oauth.get,f"https://vssps.dev.azure.com/{organization}/_apis/graph/memberships/{user_descriptor}/{group_descriptor}?api-version=7.0-preview.1")
        print(membership_check_response)

        if membership_check_response.status_code == 200:
            print(f"User is already a member of {group_name} group")
        elif membership_check_response.status_code == 404:
            membership_add_response = self._request_with_refresh(self.oauth.put,f"https://vssps.dev.azure.com/{organization}/_apis/graph/memberships/{user_descriptor}/{group_descriptor}?api-version=7.0-preview.1")

            if membership_add_response.status_code == 201:
                print(f"User added to {group_name} group")
            else:
                raise Exception(f"Failed to add user to {group_name} group")
        else:
            raise Exception("Membership check failed")

    def remove_user_from_project(self, organization: str, user_email: str, project_name: str):
        project = self.get_project_by_name(organization, project_name)
        project_descriptor = self._get_graph_descriptor(project.project_id)
        
        response = self._request_with_refresh(self.oauth.get, f"https://vssps.dev.azure.com/{organization}/_apis/graph/groups?scopeDescriptor={project_descriptor}&api-version=7.0-preview.1")
          
        if not response:
            raise Exception("Could not get groups of project: ", response.text)

        group_descriptor = None
        for group_json in response.json()["value"]:
            if group_json["principalName"] == f"[{project_name}]\\Contributors":
                group_descriptor = group_json["descriptor"]

        if not group_descriptor:
            raise Exception("No group descriptor found")
        
        user_descriptor = self._get_user_descriptor_by_email(organization, user_email)

        response = self._request_with_refresh(self.oauth.delete, f"https://vssps.dev.azure.com/{organization}/_apis/graph/memberships/{user_descriptor}/{group_descriptor}?api-version=7.0-preview.1")
        print(f"Remove user from project: {response}")
        if not response:
            raise Exception("Could not remove user from project: ", response.text)
        