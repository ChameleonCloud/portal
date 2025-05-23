from datetime import datetime
from itertools import chain
import time

import pytz

from allocations.models import Allocation
from chameleon.models import PIEligibility
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.db.models import Max, QuerySet
from django.urls import reverse
from django.utils.html import strip_tags
from djangoRT import rtModels, rtUtil
import logging
from balance_service.utils.su_calculators import project_balances
from projects.models import Project
from projects.models import Tag
from pytas.http import TASClient
from pytas.models import Project as tas_proj
from pytas.models import User as tas_user
from util.consts import allocation, project
from util.keycloak_client import KeycloakClient


logger = logging.getLogger(__name__)

TMP_PROJECT_CHARGE_CODE_PREFIX = "TMP-"


class ProjectAllocationMapper:
    def __init__(self, request):
        self.is_from_db = self._wants_db(request)
        self.tas = TASClient()
        self.current_user = request.user.username

    def _wants_db(self, request):
        return request.session.get("is_federated", False)

    def _send_allocation_request_notification(self, charge_code, alloc):
        path = reverse("admin:allocations_allocation_change", args=[alloc.id])
        alloc_url = f"https://chameleoncloud.org{path}"
        subject = f"Pending allocation request for project {charge_code}"
        body = f"""
        Please review the pending allocation request for project {charge_code} at
        {alloc_url}
        """
        rt = rtUtil.DjangoRt()
        ticket = rtModels.Ticket(
            subject=subject,
            problem_description=body,
            requestor="us@tacc.utexas.edu",
        )
        rt.createTicket(ticket)

    def _send_allocation_decision_notification(
        self, charge_code, requestor_id, status, decision_summary, host
    ):
        UserModel = get_user_model()
        user = UserModel.objects.get(pk=requestor_id)
        subject = f"Decision of your allocation request for project {charge_code}"
        body = f"""
        <p>Dear {user.first_name} {user.last_name},</p>
        <p>Your allocation request for project {charge_code} has been {status}
        with the following message:</p>
        <p>{decision_summary}</p>
        <br/>
        <p><i>This is an automatic email, please <b>DO NOT</b> reply!
        If you have any question or issue, please submit a ticket on our
        <a href="https://{host}/user/help/">help desk</a>.
        </i></p>
        <br/>
        <p>Thanks,</p>
        <p>Chameleon Team</p>
        """
        send_mail(
            subject=subject,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            message=strip_tags(body),
            html_message=body,
        )

    def _get_user_from_portal_db(self, username):
        UserModel = get_user_model()
        try:
            portal_user = UserModel.objects.get(username=username)
            return portal_user
        except UserModel.DoesNotExist:
            logger.error("Could not find user %s in DB", username)
            return None

    def _create_ticket_for_pi_request(self, user):
        """
        This is a stop-gap solution for https://collab.tacc.utexas.edu/issues/8327.
        """
        rt = rtUtil.DjangoRt()
        subject = f"Chameleon PI Eligibility Request: {user.username}"
        problem_description = (
            "This PI Eligibility request can be reviewed at "
            "https://www.chameleoncloud.org/admin/chameleon/pieligibility/"
        )
        ticket = rtModels.Ticket(
            subject=subject,
            problem_description=problem_description,
            requestor="us@tacc.utexas.edu",
        )
        rt.createTicket(ticket)

    def _create_ticket_for_pending_allocation(
        self, requestor, problem_description, owner
    ):
        rt = rtUtil.DjangoRt()
        subject = (
            "More information required to approve your Chameleon allocation request"
        )
        ticket = rtModels.Ticket(
            subject=subject,
            problem_description="Ticket created to contact the PI for more information.",
            requestor=requestor,
            owner=owner,
        )

        ticket_id = rt.createTicket(ticket)
        rt.replyToTicket(ticket_id, text=problem_description)

        return ticket_id

    def get_all_projects(self) -> "list[dict]":
        """Get all projects, all of their allocations, for all users.

        Returns:
            List[dict]: a list of projects in the TAS representation format,
                sorted by newest allocation request date. Allocations in each
                project are sorted from newest to oldest by
                portal_to_dict_proj.
        """

        # for each project, get the most recent 'date_requested' among its allocations
        # annotate the project with 'newest_request'
        # order the projects by the 'newest_request' annotation
        # to optimize the query, ensure request includes foreign keys

        project_qs = (
            Project.objects.annotate(newest_request=Max("allocations__date_requested"))
            .select_related("tag", "pi")
            .order_by("newest_request")
            .reverse()
        )
        projects = self._with_relations(project_qs)
        return [self.portal_to_dict_proj(p) for p in projects]

    def _with_relations(self, projects, fetch_balance=True, fetch_allocations=True):
        if fetch_allocations and isinstance(projects, QuerySet):
            logger.debug("Prefetching related fields")
            projects = projects.prefetch_related(
                "allocations", "allocations__requestor", "allocations__reviewer"
            )

        by_charge_code = {p.charge_code: p for p in projects}

        logger.debug(f"Fetching relations for {len(projects)} projects")

        if fetch_allocations:
            all_active_allocations = {
                a.project.charge_code: a
                # NOTE: this makes a nested .all() call to fetch allocations.
                # If the input projects argument is not a QuerySet, this will
                # make a single SQL call for each input project!
                for a in chain(*[p.allocations.all() for p in by_charge_code.values()])
                if a.status == "active"
            }
            if fetch_balance:
                logger.debug(f"Fetching balances for {len(projects)} projects")

                # get balance for allocations
                project_ids = [
                    a.project.id
                    for a in all_active_allocations.values()
                    if a.balance_service_version == 2
                ]
                for b in project_balances(project_ids):
                    charge_code = b.get("charge_code")
                    if charge_code:
                        all_active_allocations[charge_code].su_used = b.get("total")

        return projects

    def save_allocation(self, alloc, project_charge_code, host):
        reformated_alloc = self.json_to_portal_alloc(alloc, project_charge_code)
        reformated_alloc.save()
        self._send_allocation_request_notification(
            project_charge_code, reformated_alloc
        )

    def save_project(self, proj, host=None):
        allocations = self.get_attr(proj, "allocations")
        reformated_proj = self.json_to_portal_proj(proj)
        reformated_proj.save()
        if reformated_proj.charge_code.startswith(TMP_PROJECT_CHARGE_CODE_PREFIX):
            # save project in portal
            new_proj = Project.objects.filter(charge_code=reformated_proj.charge_code)
            if len(new_proj) == 0:
                logger.error(f"Couldn't find project {reformated_proj.charge_code}")
            else:
                new_proj = new_proj[0]
                valid_charge_code = (
                    "CHI-" + str(datetime.today().year)[2:] + str(new_proj.id).zfill(4)
                )
                new_proj.charge_code = valid_charge_code
                new_proj.save()
                reformated_proj.charge_code = valid_charge_code

                # create allocation
                self.save_allocation(allocations[0], valid_charge_code, host)

                # save project in keycloak
                keycloak_client = KeycloakClient()
                keycloak_client.create_project(valid_charge_code, new_proj.pi.username)

        return self.portal_to_dict_proj(reformated_proj, fetch_allocations=False)

    def get_portal_user_id(self, username):
        portal_user = self._get_user_from_portal_db(username)
        if portal_user:
            return portal_user.id
        return None

    def get_user(self, username, to_pytas_model=False, role=None):
        portal_user = self._get_user_from_portal_db(username)
        if not portal_user:
            return None

        user = self.portal_user_to_dict(portal_user, role=role)
        # update user metadata from keycloak
        user = self.update_user_metadata_from_keycloak(user)
        return tas_user(initial=user) if to_pytas_model else user

    def lazy_add_user_to_keycloak(self):
        keycloak_client = KeycloakClient()
        # check if user exist in keycloak
        keycloak_user = keycloak_client.get_user_by_username(self.current_user)
        if keycloak_user:
            return
        user = self.get_user(self.current_user)
        portal_user = self._get_user_from_portal_db(self.current_user)
        join_date = None
        if portal_user:
            join_date = datetime.timestamp(portal_user.date_joined)

        kwargs = {
            "first_name": user["firstName"],
            "last_name": user["lastName"],
            "email": user["email"],
            "affiliation_title": user["title"],
            "affiliation_department": user["department"],
            "affiliation_institution": user["institution"],
            "country": user["country"],
            "citizenship": user["citizenship"],
            "join_date": join_date,
        }
        keycloak_client.create_user(self.current_user, **kwargs)

    @staticmethod
    def get_project_nickname(project):
        return project.nickname

    @staticmethod
    def update_project_nickname(project_id, nickname):
        project = Project.objects.get(pk=project_id)
        project.nickname = nickname
        project.save()

    @staticmethod
    def update_project_tag(project_id, project_tag_id):
        project = Project.objects.get(pk=project_id)
        project_tag = Tag.objects.get(pk=project_tag_id)
        project.tag = project_tag
        project.automatically_tagged = False
        project.save()

    @staticmethod
    def update_project_pi(project_id, project_pi_username):
        project = Project.objects.get(pk=project_id)

        # update keycloak
        keycloak_client = KeycloakClient()
        keycloak_client.set_user_project_role(
            project_pi_username, project.charge_code, "admin"
        )
        keycloak_client.set_user_project_role(
            project.pi.username, project.charge_code, "member"
        )

        # update portal
        UserModel = get_user_model()
        project.pi = UserModel.objects.get(username=project_pi_username)
        project.save()

    def update_user_profile(
        self, user, new_profile, is_request_pi_eligibililty, department_directory_link
    ):
        keycloak_client = KeycloakClient()

        if is_request_pi_eligibililty:
            pie_request = PIEligibility()
            pie_request.requestor_id = user.id
            pie_request.department_directory_link = department_directory_link
            pie_request.save()
            self._create_ticket_for_pi_request(user)

        email = new_profile.get("email")
        keycloak_client.update_user(
            user.username,
            email=email,
            affiliation_title=new_profile.get("title"),
            affiliation_department=new_profile.get("department"),
            affiliation_institution=new_profile.get("institution"),
            country=new_profile.get("country"),
            citizenship=new_profile.get("citizenship"),
            phone=new_profile.get("phone"),
        )
        # The email normally is saved during login; in this case we can
        # immediately persist the change for better UX.
        if email is not None:
            user.email = email
            user.save()

    @staticmethod
    def get_publication_project(publication):
        if publication.project_id:
            try:
                return Project.objects.get(pk=publication.project_id)
            except Project.DoesNotExist:
                logger.warning(
                    f"Couldn't find project with id {publication.project_id}"
                )
        return None

    def get_user_projects(
        self, username, alloc_status=[], fetch_balance=True, to_pytas_model=False
    ):
        # get user projects from portal
        keycloak_client = KeycloakClient()
        charge_codes = keycloak_client.get_user_projects_by_username(username)
        projects_qs = Project.objects.filter(charge_code__in=charge_codes)

        user_projects = [
            self.portal_to_dict_proj(p, alloc_status=alloc_status)
            for p in self._with_relations(projects_qs, fetch_balance=fetch_balance)
        ]

        if to_pytas_model:
            return [tas_proj(initial=p) for p in user_projects]
        else:
            return user_projects

    def get_project(self, project_id):
        """Get a project by its ID (not charge code).

        Args:
            project_id (int): the project ID.

        Returns:
            pytas.models.Project: a TAS Project representation for the project.
        """
        projects = list(self._with_relations(Project.objects.filter(pk=project_id)))
        if not projects:
            raise Project.DoesNotExist()
        project = self.portal_to_dict_proj(projects[0])
        return tas_proj(initial=project)

    def allocation_approval(self, data, host):
        # update allocation model
        alloc = Allocation.objects.get(pk=data["id"])
        data["status"] = data["status"].lower()
        data["dateReviewed"] = datetime.now(pytz.utc)
        for item in [
            "reviewerId",
            "dateReviewed",
            "start",
            "end",
            "status",
            "decisionSummary",
            "computeAllocated",
        ]:
            setattr(alloc, allocation.JSON_TO_PORTAL_MAP[item], data[item])
        alloc.save()
        logger.info("Allocation model updated: data=%s", alloc.__dict__)
        # send email to PI
        email_args = {
            "charge_code": data["project"],
            "requestor_id": data["requestorId"],
            "status": data["status"],
            "decision_summary": data["decisionSummary"],
            "host": host,
        }
        self._send_allocation_decision_notification(**email_args)

    def contact_pi_via_rt(self, data):
        rt_info = data["rt"]
        ticket_id = self._create_ticket_for_pending_allocation(
            rt_info["requestor"], rt_info["problem_description"], rt_info["owner"]
        )

        allocation = data["allocation"]
        alloc = Allocation.objects.get(pk=allocation["id"])
        setattr(alloc, "status", "waiting")
        setattr(alloc, "decision_summary", f"RT ticket created with id: {ticket_id}")
        alloc.save()

    def _parse_field_recursive(self, parent, level=0):
        result = [(parent["id"], "--- " * level + parent["name"])]
        level = level + 1
        for child in parent["children"]:
            result = result + self._parse_field_recursive(child, level)
        return result

    def get_project_tags_choices(self):
        choices = (("", "Choose One"),)
        for item in Tag.objects.filter(expose=True):
            choices += ((item.id, f"{item.name} — {item.description}"),)
        return choices

    def portal_to_dict_proj(self, proj, fetch_allocations=True, alloc_status=None):
        if alloc_status is None:
            alloc_status = []
        return Project.to_dict(
            proj, fetch_allocations=fetch_allocations, alloc_status=alloc_status
        )

    def json_to_portal_alloc(self, alloc, project_charge_code):
        reformated_alloc = {}
        for key, val in list(alloc.items()):
            if key in allocation.JSON_TO_PORTAL_MAP:
                reformated_alloc[allocation.JSON_TO_PORTAL_MAP[key]] = val

        portal_project = Project.objects.filter(charge_code=project_charge_code)
        if len(portal_project) == 0:
            logger.error("Couldn't find project {} in portal".format(alloc["project"]))
        else:
            reformated_alloc["project_id"] = portal_project[0].id
        reformated_alloc["date_requested"] = datetime.now(pytz.utc)
        reformated_alloc["status"] = "pending"

        reformated_alloc = Allocation(**reformated_alloc)

        return reformated_alloc

    def json_to_portal_proj(self, proj):
        reformated_proj = {}
        for key, val in list(proj.items()):
            if key in project.JSON_TO_PORTAL_MAP:
                reformated_proj[project.JSON_TO_PORTAL_MAP[key]] = val
        if "id" in proj:
            reformated_proj["id"] = proj["id"]
            reformated_proj["nickname"] = Project.objects.get(pk=proj["id"]).nickname
        else:
            # assign temporary charge code for new project
            dt = datetime.now()
            reformated_proj["charge_code"] = TMP_PROJECT_CHARGE_CODE_PREFIX + str(
                time.mktime(dt.timetuple()) + dt.microsecond / 1e6
            ).replace(".", "")

        reformated_proj = Project(**reformated_proj)

        return reformated_proj

    def portal_user_to_dict(self, user, role="Standard"):
        return get_user_model().as_dict(user, role=role)

    def update_user_metadata_from_keycloak(self, json_formatted_user):
        keycloak_client = KeycloakClient()
        keycloak_user = keycloak_client.get_user_by_username(
            json_formatted_user["username"]
        )

        if keycloak_user:
            attrs = keycloak_user["attributes"]
            json_formatted_user.update(
                {
                    "institution": attrs.get("affiliationInstitution", None),
                    "department": attrs.get("affiliationDepartment", None),
                    "title": attrs.get("affiliationTitle", None),
                    "country": attrs.get("country", None),
                    "phone": attrs.get("phone", None),
                    "citizenship": attrs.get("citizenship", None),
                }
            )
        return json_formatted_user

    def get_attr(self, obj, key):
        """Attempt to resolve the key either as an attribute or a dict key"""
        if isinstance(obj, dict):
            return obj.get(key)
        else:
            return getattr(obj, key, None)

    def set_attr(self, obj, key, val):
        """Attempt to resolve the key either as an attribute or a dict key"""
        if isinstance(obj, dict):
            obj[key] = val
        else:
            setattr(obj, key, val)
        return obj
