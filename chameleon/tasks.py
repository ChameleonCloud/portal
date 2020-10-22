from datetime import datetime, timezone

from celery.decorators import task
from celery.utils.log import get_task_logger
from django.conf import settings
import cinderclient
import glanceclient
import novaclient

from .keystone_auth import admin_session, admin_ks_client, get_user, unscoped_user_session

LOG = get_task_logger(__name__)


class MigrationError(Exception):
    def __init__(self, messages=[]):
        self.messages = messages
        super(Exception, self).__init__(messages)


def run_migrate_task(bound_task, task_fn, **kwargs):
    if not kwargs.get('access_token'):
        LOG.error('Missing access token!')
        raise MigrationError(messages=[
            ('Session appears to have timed out in the background. '
             'Try logging out and logging in again to complete migration.')
        ])

    messages = []

    def write_message(progress_pct, message):
        LOG.info(message)
        messages.append(message)
        bound_task.update_state(state='PROGRESS', meta={
            'messages': messages, 'progress_pct': progress_pct,
        })

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
        LOG.exception('Failed to complete migration')
        exc_message = getattr(exc, 'message', None)
        if exc_message:
            messages.append(exc_message)
        raise MigrationError(messages=messages) from exc
    # Return current state as last action
    return {
        'messages': messages,
        'progress_pct': 100.0,
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
    glance = glanceclient.Client('2', session=sess)
    cinder = cinderclient.Client('3', session=sess)
    keystone = admin_ks_client(region=region)
    init_progress = 0.1

    ks_legacy_user = get_user(keystone, username)
    if not ks_legacy_user:
        yield 1.0, f'User "{username}" not found in region "{region}", skipping'
        return
    ks_legacy_project = next(iter([
        ks_p for ks_p in keystone.projects.list(user=ks_legacy_user, domain='default')
        if getattr(ks_p, 'charge_code', ks_p.name) == charge_code
    ]), None)
    if not ks_legacy_project:
        yield 1.0, f'Project {charge_code} not found in region "{region}", skipping'
        return

    # Perform login, which populates projects based on current memberships
    _do_federated_login(region, access_token)

    federated_domain = next(iter([ks_d for ks_d in keystone.domains.list() if ks_d.name == 'chameleon']))
    if not federated_domain:
        raise ValueError('Could not find federated domain')
    ks_federated_project = next(iter([
        ks_p for ks_p in keystone.projects.list(name=charge_code, domain=federated_domain)
    ]), None)
    if not ks_federated_project:
        raise ValueError('Could not find corresponding federated project')

    images_to_migrate = [
        img for img in glance.images.list(owner=ks_legacy_project)
        if img.owner == ks_legacy_project.id
    ]
    num_images = len(images_to_migrate)
    if num_images:
        # Increment the bar slightly to show there is work being done
        progress = init_progress
        yield progress, f'Will migrate {num_images} disk images for project "{charge_code}"'
    else:
        progress = 0.9
        yield progress, f'No images left to migrate for project "{charge_code}"'

    for image in images_to_migrate:
        yield progress, f'Migrating disk image "{image.name}"...'
        # Preserve already-public images
        visibility = 'public' if image.visibility == 'public' else 'shared'
        glance.images.update(image.id, owner=ks_federated_project.id, visibility=visibility)
        glance.image_members.create(image.id, ks_legacy_project.id)
        glance.image_members.update(image.id, ks_legacy_project.id, 'accepted')
        progress += ((1.0 - init_progress) / num_images)

    if sess.get_endpoint(service_type='volumev3'):
        volumes_to_migrate = [v for v in cinder.volumes.list(search_opts={
            'project_id': ks_legacy_project.id
        })]
        num_volumes = len(volumes_to_migrate)


    keystone.projects.update(ks_legacy_project,
        migrated_at=datetime.now(tz=timezone.utc),
        migrated_by=username)
    progress = 1.0
    yield progress, f'Finished migration of region "{region}"'


@task(bind=True)
def migrate_user(self, **kwargs):
    return run_migrate_task(self, _migrate_user, **kwargs)


def _migrate_user(region, username=None, access_token=None):
    sess = admin_session(region)
    nova = novaclient.client.Client('2.72', session=sess)
    keystone = admin_ks_client(region=region)
    init_progress = 0.1

    ks_legacy_user = get_user(keystone, username)
    keypairs_to_migrate = nova.keypairs.list(user_id=ks_legacy_user.id)

    num_keypairs = len(keypairs_to_migrate)

    if num_keypairs:
        # Increment the bar slightly to show there is work being done
        progress = init_progress
        yield progress, f'Will migrate {num_keypairs} keypairs'
    else:
        progress = 0.9
        yield progress, f'No keypairs left to migrate'

    # Perform login, which populates projects based on current memberships
    ks_federated_user_id = _do_federated_login(region, access_token)

    for keypair in keypairs_to_migrate:
        yield progress, f'Migrating keypair "{keypair.name}"...'
        try:
            nova.keypairs.create(
                name=keypair.name,
                public_key=keypair.public_key,
                user_id=ks_federated_user_id
            )
        except novaclient.exceptions.Conflict:
            yield progress, 'Keypair with that name already exists, skipping.'

        progress += ((1.0 - init_progress) / num_keypairs)

    keystone.users.update(ks_legacy_user,
        migrated_at=datetime.now(tz=timezone.utc))
    progress = 1.0
    yield progress, f'Successfully finished migration'


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
