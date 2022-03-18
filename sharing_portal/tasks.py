import hashlib
import hmac
import os
import requests
from time import time

from celery.decorators import task
from celery.utils.log import get_task_logger
from django.conf import settings

from sharing_portal.models import ArtifactVersion, Artifact, Label
from sharing_portal import trovi
from sharing_portal.zenodo import DepositionMetadata, ZenodoClient

from keycloak.realm import KeycloakRealm
from util.keycloak_client import KeycloakClient
from collections import namedtuple

LOG = get_task_logger(__name__)


@task
def publish_to_zenodo(artifact_version_id, zenodo_access_token=None):
    LOG.info('Publishing artifact version %s to Zenodo', artifact_version_id)

    if not zenodo_access_token:
        zenodo_access_token = settings.ZENODO_DEFAULT_ACCESS_TOKEN
    artifact_version = ArtifactVersion.objects.get(pk=artifact_version_id)
    if artifact_version.deposition_repo != ArtifactVersion.CHAMELEON:
        raise ValueError((
            'Can only publish Chameleon artifacts to Zenodo, this artifact is '
            'part of the "{}" repo'.format(artifact_version.deposition_repo)))
    if artifact_version.doi:
        LOG.warning(
            'Attempted re-publish of version {}, ignoring'.format(artifact_version_id))
        return

    artifact = artifact_version.artifact
    metadata = DepositionMetadata.from_version(artifact_version)
    zenodo = ZenodoClient(access_token=zenodo_access_token)

    # Stream artifact file to Zenodo deposition
    download_url = _temp_url(artifact_version.deposition_id)
    r = requests.get(download_url, stream=True)
    r.raise_for_status()
    r.raw.decode_content = True

    if artifact.doi:
        version_doi = zenodo.new_deposition_version(metadata=metadata, doi=artifact.doi, file=r.raw)
    else:
        version_doi, canonical_doi = zenodo.create_deposition(metadata=metadata, file=r.raw)
        # Also store canonical Zenodo "conceptdoi", which refers to entire deposition
        if canonical_doi:
            artifact = artifact_version.artifact
            artifact.doi = canonical_doi
            artifact.save()
        else:
            LOG.error('Could not get canonical DOI for deposition from Zenodo for version {}'.format(version_doi))

    artifact_version.deposition_repo = ArtifactVersion.ZENODO
    artifact_version.deposition_id = version_doi
    artifact_version.save()

def _temp_url(deposition_id):
    endpoint = os.environ['ARTIFACT_SHARING_SWIFT_ENDPOINT']
    origin = endpoint[:endpoint.index('/v1/')]
    path = '/'.join([
        endpoint[endpoint.index('/v1/'):],
        os.environ['ARTIFACT_SHARING_SWIFT_CONTAINER'],
        deposition_id
    ])
    key = os.environ['ARTIFACT_SHARING_SWIFT_TEMP_URL_KEY']
    duration_in_seconds = 60
    expires = int(time() + duration_in_seconds)
    hmac_body = "GET\n{}\n{}".format(expires, path)
    sig = hmac.new(
        key.encode("utf-8"), hmac_body.encode("utf-8"), hashlib.sha1
    ).hexdigest()
    return "{origin}{path}?temp_url_sig={sig}&temp_url_expires={expires}".format(
        origin=origin, path=path, sig=sig, expires=expires
    )


@task
def sync_all_to_trovi():
    token = _get_trovi_token(client_credentials=False)
    for artifact in Artifact.objects.all():
        try:
            sync_to_trovi(artifact.pk, token=token)
        except trovi.TroviException:
            if input("skip? (y/n)") != "y":
                raise


@task
def sync_to_trovi(artifact_id, token=None):
    if not token:
        token = _get_trovi_token(client_credentials=False)
    trovi_tags = [t["tag"] for t in trovi.list_tags(token)]
    for tag in Label.objects.all():
        if tag.label not in trovi_tags:
            trovi.create_tag(token, tag.label)
            print(f"Created new tag {tag.label}")

    artifact_model = Artifact.objects.get(pk=artifact_id)
    print("Syncing {artifact.title}.")
    if artifact_model.trovi_uuid:
        print(
            f"Artifact already created on trovi {artifact_model.trovi_uuid}, checking for updates"
        )
        artifact_in_trovi = trovi.get_artifact(token, artifact_id)
        artifact_in_portal = trovi.portal_artifact_to_trovi(
            artifact_model, prompt_input=False,
        )
        patches = []
        # Simple metadata to compare
        simple_metadata_keys = [
            "title",
            "long_description",
            "title",
            "short_description",
            "owner_urn",
            "visibility",
            "tags",
            "linked_projects",
        ]
        for key in simple_metadata_keys:
            if artifact_in_trovi[key] != artifact_in_portal[key]:
                patches.append(
                    {
                        "op": "replace",
                        "path": f"/{key}",
                        "value": artifact_in_portal[key],
                    }
                )

        # Check authorship changes
        trovi_author_count = len(artifact_in_trovi["authors"])
        portal_author_count = len(artifact_in_portal["authors"])
        for i in range(min(trovi_author_count, portal_author_count)):
            # Since portal only stores name, it is all we can check for differences
            if (
                artifact_in_trovi["authors"][i]["full_name"]
                != artifact_in_portal["authors"][i]["full_name"]
            ):
                continue
                patches.append(
                    _author_patch("replace", artifact_in_portal["authors"][i], i)
                )
        if trovi_author_count < portal_author_count:
            # Add new authors
            for i in range(trovi_author_count, portal_author_count):
                patches.append(
                    _author_patch("add", artifact_in_portal["authors"][i], i)
                )
        elif trovi_author_count > portal_author_count:
            for i in range(portal_author_count, trovi_author_count):
                print(f"Removing author '{i}'")
                patches.append(
                    {
                        "op": "remove",
                        "path": f"/authors/{i}",
                    }
                )

        # Check reproducibiltity changes
        reproducibility_keys = ["access_hours", "enable_requests"]
        for key in reproducibility_keys:
            if (
                artifact_in_trovi["reproducibility"][key]
                != artifact_in_portal["reproducibility"][key]
            ):
                patches.append(
                    {
                        "op": "replace",
                        "path": f"/reproducibility/{key}",
                        "value": artifact_in_portal["reproducibility"][key],
                    }
                )

        # TODO check metrics on versions

        if patches:
            trovi.patch_artifact(token, artifact_model.trovi_uuid, patches)
    else:
        artifact_in_trovi = trovi.create_artifact(token, artifact_id)
        print(f"Created trovi artifact {artifact_in_trovi['uuid']}")
        artifact_in_portal = trovi.portal_artifact_to_trovi(
            Artifact.objects.get(pk=artifact_id),
            prompt_input=False,
        )

    # Check for new portal versions
    trovi_version_contents_urns = [
        version["contents"]["urn"] for version in artifact_in_trovi["versions"]
    ]
    for version in artifact_in_portal["versions"]:
        if version["contents"]["urn"] not in trovi_version_contents_urns:
            trovi.create_version(
                token,
                artifact_in_trovi["uuid"],
                version["contents"]["urn"],
                version["links"],
            )
            print(f"Created new version {version['contents']['urn']}")

    # Check for deleted portal versions
    portal_version_contents_urns = [
        version["contents"]["urn"] for version in artifact_in_portal["versions"]
    ]
    for version in artifact_in_trovi["versions"]:
        if version["contents"]["urn"] not in portal_version_contents_urns:
            trovi.delete_version(token, artifact_in_portal["uuid"], version["slug"])
            print(f"Deleted trovi version {version['contents']['urn']}")


def _author_patch(op, json_author, index):
    # Named tuple since get_author expects an object
    AuthorTuple = namedtuple("Author", "name affiliation ")
    author_tuple = AuthorTuple(
        name=json_author["full_name"],
        affiliation=json_author["affiliation"],
    )
    new_json_author = trovi.get_author(author_tuple)
    print(
        f"Applied '{op}' to author at index '{index}'"
        f"with {new_json_author['full_name']}"
    )
    return {
        "op": op,
        "path": f"/authors/{index}",
        "value": new_json_author,
    }


def _get_trovi_token(client_credentials=False):
    keycloak_client = KeycloakClient()
    realm = KeycloakRealm(server_url=keycloak_client.server_url, realm_name="chameleon")
    if client_credentials:
        print("Using client credentials")
        openid = realm.open_id_connect(
            client_id=keycloak_client.client_id,
            client_secret=keycloak_client.client_secret,
        )
        creds = openid.client_credentials()
    else:
        print("Using password credentials")
        openid = realm.open_id_connect(
            client_id=settings.OIDC_RP_CLIENT_ID,
            client_secret=settings.OIDC_RP_CLIENT_SECRET,
        )
        username = os.getenv("CHAMELEON_USER")
        password = os.getenv("CHAMELEON_PASS")
        if not username:
            username = input("Chameleon username: ")
        if not password:
            password = input("Chameleon password: ")
        creds = openid.password_credentials(username, password)
    return trovi.get_token(creds["access_token"], is_admin=True)["access_token"]
