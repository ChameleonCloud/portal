from celery import shared_task as task
from celery.utils.log import get_task_logger
from django.contrib.auth.models import User
from django.db.models import Q
from chameleon.models import Institution, InstitutionAlias, UserInstitution
from util.keycloak_client import KeycloakClient
from django.http import JsonResponse
from celery.result import AsyncResult
from chameleon.celery import app as celery_app

from django.urls import path

LOG = get_task_logger(__name__)


@task()
def update_institutions(interactive=True):
    """Intended to be run manually via the CLI on occasion. Edited in tandem
    with the institution admin site.
    """
    for user in User.objects.filter(institutions__isnull=True):
        keycloak_client = KeycloakClient()
        kc_user = keycloak_client.get_user_from_portal_user(user)
        if not kc_user:
            # Legacy user, no login since fed. identity
            continue
        institution = kc_user.get("attributes", {}).get("affiliationInstitution")
        if institution:
            inst_obj = Institution.objects.filter(
                Q(name__iexact=institution) | Q(aliases__alias__iexact=institution)
            ).first()

            if not inst_obj:
                # Skip this iteration if not interactive
                if not interactive:
                    continue

                # Ask for institution from alias
                inst_input = input(f"Institution for '{institution}'?").strip()
                if not len(inst_input):
                    # Check if the DB was manually updated with this new institution
                    inst_obj = Institution.objects.filter(
                        Q(name__iexact=institution)
                        | Q(aliases__alias__iexact=institution)
                    ).first()
                    if not inst_obj:
                        print(user.username, "skipping: at", institution)
                        continue
                else:
                    # Otherwise, insert new alias
                    inst_obj = Institution.objects.filter(
                        Q(name__iexact=institution)
                        | Q(aliases__alias__iexact=institution)
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


@task()
def run_normalize_institutions():
    """Nightly task: match unclassified users to canonical Institution records."""
    from django.core.management import call_command
    call_command("normalize_institutions")


class AdminTaskManager:
    """This is used to add a "start_task" and "check_task" view to an admin page.
    This is useful for one-off tasks that an admin should initiate.
    """

    def __init__(self, admin_site, name, task_function):
        self.name = name
        self._id = f"{name}_task_id"
        self.task_function = task_function
        self.admin_site = admin_site
        self.start_path_name = f"start_{self.name}"
        self.check_path_name = f"check_{self.name}"
        self.terminate_path_name = f"terminate_{self.name}"

    def get_urls(self):
        return [
            path(
                f"start/{self.name}",
                self.admin_site.admin_view(self.start_task),
                name=self.start_path_name,
            ),
            path(
                f"check/{self.name}",
                self.admin_site.admin_view(self.check_task),
                name=self.check_path_name,
            ),
            path(
                f"terminate/{self.name}",
                self.admin_site.admin_view(self.terminate_task),
                name=self.terminate_path_name,
            ),
        ]

    def start_task(self, request):
        """Start task, if the user has doesn't have a running task,
        otherwise return the task id.
        """
        task_id = request.session.get(self._id)
        if task_id:
            result = AsyncResult(task_id, app=celery_app)
            if result.state in ["PROGRESS", "PENDING"]:
                return JsonResponse({"id": task_id})
            else:
                del request.session[self._id]
        task = self.task_function.delay()
        request.session[self._id] = task.id
        return JsonResponse({"id": task.id})

    def terminate_task(self, request):
        task_id = request.session.get(self._id)
        AsyncResult(task_id, app=celery_app).revoke(terminate=True)
        del request.session[self._id]
        return JsonResponse({"status": "TERMINATED"})

    def check_task(self, request):
        """Get the latest status from the user's task."""
        task_id = request.session.get(self._id)
        if task_id:
            result = AsyncResult(task_id, app=celery_app)
            if result.state == "PROGRESS":
                return JsonResponse({"status": "PROGRESS", **result.info})
            elif result.state == "FAILURE":
                del request.session[self._id]
                return JsonResponse(
                    {
                        "status": "FAILURE",
                        "result": f"{type(result.result)} {result.result}",
                    }
                )
            elif result.state == "SUCCESS":
                del request.session[self._id]
            return JsonResponse({"status": result.state, "result": result.result})
        return JsonResponse({"status": None})
