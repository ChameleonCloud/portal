import functools
import logging
import json

from django.db import transaction
from django.http import (
    HttpResponseBadRequest,
    HttpResponseForbidden,
    HttpResponseServerError,
    HttpResponse,
)
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt

from .enforcement import exceptions as ue_exceptions
from .enforcement import usage_enforcement
from .utils.openstack import keystone
from .utils import su_calculators
from . import exceptions

logger = logging.getLogger("balance_service")


# decorator for authentication
def authenticate(func):
    @functools.wraps(func)
    def auth_f(*args, **kwargs):
        request = args[0]
        try:
            keystone_api = keystone.KeystoneAPI.load_from_request(request)
            user_name = keystone_api.get_auth_username()
        except (exceptions.AuthURLException, exceptions.AuthUserException) as e:
            logger.exception(e)
            return HttpResponseForbidden()
        except Exception:
            logger.exception("Not Authorized.")
            return HttpResponseForbidden()

        logger.debug("user {} authorized".format(user_name))

        return func(keystone_api, *args, **kwargs)

    return auth_f


@require_http_methods(["GET"])
@authenticate
def batch_get_project_allocations(keystone_api, request):
    projects = request.GET["projects"]
    if not projects:
        return HttpResponseBadRequest("No projects specified")
    # Assume comma-separated
    projects = [int(pid) for pid in projects.split(",")]

    return HttpResponse(
        json.dumps({"projects": su_calculators.project_balances(projects)}),
        content_type="application/json",
    )


@require_http_methods(["GET"])
@authenticate
def get_project_allocation(keystone_api, request, project_id):
    return su_calculators.project_balances([project_id])[0]


# Usage Enforcement API


def make_enforcement_response(check):
    if isinstance(check, Exception):
        return HttpResponse(
            json.dumps({"message": check.message}),
            content_type="application/json",
            status=check.code,
        )
    return HttpResponse("", status=204)


@csrf_exempt
@require_http_methods(["POST"])
@authenticate
@transaction.atomic
def check_create(keystone_api, request):
    data = json.loads(request.body)
    enforcer = usage_enforcement.UsageEnforcer(keystone_api)

    check = None

    try:
        enforcer.check_usage_against_allocation(data)
    except ue_exceptions.BillingError as e:
        logger.exception(e)
        check = e
    except Exception as e:
        logger.exception(e)
        return HttpResponseServerError("Unexpected Error")

    return make_enforcement_response(check)


@csrf_exempt
@require_http_methods(["POST"])
@authenticate
@transaction.atomic
def check_update(keystone_api, request):
    data = json.loads(request.body)
    enforcer = usage_enforcement.UsageEnforcer(keystone_api)

    check = None

    try:
        enforcer.check_usage_against_allocation_update(data)
    except ue_exceptions.BillingError as e:
        logger.exception(e)
        check = e
    except Exception as e:
        logger.exception(e)
        return HttpResponseServerError("Unexpected Error")

    return make_enforcement_response(check)


@csrf_exempt
@require_http_methods(["POST"])
@authenticate
@transaction.atomic
def on_end(keystone_api, request):
    data = json.loads(request.body)
    enforcer = usage_enforcement.UsageEnforcer(keystone_api)

    try:
        enforcer.stop_charging(data)
    except ue_exceptions.BillingError as e:
        logger.exception(e)
        return make_enforcement_response(e)
    except Exception as e:
        logger.exception(e)
        return HttpResponseServerError("Unexpected Error")

    return make_enforcement_response(None)
