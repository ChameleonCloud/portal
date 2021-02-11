import hashlib
import hmac
import os
from time import time

import requests
from celery.decorators import task
from celery.utils.log import get_task_logger
from django.conf import settings

from sharing_portal.models import ArtifactVersion
from sharing_portal.zenodo import DepositionMetadata, ZenodoClient

LOG = get_task_logger(__name__)


@task
def publish_to_zenodo(artifact_version_id, zenodo_access_token=None):
    LOG.info("Publishing artifact version %s to Zenodo", artifact_version_id)

    if not zenodo_access_token:
        zenodo_access_token = settings.ZENODO_DEFAULT_ACCESS_TOKEN
    artifact_version = ArtifactVersion.objects.get(pk=artifact_version_id)
    if artifact_version.deposition_repo != ArtifactVersion.CHAMELEON:
        raise ValueError(
            (
                "Can only publish Chameleon artifacts to Zenodo, this artifact is "
                'part of the "{}" repo'.format(artifact_version.deposition_repo)
            )
        )
    if artifact_version.doi:
        LOG.warning(
            "Attempted re-publish of version {}, ignoring".format(artifact_version_id)
        )
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
        version_doi = zenodo.new_deposition_version(
            metadata=metadata, doi=artifact.doi, file=r.raw
        )
    else:
        version_doi, canonical_doi = zenodo.create_deposition(
            metadata=metadata, file=r.raw
        )
        # Also store canonical Zenodo "conceptdoi", which refers to entire deposition
        if canonical_doi:
            artifact = artifact_version.artifact
            artifact.doi = canonical_doi
            artifact.save()
        else:
            LOG.error(
                "Could not get canonical DOI for deposition from Zenodo for version {}".format(
                    version_doi
                )
            )

    artifact_version.deposition_repo = ArtifactVersion.ZENODO
    artifact_version.deposition_id = version_doi
    artifact_version.save()


def _temp_url(deposition_id):
    endpoint = os.environ["ARTIFACT_SHARING_SWIFT_ENDPOINT"]
    origin = endpoint[: endpoint.index("/v1/")]
    path = "/".join(
        [
            endpoint[endpoint.index("/v1/") :],
            os.environ["ARTIFACT_SHARING_SWIFT_CONTAINER"],
            deposition_id,
        ]
    )
    key = os.environ["ARTIFACT_SHARING_SWIFT_TEMP_URL_KEY"]
    duration_in_seconds = 60
    expires = int(time() + duration_in_seconds)
    hmac_body = "GET\n{}\n{}".format(expires, path)
    sig = hmac.new(
        key.encode("utf-8"), hmac_body.encode("utf-8"), hashlib.sha1
    ).hexdigest()
    return "{origin}{path}?temp_url_sig={sig}&temp_url_expires={expires}".format(
        origin=origin, path=path, sig=sig, expires=expires
    )
