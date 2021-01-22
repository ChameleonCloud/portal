import json
import logging
from urllib.parse import urlencode
from uuid import uuid4

from celery.result import AsyncResult
from django.conf import settings
from django.core.urlresolvers import reverse
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from djangoRT import rtUtil
from mozilla_django_oidc.views import OIDCAuthenticationRequestView

from chameleon.celery import app as celery_app
from chameleon.keystone_auth import (
    admin_ks_client,
    get_user,
    has_valid_token,
    WHITELISTED_PROJECTS,
)
from user_news.models import Outage
from webinar_registration.models import Webinar
from util.project_allocation_mapper import ProjectAllocationMapper
from webinar_registration.models import Webinar
from .tasks import MigrationError, migrate_project, migrate_user

LOG = logging.getLogger(__name__)


@login_required
def dashboard(request):
    context = {}
    # active projects...
    mapper = ProjectAllocationMapper(request)
    active_projects = mapper.get_user_projects(
        request.user.username,
        alloc_status=["Active", "Approved", "Pending"],
        to_pytas_model=True,
    )
    context["active_projects"] = active_projects

    context["show_migration_info"] = request.session.get("has_legacy_account", False)

    # open tickets...
    rt = rtUtil.DjangoRt()
    context["open_tickets"] = rt.getUserTickets(request.user.email)

    # ongoing outages...
    outages = [
        o for o in Outage.objects.order_by("-end_date", "-start_date") if not o.resolved
    ]  # silly ORM quirk
    context["outages"] = outages

    webinars = Webinar.objects.filter(end_date__gte=timezone.now())
    context["webinars"] = webinars

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


@login_required
def migrate(request):
    token_region = "KVM@TACC"
    if request.GET.get("force") or has_valid_token(request, region=token_region):
        return render(request, "federation/migrate.html")
    else:
        params = request.GET.copy()
        params["next"] = reverse("federation_migrate_account")
        params["region"] = token_region
        return redirect(
            reverse("federation_confirm_legacy_credentials") + f"?{urlencode(params)}"
        )


@require_http_methods(["GET", "POST"])
def api_migration_job(request):
    if request.method == "POST":
        try:
            body = json.loads(request.body)
            migration_type = body.get("migration_type")
            charge_code = body.get("charge_code")
        except:
            return JsonResponse({"error": "malformed request"}, status=400)
        if migration_type not in ["user", "project"]:
            return JsonResponse({"error": "invalid migration type"}, status=400)

        task_id = str(uuid4())

        if migration_type == "project":
            if not charge_code:
                return JsonResponse({"error": "missing charge_code"}, status=400)
            migrate_project.apply_async(
                kwargs={
                    "username": request.user.username,
                    "access_token": request.session.get("oidc_access_token"),
                    "charge_code": charge_code,
                },
                task_id=task_id,
            )
        elif migration_type == "user":
            migrate_user.apply_async(
                kwargs={
                    "username": request.user.username,
                    "access_token": request.session.get("oidc_access_token"),
                },
                task_id=task_id,
            )

        return JsonResponse({"task_id": task_id})
    else:
        task_id = request.GET.get("task_id")
        if not task_id:
            return JsonResponse({"error": "missing task_id"}, status=400)
        task_result = AsyncResult(task_id, app=celery_app)
        if isinstance(task_result.info, MigrationError):
            details = {
                "messages": task_result.info.messages + ["Failed to finish migration"],
            }
        else:
            details = task_result.info
        return JsonResponse({"state": task_result.state, **details})


@require_http_methods(["GET"])
def api_migration_state(request):
    # The user may have different projects across different sites, if they only
    # used a project on a particular site, but not others.
    all_legacy_projects = {}
    legacy_user = None
    for region in list(settings.OPENSTACK_AUTH_REGIONS.keys()):
        keystone = admin_ks_client(region=region)
        ks_legacy_user = get_user(keystone, request.user.username)
        legacy_user = {
            "name": ks_legacy_user.name,
            "migrated_at": getattr(ks_legacy_user, "migrated_at", None),
        }
        all_legacy_projects.update(
            {
                ks_p.charge_code: {
                    "name": ks_p.name,
                    "charge_code": ks_p.charge_code,
                    "migrated_at": getattr(ks_p, "migrated_at", None),
                    "migrated_by": getattr(ks_p, "migrated_by", None),
                }
                for ks_p in keystone.projects.list(
                    user=ks_legacy_user, domain="default"
                )
                if ks_p.charge_code not in all_legacy_projects
                and ks_p.name not in WHITELISTED_PROJECTS
            }
        )
    return JsonResponse(
        {"user": legacy_user, "projects": list(all_legacy_projects.values())}
    )
