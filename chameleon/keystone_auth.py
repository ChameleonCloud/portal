import time

from keystoneauth1.identity import v3
from keystoneauth1 import adapter, session
from keystoneclient.v3 import client
from django.conf import settings
from projects.models import ProjectExtras

import logging

LOG = logging.getLogger(__name__)

SESSION_DEFAULT_KWARGS = {
    "timeout": 5,
}

# These projects are managed internally by Keystone/the deployment, and
# should not be touched by any sync processes
WHITELISTED_PROJECTS = set(["openstack", "maintenance"])


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
        raise ValueError("No auth URL defined for region {}".format(region))
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
        user_domain_id="default",
        password=settings.OPENSTACK_SERVICE_PASSWORD,
        project_name=settings.OPENSTACK_SERVICE_PROJECT_NAME,
        project_domain_id="default",
    )
    sess = session.Session(auth=auth, **SESSION_DEFAULT_KWARGS)
    sess = adapter.Adapter(sess, interface="public", region_name=region)
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
        region = request.session.get("services_region")

    if not region:
        raise ValueError("Cannot detect services region")

    sess = admin_session(region)
    # We have to set interface/region_name also on the Keystone client, as it
    # does not smartly inherit the value sent in on a KSA Adapter instance.
    return client.Client(session=sess, interface="public", region_name=region)


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
    return next(iter(ks_admin.users.list(name=username, domain=domain_id)), None)


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
            kwargs["email"] = email
        if password is not None:
            kwargs["password"] = password
        if enabled is not None:
            kwargs["enabled"] = enabled

        if ks_user:
            ks_admin.users.update(user=ks_user, **kwargs)
            LOG.info(
                "Updated user with username: {0}, email:{1}, domain_id: {2}".format(
                    username, email, domain_id
                )
            )
            if "password" in kwargs:
                # NOTE(jason): this is a total hack to get around some (likely)
                # bad code in Keystone. There seems to be a race condition
                # between updating a user's password and token revocation events
                # firing. If the unscoped token is generated before the
                # revocation events fire, then it will immediately become
                # invalid. There is not a great way to detect when this happens,
                # so we just have to pray that one second is enough time.
                time.sleep(1)
        else:
            kwargs["domain"] = domain_id
            kwargs["options"] = {"lock_password": True}
            ks_user = ks_admin.users.create(username, **kwargs)
            LOG.info(
                "Created user with username: {0}, email:{1}, domain_id: {2}".format(
                    username, email, domain_id
                )
            )
        return ks_user

    except Exception as e:
        LOG.error(
            "Error creating user with username: {0}, email:{1}, domain_id: {2}".format(
                username, email, domain_id
            )
        )
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
    for region in list(settings.OPENSTACK_AUTH_REGIONS.keys()):
        ks_admin = admin_ks_client(region=region)
        sync_user(ks_admin, username, enabled=False)
