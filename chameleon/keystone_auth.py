import time

from keystoneauth1.identity import v3
from keystoneauth1 import adapter, session
from keystoneclient.v3 import client
from django.conf import settings
from projects.models import ProjectExtras

import logging
LOG = logging.getLogger(__name__)

SESSION_DEFAULT_KWARGS = {
    'timeout': 5,
}

# These projects are managed internally by Keystone/the deployment, and
# should not be touched by any sync processes
WHITELISTED_PROJECTS = set(['openstack', 'maintenance'])


def auth_url_for_region(region):
    """Given a region name, return the Keystone auth URL for that region.

    This is configured via the ``OPENSTACK_AUTH_REGIONS`` setting, e.g.:

        OPENSTACK_AUTH_REGIONS = {
            'RegionOne': 'https://idp.example.com:5000/v3',
            'RegionTwo': 'https://idp2.example.com:5000/v3',
        }

    Args:
        region (str): the name of the region.

    Returns:
        str: the Keystone authentication URL for the given region.

    Raises:
        ValueError: if no authentication URL is configured for the region.
    """
    auth_url = settings.OPENSTACK_AUTH_REGIONS.get(region)
    if not auth_url:
        raise ValueError('No auth URL defined for region {}'.format(region))
    return auth_url


def admin_session(region):
    """Create a Keystone authentication session scoped to the admin user.

    Args:
        region (str): the name of the region.

    Returns:
        adapter.Adapter: a session object with the region set as a default.
    """
    auth = v3.Password(
        auth_url=auth_url_for_region(region),
        username=settings.OPENSTACK_SERVICE_USERNAME,
        user_domain_id='default',
        password=settings.OPENSTACK_SERVICE_PASSWORD,
        project_name=settings.OPENSTACK_SERVICE_PROJECT_NAME,
        project_domain_id='default',
    )
    sess = session.Session(auth=auth, **SESSION_DEFAULT_KWARGS)
    sess = adapter.Adapter(sess, interface='public', region_name=region)
    return sess


def project_scoped_session(project_id=None, unscoped_token=None, region=None):
    """Create a Keystone authentication session scoped to a given project.

    Args:
        project_id (str): the Keystone project ID.
        unscoped_token (str): an unscoped Keystone token that will be exchanged
            for the project-scoped token. The user of the unscoped token must
            have some role in the target project.
        region (str): the name of the region.

    Returns:
        adapter.Adapter: a session object with the region set as a default.
    """
    if not (project_id and unscoped_token and region):
        raise ValueError('Not enough information to make auth request')

    auth = v3.Token(auth_url=auth_url_for_region(region), token=unscoped_token,
                    project_id=project_id)
    sess = session.Session(auth=auth, **SESSION_DEFAULT_KWARGS)
    sess = adapter.Adapter(sess, interface='public', region_name=region)
    return sess


def unscoped_user_session(region, username, password,
                          user_domain_id='default'):
    """Create a Keystone authentication session with no scope.

    Such unscoped sessions are useful mostly for storing an unscoped token that
    can be exchanged for a scoped token later.

    Args:
        region (str): the name of the region.
        username (str): the user's username.
        password (str): the user's password.
        user_domain_id (:obj:str, optional): the Keystone domain ID for the
            user. Defaults to the default domain of ``default``.

    Returns:
        session.Session: a session object explicitly unscoped for the user.
    """
    auth = v3.Password(
        auth_url=auth_url_for_region(region),
        username=username,
        password=password,
        user_domain_id=user_domain_id,
        unscoped=True,
    )
    sess = session.Session(auth=auth, **SESSION_DEFAULT_KWARGS)
    return sess


def admin_ks_client(region=None, request=None):
    """Create a Keystone client with admin credentials for a target reason.

    Args:
        region (str): an explicit region to look up the Keystone server with.
            If not set, attempts to discover this from the request.
        request (Request): the request to inspect to discover which Keystone
            server should be used.

    Returns:
        keystone.Client: a Keystone client scoped to the admin project.

    Raises:
        ValueError: if neither a region nor a request are passed as arguments.
    """
    if (not region) and request:
        region = request.session.get('services_region')

    if not region:
        raise ValueError('Cannot detect services region')

    sess = admin_session(region)
    # We have to set interface/region_name also on the Keystone client, as it
    # does not smartly inherit the value sent in on a KSA Adapter instance.
    return client.Client(session=sess, interface='public',
                         region_name=region)


def regenerate_tokens(request, password):
    """Regenerate unscoped tokens for the user for each configured region.

    If the user does not already exist in Keystone for a given region, their
    account will be automatically provisioned. The tokens generated are
    unscoped and must be exchanged for scoped project tokens to be useful.

    The tokens are stored on the user session object for later retrieval, but
    should be fetched via the `get_token` function.

    Args:
        request (Request): the authenticated parent web request.
        password (str): the password of the user.
    """
    username = request.user.username
    email = request.user.email
    tokens = {}

    for region in settings.OPENSTACK_AUTH_REGIONS.keys():
        ks_admin = admin_ks_client(region=region)
        try:
            sess = unscoped_user_session(region, username, password)
            try:
                tokens[region] = sess.get_token()
            except Exception as e:
                LOG.warning((
                    'Error retrieving OpenStack token from region {}, '
                    'retrying after syncing Keystone user').format(region))
                # It's possible the user does not yet exist in Keystone or
                # has updated their password--update the user and retry.
                sync_user(ks_admin, username=username, email=email,
                    password=password)
                tokens[region] = sess.get_token()
        except Exception as e:
            LOG.error((
                'Error retrieving Openstack Token from region: {}'
                .format(region + ', ' + e.message) + str(sys.exc_info()[0])))

    request.session['os_token'] = tokens


def get_token(request, region=None):
    if not region:
        region = request.session.get('services_region')

    if not region:
        LOG.error('Error getting token from session: no region detected')
        return None

    return request.session.get('os_token', {}).get(region)


def sync_projects(ks_admin, ks_user, tas_user_projects):
    """Sync a user's Keystone projects against their TAS active projects.

    A user's active TAS projects are compared with projects existing already
    within the target Keystone server. Any projects that don't exist at all
    are lazily provisioned. Any projects the user is currently a member of, but
    which are not in the list of their TAS projects, have the user's membership
    revoked. Similarly, any projects in Keystone that they are not yet members
    of have those memberships provisioned.

    Args:
        ks_admin (keystone.Client): a Keystone client with admin privileges.
        ks_user (keystone.User): the Keystone user that should have their
            memberships adjusted.
        tas_user_projects (List[pytas.models.Project]): a list of TAS projects
            known to be active for the target user.

    Returns:
        List[keystone.Project]: a list of all the Keystone projects the user
            is a member of, post-sync.
    """
    domain_id = ks_admin.user_domain_id

    member_role = next(iter(
        ks_admin.roles.list(name='_member_', domain=domain_id)), None)

    if not member_role:
        LOG.error('Could not fetch member role for domain, unable to sync membership for {}'.format(username))
        return []

    all_ks_projects = {
        ks_p.charge_code: ks_p
        for ks_p in ks_admin.projects.list(domain=domain_id)
        if hasattr(ks_p, 'charge_code')
    }
    tas_projects = {
        tas_p.chargeCode: tas_p
        for tas_p in tas_user_projects
    }

    tas_granted = set(tas_projects.keys())

    # Create projects that don't exist in Keystone at all
    for missing in tas_granted - set(all_ks_projects.keys()):
        ks_p = create_project(ks_admin, tas_projects[missing])
        all_ks_projects[missing] = ks_p
        LOG.debug('Created missing project %s', ks_p.name)

    # Find list of projects that user is a member of
    ks_granted = set([
        ks_p.charge_code
        for ks_p in ks_admin.projects.list(user=ks_user, domain=domain_id)
        if hasattr(ks_p, 'charge_code')
    ])

    to_add = tas_granted - ks_granted - WHITELISTED_PROJECTS
    to_remove = ks_granted - tas_granted - WHITELISTED_PROJECTS

    for charge_code in to_add:
        ks_p = all_ks_projects[charge_code]
        if not ks_p.enabled:
            ks_admin.projects.update(ks_p, enabled=True)
        ks_admin.roles.grant(member_role.id, user=ks_user, project=ks_p)
        LOG.debug('Added %s to project %s', ks_user.name, ks_p.name)

    for charge_code in to_remove:
        ks_p = all_ks_projects[charge_code]
        ks_admin.roles.revoke(member_role.id, user=ks_user, project=ks_p)
        LOG.debug('Removed %s from project %s', ks_user.name, ks_p.name)

    return [
        ks_p for ks_p in all_ks_projects.values()
        if ks_p.charge_code in tas_granted
    ]


def create_project(ks_admin, tas_project):
    """Create a new Keystone project from an existing TAS project.

    If a nickname is defined in the ProjectExtras model for this TAS project,
    it is used as the project's name.

    Args:
        ks_admin (keystone.Client): a Keystone client with admin privileges
        tas_project (pytas.models.Project): a TAS project

    Returns:
        keystone.Project: the new Keystone project.
    """
    project_extras = ProjectExtras.objects.filter(tas_project_id=tas_project.id)

    if project_extras:
        name = project_extras[0].nickname
    else:
        name = tas_project.chargeCode

    return ks_admin.projects.create(name=name,
        domain=ks_admin.user_domain_id,
        charge_code=tas_project.chargeCode,
        description=tas_project.description)


def get_user(ks_admin, username):
    """Fetch a user from Keystone by username.

    The user is fetched from the domain of the user the Keystone client is
    scoped to, which is typically the 'default' domain, but can be changed
    by passing a different client.

    Args:
        ks_admin (keystone.Client): the Keystone client, which must have admin
            privileges to perform the lookup.
        username (str): the username to lookup

    Returns:
        keystone.User: the Keystone user found for the username, or None
    """
    domain_id = ks_admin.user_domain_id
    return next(iter(
        ks_admin.users.list(name=username, domain=domain_id)), None)


def sync_user(ks_admin, username, email=None, password=None, enabled=None):
    """Sync properties to a Keystone user representation.

    This can be used to update the email, password, or enabled/disabled status
    of a Keystone user. Any updates are treated as PATCH updates; not
    specifying an argument leaves the value on the user unchanged.

    Args:
        ks_admin (keystone.Client): a Keystone client with admin privileges
        username (str): the username to update
        email (str): an email address to add/update for the user
        password (str): a password to add/update for the user
        enabled (bool): the user's new enabled status

    Returns:
        keystone.User: the user that was successfully updated. If an error
            occurs during the update, an error is logged and None is returned.
    """
    domain_id = ks_admin.user_domain_id
    try:
        ks_user = get_user(ks_admin, username)
        kwargs = {}
        if email is not None:
            kwargs['email'] = email
        if password is not None:
            kwargs['password'] = password
        if enabled is not None:
            kwargs['enabled'] = enabled

        if ks_user:
            ks_admin.users.update(user=ks_user, **kwargs)
            LOG.info('Updated user with username: {0}, email:{1}, domain_id: {2}'.format(username, email, domain_id))
            if 'password' in kwargs:
                # NOTE(jason): this is a total hack to get around some (likely)
                # bad code in Keystone. There seems to be a race condition
                # between updating a user's password and token revocation events
                # firing. If the unscoped token is generated before the
                # revocation events fire, then it will immediately become
                # invalid. There is not a great way to detect when this happens,
                # so we just have to pray that one second is enough time.
                time.sleep(1)
        else:
            kwargs['domain'] = domain_id
            kwargs['options'] = {'lock_password':True}
            ks_user = ks_admin.users.create(username, **kwargs)
            LOG.info('Created user with username: {0}, email:{1}, domain_id: {2}'.format(username, email, domain_id))
        return ks_user

    except Exception as e:
        LOG.error('Error creating user with username: {0}, email:{1}, domain_id: {2}'.format(username, email, domain_id))
        LOG.error(e)
        return None


def disable_user(username):
    """Disable a user in all Keystone deployments.

    Iterates through all regions defined in ``OPENSTACK_AUTH_REGIONS`` and
    force-disables the Keystone user in each.

    Args:
        username (str): the username to look up. The user is always looked up
            in the 'default' domain.
    """
    for region in settings.OPENSTACK_AUTH_REGIONS.keys():
        ks_admin = admin_ks_client(region=region)
        sync_user(ks_admin, username, enabled=False)
