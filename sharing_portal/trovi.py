import requests
import os
from urllib.parse import urljoin, urlparse, urlencode
from sharing_portal.models import Artifact
from django.conf import settings
from django.contrib.auth.models import User
from django.db.models.functions import Concat
from django.db.models import Value
from keycloak.realm import KeycloakRealm
from util.keycloak_client import KeycloakClient
from projects.models import Project


class TroviException(Exception):
    pass


def url_with_token(path, token, query=None):
    if not query:
        query = {}
    query["access_token"] = token
    return urljoin(os.getenv("TROVI_API_BASE_URL"), f"{path}?{urlencode(query)}")


def check_status(response, code):
    if response.status_code != code:
        try:
            response_json = response.json()
            detail = response_json.get(
                "detail", response_json.get("error_description", response.text)
            )
        except AttributeError:
            detail = response.text
        except requests.exceptions.JSONDecodeError:
            if response.status_code == 500:
                detail = ""
            else:
                detail = response.text
        request = response.request
        request_path = urlparse(request.url).path
        message = (
            f"{request.method} {request_path} {response.status_code} "
            f"returned, expected {code}: {detail}"
        )
        raise TroviException(message)


def get_client_admin_token():
    keycloak_client = KeycloakClient()
    realm = KeycloakRealm(server_url=keycloak_client.server_url, realm_name="master")
    openid = realm.open_id_connect(
        client_id=keycloak_client.client_id, client_secret=keycloak_client.client_secret
    )
    creds = openid.client_credentials()
    return get_token(creds["access_token"], is_admin=True)["access_token"]


def get_token(token, is_admin=False):
    scopes = ["artifacts:read", "artifacts:write"]
    if is_admin:
        scopes.append("trovi:admin")
    res = requests.post(
        urljoin(os.getenv("TROVI_API_BASE_URL"), "/token/"),
        json={
            "grant_type": "token_exchange",
            "subject_token": token,
            "subject_token_type": "urn:ietf:params:oauth:token-type:jwt",
            "scope": " ".join(scopes),
        },
    )
    check_status(res, requests.codes.created)
    return res.json()


def list_artifacts(token, sort_by="updated_at"):
    res = requests.get(
        url_with_token("/artifacts/", token, query=dict(sort_by=sort_by))
    )
    check_status(res, requests.codes.ok)
    return res.json()["artifacts"]


def list_tags(token):
    res = requests.get(url_with_token("/meta/tags/", token))
    check_status(res, requests.codes.ok)
    return res.json()["tags"]


def create_tag(token, tag):
    json_data = {"tag": tag}
    res = requests.post(url_with_token("/meta/tags/", token), json=json_data)
    check_status(res, requests.codes.created)
    return res.json()["tag"]


def get_author(author, prompt_input=False):
    matching_users = list(
        User.objects.annotate(full_name=Concat("first_name", Value(" "), "last_name"))
        .filter(full_name=author.name.strip())
        .all()
    )
    if not matching_users:
        if prompt_input:
            email = input(f"Email for {author.name} at {author.affiliation}: ")
        else:
            email = None
    else:
        # Use .edu address if there is just one
        edu_user = None
        for user in matching_users:
            if user.email.endswith(".edu"):
                # If multiple matches, break and force manual input
                if edu_user:
                    edu_user = None
                    break
                edu_user = user

        if edu_user:
            print("Using only .edu address", edu_user.email)
            selected_user = edu_user
        else:
            selected_user = matching_users[0]
            if len(matching_users) > 1 and prompt_input:
                print(f"Email for {author.name} at {author.affiliation}")
                for idx, user in enumerate(matching_users):
                    print(f"[{idx}]", user.first_name, user.last_name, user.email)
                selected_user = matching_users[int(input("index: "))]
        email = selected_user.email
    return {
        "full_name": author.name.strip(),
        "affiliation": author.affiliation,
        "email": email,
    }


def portal_artifact_to_trovi(portal_artifact, prompt_input=False):
    trovi_artifact = {
        "tags": [label.label for label in portal_artifact.labels.all()],
        "authors": [
            get_author(author, prompt_input) for author in portal_artifact.authors.all()
        ],
        "linked_projects": []
        if not portal_artifact.project
        else [
            f"urn:trovi:project:{settings.ARTIFACT_OWNER_PROVIDER}:{portal_artifact.project.charge_code}"
        ],
        "reproducibility": {
            "enable_requests": portal_artifact.is_reproducible,
            "access_hours": portal_artifact.reproduce_hours,
        },
        "title": portal_artifact.title,
        "short_description": portal_artifact.short_description or portal_artifact.title,
        "long_description": portal_artifact.description,
        "owner_urn": f"urn:trovi:user:{settings.ARTIFACT_OWNER_PROVIDER}:{portal_artifact.created_by.username}",
        "visibility": "public" if portal_artifact.is_public else "private",
    }
    # If existing
    if portal_artifact.trovi_uuid:
        trovi_artifact["uuid"] = portal_artifact.trovi_uuid
        trovi_artifact["versions"] = [
            {
                "contents": {
                    "urn": f"urn:trovi:contents:{version.deposition_repo}:{version.deposition_id}"
                },
                "metrics": {"access_count": version.launch_count},
                "links": [],
                #"created_at": version.created_at.strftime(settings.ARTIFACT_DATETIME_FORMAT),
            }
            for version in portal_artifact.versions.all()
        ]
        trovi_artifact["created_at"] = portal_artifact.created_at.strftime(settings.ARTIFACT_DATETIME_FORMAT)
    else:
        all_versions = list(portal_artifact.versions.all())
        if all_versions:
            version = all_versions[0]
            trovi_artifact["version"] = {
                "contents": {
                    "urn": f"urn:trovi:contents:{version.deposition_repo}:{version.deposition_id}"
                },
                "links": [],
            }
    return trovi_artifact


def get_artifact(token, artifact_id):
    artifact = Artifact.objects.get(pk=artifact_id)
    url = url_with_token(f"/artifacts/{artifact.trovi_uuid}/", token)
    res = requests.get(url)
    check_status(res, requests.codes.ok)
    return res.json()


def get_artifact_by_trovi_uuid(token, artifact_id, sharing_key=None):
    if sharing_key:
        url = url_with_token(
            f"/artifacts/{artifact_id}/", token, query=dict(sharing_key=sharing_key)
        )
    else:
        url = url_with_token(f"/artifacts/{artifact_id}/", token)
    res = requests.get(url)
    check_status(res, requests.codes.ok)
    return res.json()


def create_artifact(token, artifact_id, prompt_input=False):
    artifact = Artifact.objects.get(pk=artifact_id)
    json_data = portal_artifact_to_trovi(artifact, prompt_input=prompt_input)
    while len(json_data["title"]) > 70:
        print(f"This title is {len(json_data['title'])} chars (max 70)")
        print(json_data["title"])
        json_data["title"] = input("New title: ")
    res = requests.post(url_with_token("/artifacts/", token), json=json_data)
    check_status(res, requests.codes.created)
    trovi_artifact = res.json()
    artifact.trovi_uuid = trovi_artifact["uuid"]
    artifact.save()
    return trovi_artifact


def patch_artifact(token, artifact_uuid, patches, force=False):
    json_data = {"patch": patches}
    print(json_data)
    query = {}
    if force:
        query["force"] = True
    res = requests.patch(
        url_with_token(f"/artifacts/{artifact_uuid}/", token, query=query),
        json=json_data,
    )
    check_status(res, requests.codes.ok)
    return res.json()


def create_version(token, trovi_artifact_uuid, contents_urn, links=None):
    json_data = {"contents": {"urn": contents_urn}}
    if links:
        json_data["links"] = links
    res = requests.post(
        url_with_token(f"/artifacts/{trovi_artifact_uuid}/versions/", token),
        json=json_data,
    )
    check_status(res, requests.codes.created)
    return res.json()


def delete_version(token, trovi_artifact_uuid, slug):
    res = requests.delete(
        url_with_token(f"/artifacts/{trovi_artifact_uuid}/versions/{slug}/", token),
    )
    check_status(res, requests.codes.no_content)


def increment_metric_count(
        artifact_id, version_slug, token=None, metric="access_count", amount=1
):
    if not token:
        token = get_client_admin_token()
    query = {
        "metric": metric,
        "amount": amount,
        "origin": token,
    }
    res = requests.put(
        url_with_token(
            f"/artifacts/{artifact_id}/versions/{version_slug}/metrics/",
            token,
            query=query,
        )
    )
    check_status(res, requests.codes.no_content)


def parse_project_urn(project_urn):
    provider, project_id = project_urn.split(":", 4)[3:]
    return {
        "provider": provider,
        "id": project_id,
    }


def parse_owner_urn(owner_urn):
    provider, project_id = owner_urn.split(":", 4)[3:]
    return {
        "provider": provider,
        "id": project_id,
    }


def parse_contents_urn(contents_urn):
    provider, contents_id = contents_urn.split(":", 4)[3:]
    return {
        "provider": provider,
        "id": contents_id,
    }


def get_linked_project(artifact):
    chameleon_projects = [
        parse_project_urn(lp)
        for lp in artifact["linked_projects"]
        if parse_project_urn(lp)["provider"] == "chameleon"
    ]
    if not chameleon_projects:
        return None
    charge_code = chameleon_projects[0]["id"]
    return Project.objects.get(charge_code=charge_code)


def set_linked_project(artifact, charge_code, token=None):
    # Note this operation is `set` since we only allow one `chameleon` project
    # on a trovi artifact
    new_urn = f"urn:trovi:project:chameleon:{charge_code}"
    project_indices = [
        i
        for i, project in enumerate(artifact["linked_projects"])
        if project.split(":", 4)[3] == "chameleon"
    ]
    patches = []
    # Replace index if it exists
    if project_indices:
        patches.append(
            {
                "op": "replace",
                "path": f"/linked_projects/{project_indices[0]}",
                "value": new_urn,
            }
        )
    else:
        patches.append({"op": "add", "path": "/linked_projects/-", "value": new_urn})
    if token:
        patch_artifact(token, artifact["uuid"], patches)
    else:
        patch_artifact(get_client_admin_token(), artifact["uuid"], patches)
