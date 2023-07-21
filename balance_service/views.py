import functools
import logging
import json

from django.db import transaction
from django.http import (
    HttpResponseBadRequest,
    HttpResponseForbidden,
    HttpResponse,
    JsonResponse,
    HttpResponseServerError,
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
        except Exception as ex:
            logger.exception(ex)
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
    try:
        balance = su_calculators.project_balances([project_id])[0]
    except IndexError:
        # if project ID is not found
        balance = {}
    except Exception:
        return HttpResponseServerError("Unexpected Error")
    return JsonResponse(balance)


# Usage Enforcement API


def make_enforcement_response(check):
    if isinstance(check, Exception):
        return HttpResponse(
            json.dumps({"message": check.message}),
            content_type="application/json",
            status=check.code,
        )
    return HttpResponse("", status=204)


def _unexpected_error():
    return ue_exceptions.EnforcementException(message="Unexpected Error", code=500)


def _parse_external_balance_service_request(req):
    check = None
    if req.status_code == 403:
        message = req.json().get("message")
        logger.exception(message)
        check = ue_exceptions.BillingError(message=message)
    elif req.status_code != 204:
        check = _unexpected_error()

    return check


def _process(enforcer, request, fun_v2):
    data = json.loads(request.body)

    check = None
    balance_service_version = int(enforcer.get_balance_service_version(data))
    if balance_service_version == 1:
        raise ValueError("Balance service version 1 is not supported")

    # balance service v2
    try:
        fun_v2(data)
    except ue_exceptions.BillingError as e:
        logger.exception(e)
        check = e
    except Exception as e:
        logger.exception(e)
        check = _unexpected_error()

    return make_enforcement_response(check)


@csrf_exempt
@require_http_methods(["POST"])
@authenticate
@transaction.atomic
def check_create(keystone_api, request):
    enforcer = usage_enforcement.UsageEnforcer(keystone_api)
    return _process(
        enforcer,
        request,
        enforcer.check_usage_against_allocation,
    )


@csrf_exempt
@require_http_methods(["POST"])
@authenticate
@transaction.atomic
def check_update(keystone_api, request):
    enforcer = usage_enforcement.UsageEnforcer(keystone_api)
    return _process(
        enforcer,
        request,
        enforcer.check_usage_against_allocation_update,
    )


@csrf_exempt
@require_http_methods(["POST"])
@authenticate
@transaction.atomic
def on_end(keystone_api, request):
    enforcer = usage_enforcement.UsageEnforcer(keystone_api)
    return _process(
        enforcer,
        request,
        enforcer.stop_charging,
    )
