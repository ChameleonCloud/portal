from django.shortcuts import render
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core import validators
from django.core.exceptions import ValidationError
from django.http import HttpResponse, JsonResponse, HttpResponseForbidden
from django.contrib.auth.decorators import login_required, user_passes_test
from projects.models import Project
from util.keycloak_client import KeycloakClient
from util.project_allocation_mapper import ProjectAllocationMapper

import logging
import json

logger = logging.getLogger(__name__)


def allocation_admin_or_superuser(user):
    if user:
        logger.debug(
            "If user has allocation admin role: %s",
            user.groups.filter(name="Allocation Admin").count(),
        )
        return (
            user.groups.filter(name="Allocation Admin").count() == 1
        ) or user.is_superuser
    return False


@login_required
@user_passes_test(allocation_admin_or_superuser, login_url="/admin/allocations/denied/")
def index(request):
    user = request.user
    logger.debug("Serving allocation approval view to: %s", user.username)
    context = {}
    return render(request, "allocations/index.html", context)


def denied(request):
    user = request.user
    if user:
        logger.debug("Denying allocation approval view to: %s", user.username)
    context = {}
    return render(request, "allocations/denied.html", context)


def get_all_alloc(request):
    """Get all allocations, grouped by project.

    Args:
        request: the request that is passed in.

    Raises:
        Exception: when loading projects fails.

    Returns:
        json: dumps all data as serialized json.
    """
    try:
        keycloak_client = KeycloakClient()
        user_attributes = keycloak_client.get_all_users_attributes()
        mapper = ProjectAllocationMapper(request)
        resp = mapper.get_all_projects()
        logger.debug("Total projects: %s", len(resp))
        for r in resp:
            pi_attributes = user_attributes.get(r["pi"]["username"], {})
            if pi_attributes:
                institution = pi_attributes.get("affiliationInstitution", [])
                country = pi_attributes.get("country", [])
                r["pi"]["institution"] = next(iter(institution), None)
                r["pi"]["country"] = next(iter(country), None)
    except Exception as e:
        logger.exception("Error loading chameleon projects")
        messages.error(request, e)
        raise
    return json.dumps(resp)


@login_required
@user_passes_test(allocation_admin_or_superuser, login_url="/admin/allocations/denied/")
def view(request):
    """Return http response of get_all_alloc. Matches Template."""
    return HttpResponse(get_all_alloc(request), content_type="application/json")


def view_project(request, charge_code):
    provided_token = request.GET.get("token") if request.GET.get("token") else None
    stored_token = getattr(settings, "PROJECT_ALLOCATION_DETAILS_TOKEN", None)
    if not provided_token or not stored_token or provided_token != stored_token:
        logger.error("Project allocation api Access Token validation failed")
        return HttpResponseForbidden()

    try:
        project = Project.objects.get(charge_code=charge_code)
    except Project.DoesNotExist:
        return JsonResponse({"error": "Project not found"}, status=404)

    is_waiting = project.allocations.filter(
        status__in=["pending", "approved", "waiting"]
    ).exists()
    is_active = project.allocations.filter(status="active").exists()
    furthest_allocation = project.allocations.order_by("-expiration_date").first()
    data = {
        "charge_code": project.charge_code,
        "nickname": project.nickname,
        "pi": project.pi.email,
        "status": furthest_allocation.status,
        "expiration_date": furthest_allocation.expiration_date,
        "is_active": is_active,
        "has_pending_allocation": is_waiting,
    }
    return JsonResponse(data)


@login_required
@user_passes_test(allocation_admin_or_superuser, login_url="/admin/allocations/denied/")
def return_json(request):
    """Return http response of get_all_alloc. Does not match Template."""
    return HttpResponse(get_all_alloc(request), content_type="application/json")


@login_required
@user_passes_test(allocation_admin_or_superuser, login_url="/admin/allocations/denied/")
def user_select(request):
    user = request.user
    logger.debug("Serving user projects view to: %s", user.username)
    context = {}
    return render(request, "allocations/user-projects.html", context)


@login_required
@user_passes_test(allocation_admin_or_superuser, login_url="/admin/allocations/denied/")
def user_projects(request, username):
    logger.info(
        "User projects requested by admin: %s for user %s", request.user, username
    )
    resp = {"status": "error", "msg": "", "result": []}
    if username:
        try:
            mapper = ProjectAllocationMapper(request)
            user_projects = mapper.get_user_projects(username)
            resp["status"] = "success"
            resp["result"] = user_projects
            logger.info(
                "Total chameleon projects for user %s: %s", username, len(user_projects)
            )
        except Exception as e:
            logger.debug(
                "Error loading projects for user: %s with error %s", username, e
            )
            resp["msg"] = "Error loading projects for user: %s" % username
    return HttpResponse(json.dumps(resp), content_type="application/json")


@login_required
@user_passes_test(allocation_admin_or_superuser, login_url="/admin/allocations/denied/")
def approval(request):
    resp = {}
    errors = {}
    status = ""
    if request.POST:
        mapper = ProjectAllocationMapper(request)
        data = json.loads(request.body)
        data["reviewer"] = request.user.username
        data["reviewerId"] = mapper.get_portal_user_id(request.user.username)
        logger.info("Allocation approval requested by admin: %s", request.user)
        logger.info("Allocation approval request data: %s", json.dumps(data))
        validate_datestring = validators.RegexValidator(r"^\d{4}-\d{2}-\d{2}$")
        if not data["decisionSummary"]:
            errors["decisionSummary"] = "Decision Summary is required."

        if not data["status"]:
            errors["status"] = "Status is required. "
        elif not data["status"] in [
            "Pending",
            "pending",
            "Approved",
            "approved",
            "Rejected",
            "rejected",
            "Waiting",
            "waiting",
        ]:
            errors["status"] = (
                'Status must be "Pending", "pending", "Approved", "approved", "Rejected", "rejected"'
            )
        else:
            if data["start"]:
                try:
                    validate_datestring(data["start"])
                except ValidationError:
                    errors["start"] = (
                        'Start date must be a valid date string e.g. "2015-05-20" .'
                    )
            elif data["status"].lower() == "approved":
                errors["start"] = "Start date is required."

            if data["end"]:
                try:
                    validate_datestring(data["end"])
                except ValidationError:
                    errors["end"] = (
                        'Start date must be a valid date string e.g. "2015-05-20" .'
                    )
            elif data["status"].lower() == "approved":
                errors["end"] = "Start date is required."

        if data["computeAllocated"]:
            try:
                data["computeAllocated"] = int(data["computeAllocated"])
            except ValueError:
                errors["computeAllocated"] = "Compute Allocated must be a number."

        if not data["project"]:
            errors["project"] = "Project charge code is required."

        if data["reviewerId"]:
            try:
                data["reviewerId"] = int(data["reviewerId"])
            except ValueError:
                errors["reviewerId"] = "Reviewer id must be number."
        else:
            errors["reviewerId"] = "Reviewer id is required."

        if data["dateReviewed"]:
            try:
                validate_datestring(data["dateReviewed"])
            except ValidationError:
                errors["dateReviewed"] = (
                    'Reviewed date must be a valid date string e.g. "2015-05-20" .'
                )
        else:
            errors["dateReviewed"] = "Reviewed date is required."
        if len(errors) == 0:
            # source
            data["source"] = "Chameleon"

            try:
                mapper.allocation_approval(data, request.get_host())
                status = "success"
            except Exception as e:
                logger.exception("Error processing allocation approval.")
                status = "error"
                errors["message"] = (
                    "An unexpected error occurred. If this problem persists please create a help ticket."
                )

        else:
            logger.info("Request data failed validation. %s", list(errors.values()))
            status = "error"

    else:
        status = "error"
        errors["message"] = "Only POST method allowed."
    resp["status"] = status
    resp["errors"] = errors
    return HttpResponse(json.dumps(resp), content_type="application/json")


@login_required
@user_passes_test(allocation_admin_or_superuser, login_url="/admin/allocations/denied/")
def contact(request):
    resp = {}
    errors = {}
    status = ""
    if request.POST:
        mapper = ProjectAllocationMapper(request)
        data = json.loads(request.body)
        data["rt"]["owner"] = request.user.username

        if data["allocation"]["status"] not in ["Pending", "pending"]:
            errors["allocation"] = "Contacting PI when allocation is pending."

        if len(errors) == 0:
            try:
                mapper.contact_pi_via_rt(data)
                status = "success"
            except Exception:
                logger.exception("Error contacting PI.")
                status = "error"
                errors["message"] = (
                    "An unexpected error occurred. If this problem persists please create a help ticket."
                )

        else:
            logger.info("Request data failed validation. %s", list(errors.values()))
            status = "error"

    else:
        status = "error"
        errors["message"] = "Only POST method allowed."
    resp["status"] = status
    resp["errors"] = errors
    return HttpResponse(json.dumps(resp), content_type="application/json")


def allocations_template(request, resource):
    logger.debug("Template requested: %s.html", resource)
    template_url = "allocations/%s.html" % resource
    return render(request, template_url)
