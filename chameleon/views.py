import logging
from urllib.parse import urlencode, urlsplit

from django.conf import settings
from django.contrib.auth.models import User
from django.urls import reverse
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.utils import timezone
from django.views.decorators.cache import cache_page
from django.views.decorators.http import require_http_methods
from djangoRT import rtUtil
from mozilla_django_oidc.views import OIDCAuthenticationRequestView
import requests

from chameleon.edge_hw_discovery_api import EDGE_HW_API
from .models import Dataset, DatasetDownloadEvent
from user_news.models import Outage
from util.project_allocation_mapper import ProjectAllocationMapper

LOG = logging.getLogger(__name__)

edge_api = EDGE_HW_API()


@login_required
def dashboard(request):
    context = {}
    # active projects...
    mapper = ProjectAllocationMapper(request)
    active_projects = mapper.get_user_projects(
        request.user,
        alloc_status=["active", "approved", "pending"],
        to_pytas_model=True,
    )
    context["active_projects"] = active_projects

    # open tickets...
    rt = rtUtil.DjangoRt()
    context["open_tickets"] = rt.getUserTickets(request.user.email)
    context["logged_in_tickets"] = rt.logged_in

    # ongoing outages...
    outages = [
        o for o in Outage.objects.order_by("-end_date", "-start_date") if not o.resolved
    ]  # silly ORM quirk
    context["outages"] = outages

    return render(request, "dashboard.html", context)


class OIDCRegisterView(OIDCAuthenticationRequestView):
    """Create a registration view that derives from the default login view.

    The only difference is the auth endpoint is slightly different; Keycloak
    exposes a /registrations path instead of /auth, which brings users to a
    register flow instead of a login flow. We currently use this to customize
    what authentication methods the user sees in login vs. register, to hide
    the legacy login in the registration flow.
    """

    def __init__(self, *args, **kwargs):
        super(OIDCRegisterView, self).__init__(*args, **kwargs)
        self.OIDC_OP_AUTH_ENDPOINT = self.get_settings("OIDC_OP_REGISTRATION_ENDPOINT")


def edge_hardware_discovery(request):
    """Hardware resource discovery page for CHI@Edge."""
    devices = {"devices": edge_api.get_devices()}
    return render(request, "edge-hw-discovery/resources.html", devices)


def force_password_login(request):
    """Redirect user to login with a parameter that forces a password login.

    This is a way to do a one-off opt-out of federated login.
    """
    params = request.GET.copy()
    params[settings.FORCE_OLD_LOGIN_EXPERIENCE_PARAM] = "1"
    return redirect(reverse("login") + f"?{urlencode(params)}")


def password_reset(request):
    """Legacy view for redirecting password reset requests back to TAS.

    When a user requests a password reset, the link in their mail from TAS
    points to Portal; we simply return them to the corresponding endpoint
    on the TACC user portal.
    """
    host = settings.TACC_USER_PORTAL_HOST
    return redirect(f"{host}/password-reset?{urlencode(request.GET)}")


def admin_or_superuser(user):
    if user:
        LOG.debug(
            "If user has allocation admin role: %s",
            user.groups.filter(name="Allocation Admin").count(),
        )
        return (
            user.groups.filter(name="Allocation Admin").count() == 1
        ) or user.is_superuser
    return False


def blog_redirect(request):
    # parse path into either list of all posts, a specific post, category
    base_blog_url = "https://blog.chameleoncloud.org"
    url = base_blog_url

    category_map = {
        "changelog": "chameleon-changelog",
        "tips": "tips-and-tricks",
        "announcements": "announcements",
        "education": "education",
        "featured": "featured",
        "user-experiments": "user-experiments",
    }

    url_obj = urlsplit(request.path)
    path_parts = url_obj.path.strip("/").split("/")
    if len(path_parts) == 3 and path_parts[1] == "category":
        category = category_map.get(path_parts[2])
        url = f"{base_blog_url}/categories/{category}" if category else base_blog_url
    elif len(path_parts) == 3 and path_parts[1] == "author":
        username = path_parts[2]
        author = User.objects.get(username=username)
        url = f"{base_blog_url}/authors/{author.get_full_name().lower().replace(' ', '-')}"
    elif len(path_parts) == 5:
        url = f"{base_blog_url}/posts/{path_parts[4]}"
    elif len(path_parts) == 2 and path_parts[1] == "feed":
        url = f"{base_blog_url}/posts/index.xml"
    return redirect(url, permanent=True)


@cache_page(60 * 5)
def featured_json(request):
    response = requests.get("https://blog.chameleoncloud.org/featured.json")
    if response.status_code != 200:
        LOG.warning(f"Failed to fetch featured posts: {response.status_code}")
        return JsonResponse([], safe=False, status=500)
    featured = response.json()
    return JsonResponse(featured, safe=False)


@login_required
def download_dataset(request, dataset_id):
    ds = Dataset.objects.get(pk=dataset_id)
    DatasetDownloadEvent.objects.create(
        downloaded_by=request.user,
        dataset=ds,
    )
    return redirect(ds.url)
