from datetime import datetime, timezone

from celery.decorators import task
from celery.utils.log import get_task_logger
from django.conf import settings
from django.contrib.auth.models import User
from django.db.models import Q
from chameleon.models import Institution, InstitutionAlias, UserInstitution
from cinderclient.v3 import client as cinder_client
import glanceclient
import novaclient
from util.keycloak_client import KeycloakClient

from .keystone_auth import (
    admin_session,
    admin_ks_client,
    get_user,
    unscoped_user_session,
    project_scoped_session,
)

LOG = get_task_logger(__name__)


class MigrationError(Exception):
    def __init__(self, messages=[]):
        self.messages = messages
        super(MigrationError, self).__init__(messages)


def run_migrate_task(bound_task, task_fn, **kwargs):
    if not kwargs.get("access_token"):
        LOG.error("Missing access token!")
        raise MigrationError(
            messages=[
                (
                    "Session appears to have timed out in the background. "
                    "Try logging out and logging in again to complete migration."
                )
            ]
        )

    messages = []

    def write_message(progress_pct, message):
        LOG.info(message)
        messages.append(message)
        bound_task.update_state(
            state="PROGRESS",
            meta={
                "messages": messages,
                "progress_pct": progress_pct,
            },
        )

    try:
        regions = list(settings.OPENSTACK_AUTH_REGIONS.keys())
        for i, region in enumerate(regions):
            job = task_fn(region, **kwargs)
            # Interpolate the total progress as a function of the total number
            # of regions; at the end, we should be at 100%.
            factor = (1.0 / len(regions)) * 100
            write_message(factor * i, f'Processing region "{region}"')
            for progress, message in job:
                write_message(factor * (i + progress), message)
    except Exception as exc:
        LOG.exception("Failed to complete migration")
        exc_message = getattr(exc, "message", None)
        if exc_message:
            messages.append(exc_message)
        raise MigrationError(messages=messages) from exc
    # Return current state as last action
    return {
        "messages": messages,
        "progress_pct": 100.0,
    }


@task(bind=True)
def migrate_project(self, **kwargs):
    """Migrate a user's keypairs and project images to new federated entities.

    This task periodically updates its state so you can query the progress of
    the migration operation. The state has the following form:

        state (str): the current state of the migration, typically 'PROGRESS'
        meta (dict): a dict with state metadata, containing:
            message (str): a summary of the last operation performed.
            current (int): which migration step is being processed
            total (int): how many steps are in the migration.

    Args:
        username (str): the username of the user to migrate. Expected to be the
            same across the default and federated Keystone domains.
        access_token (str): the user's OIDC access_token obtained during login.
        charge_code (str): the charge code for the project to migrate.
    """
    return run_migrate_task(self, _migrate_project, **kwargs)


def _migrate_project(region, username=None, charge_code=None, access_token=None):
    sess = admin_session(region)
    glance = glanceclient.Client("2", session=sess)
    keystone = admin_ks_client(region=region)
    init_progress = 0.1

    ks_legacy_user = get_user(keystone, username)
    if not ks_legacy_user:
        yield 1.0, f'User "{username}" not found in region "{region}", skipping'
        return

    ks_legacy_project = next(
        iter(
            [
                ks_p
                for ks_p in keystone.projects.list(
                    user=ks_legacy_user, domain="default"
                )
                if getattr(ks_p, "charge_code", ks_p.name) == charge_code
            ]
        ),
        None,
    )

    if not ks_legacy_project:
        yield 1.0, f'Project {charge_code} not found in region "{region}", skipping'
        return

    # Perform login, which populates projects based on current memberships
    _do_federated_login(region, access_token)

    federated_domain = next(
        iter([ks_d for ks_d in keystone.domains.list() if ks_d.name == "chameleon"])
    )
    if not federated_domain:
        raise ValueError("Could not find federated domain")
    ks_federated_project = next(
        iter(
            [
                ks_p
                for ks_p in keystone.projects.list(
                    name=charge_code, domain=federated_domain
                )
            ]
        ),
        None,
    )
    if not ks_federated_project:
        raise ValueError("Could not find corresponding federated project")

    images_to_migrate = [
        img
        for img in glance.images.list(owner=ks_legacy_project)
        if img.owner == ks_legacy_project.id
    ]
    volumes_to_migrate = []

    if region == "KVM@TACC":
        unscoped_session = unscoped_user_session(region, access_token=access_token)
        scoped_user_session = project_scoped_session(
            project_id=ks_federated_project.id,
            unscoped_token=unscoped_session.get_token(),
            region=region,
        )

        admin_cinder = cinder_client.Client(session=sess)
        user_cinder = cinder_client.Client(session=scoped_user_session)

        volumes_to_migrate = [
            v
            for v in admin_cinder.volumes.list(
                search_opts={"all_tenants": 1, "project_id": ks_legacy_project.id}
            )
        ]

    num_images = len(images_to_migrate)
    num_volumes = num_volumes = len(volumes_to_migrate)
    migrations_count = num_images + num_volumes

    if migrations_count:
        # Increment the bar slightly to show there is work being done
        progress = init_progress

        yield progress, (
            f"Will migrate {num_images} disk images and {num_volumes} volumes "
            f'for project "{charge_code}"'
        )
    else:
        progress = 0.9
        yield progress, (
            f"No images or volumes left to migrate for project " f'"{charge_code}"'
        )

    for image in images_to_migrate:
        yield progress, f'Migrating disk image "{image.name}"...'
        # Preserve already-public images
        visibility = "public" if image.visibility == "public" else "shared"
        glance.images.update(
            image.id, owner=ks_federated_project.id, visibility=visibility
        )
        glance.image_members.create(image.id, ks_legacy_project.id)
        glance.image_members.update(image.id, ks_legacy_project.id, "accepted")
        progress += (1.0 - init_progress) / migrations_count

    for volume in volumes_to_migrate:
        yield progress, f'Migrating volumes "{volume.name}"...'
        if volume.status == "available":
            transfer = admin_cinder.transfers.create(volume.id)
            user_cinder.transfers.accept(transfer.id, transfer.auth_key)
        else:
            yield progress, (
                f"Volume {volume.name} is not available to transfer. "
                f"Please detach volume from any instances and re-run "
                f"migration."
            )

        progress += (1.0 - init_progress) / migrations_count

    keystone.projects.update(
        ks_legacy_project,
        migrated_at=datetime.now(tz=timezone.utc),
        migrated_by=username,
    )
    progress = 1.0
    yield progress, f'Finished migration of region "{region}"'


@task(bind=True)
def migrate_user(self, **kwargs):
    return run_migrate_task(self, _migrate_user, **kwargs)


def _migrate_user(region, username=None, access_token=None):
    sess = admin_session(region)
    nova = novaclient.client.Client("2.72", session=sess)
    keystone = admin_ks_client(region=region)
    init_progress = 0.1

    ks_legacy_user = get_user(keystone, username)
    keypairs_to_migrate = nova.keypairs.list(user_id=ks_legacy_user.id)

    num_keypairs = len(keypairs_to_migrate)

    if num_keypairs:
        # Increment the bar slightly to show there is work being done
        progress = init_progress
        yield progress, f"Will migrate {num_keypairs} keypairs"
    else:
        progress = 0.9
        yield progress, f"No keypairs left to migrate"

    # Perform login, which populates projects based on current memberships
    ks_federated_user_id = _do_federated_login(region, access_token)

    for keypair in keypairs_to_migrate:
        yield progress, f'Migrating keypair "{keypair.name}"...'
        try:
            nova.keypairs.create(
                name=keypair.name,
                public_key=keypair.public_key,
                user_id=ks_federated_user_id,
            )
        except novaclient.exceptions.Conflict:
            yield progress, "Keypair with that name already exists, skipping."

        progress += (1.0 - init_progress) / num_keypairs

    keystone.users.update(ks_legacy_user, migrated_at=datetime.now(tz=timezone.utc))
    progress = 1.0
    yield progress, f"Successfully finished migration"


def _do_federated_login(region, access_token):
    """Perform a federated login using OIDC access token.

    Args:
        region (str): the region to authenticate to.
        access_token (str): the OIDC access token.

    Returns:
        str: the federated user ID in Keystone
    """
    sess = unscoped_user_session(region, access_token=access_token)
    return sess.get_user_id()


@task()
def update_institutions():
    """Intended to be run manually via the CLI on occasion. Edited in tandem
    with the institution admin site.
    """
    for user in User.objects.filter(institutions__isnull=True):
        keycloak_client = KeycloakClient()
        kc_user = keycloak_client.get_user_by_username(user.username)
        if not kc_user:
            # Legacy user, no login since fed. identity
            continue
        institution = kc_user.get("attributes", {}).get("affiliationInstitution")
        if institution:
            # TODO issues: Temple University is subset of TN Temple University, e.g.
            inst_obj = Institution.objects.filter(
                Q(name__iexact=institution) | Q(aliases__alias__iexact=institution)
            ).first()

            if not inst_obj:
                # Ask for institution from alias
                inst_input = input(f"Institution for '{institution}'?").strip()
                if not len(inst_input):
                    # Check if the DB was manually updated with this new institution
                    inst_obj = Institution.objects.filter(
                        Q(name__iexact=institution) | Q(aliases__alias__iexact=institution)
                    ).first()
                    if not inst_obj:
                        print(user.username, "skipping: at", institution)
                        continue
                else:
                    # Otherwise, insert new alias
                    inst_obj = Institution.objects.filter(
                        Q(name__iexact=institution) | Q(aliases__alias__iexact=institution)
                    ).first()
                    InstitutionAlias.objects.create(
                        alias=institution,
                        institution=inst_obj,
                    )
            print(user.username, "is with", inst_obj.name)
            UserInstitution.objects.create(
                user=user,
                institution=inst_obj,
            )
