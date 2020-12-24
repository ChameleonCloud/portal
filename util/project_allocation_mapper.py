from pytas.models import Project as tas_proj
from pytas.models import User as tas_user
from pytas.http import TASClient
from allocations.models import Allocation as portal_alloc
from allocations.allocations_api import BalanceServiceClient
from projects.models import Project as portal_proj
from projects.models import ProjectExtras, FieldHierarchy
from chameleon.models import PIEligibility
from datetime import datetime
import logging
import pytz
import time
from django.db.models import Max
from django.conf import settings
from django.core.mail import send_mail
from django.utils.html import strip_tags
from django.contrib.auth import get_user_model
from djangoRT import rtUtil, rtModels
from util.consts import allocation, project
from util.keycloak_client import KeycloakClient

logger = logging.getLogger(__name__)

TMP_PROJECT_CHARGE_CODE_PREFIX = 'TMP-'

class ProjectAllocationMapper:
    def __init__(self, request):
        self.is_from_db = self._wants_db(request)
        self.tas = TASClient()
        self.current_user = request.user.username

    def _wants_db(self, request):
        return request.session.get('is_federated', False)

    def _send_allocation_request_notification(self, charge_code, host):
        subject = 'Pending allocation request for project {}'.format(charge_code)
        body = '''
                <p>Please review the pending allocation request for project {project_charge_code}
                at <a href='https://{host}/admin/allocations/' target='_blank'>admin page</a></p>
                '''.format(project_charge_code = charge_code, host = host)
        send_mail(subject, strip_tags(body), settings.DEFAULT_FROM_EMAIL, [settings.PENDING_ALLOCATION_NOTIFICATION_EMAIL], html_message=body)

    def _send_allocation_decision_notification(self, charge_code, requestor_id, status, decision_summary, host):
        UserModel = get_user_model()
        user = UserModel.objects.get(pk=requestor_id)
        subject = 'Decision of your allocation request for project {}'.format(charge_code)
        body = '''
                <p>Dear {first} {last},</p>
                <p>Your allocation request for project {project_charge_code} has been {status},
                due to the following reason:</p>
                <p>{decision_summary}</p>
                <br/>
                <p><i>This is an automatic email, please <b>DO NOT</b> reply!
                If you have any question or issue, please submit a ticket on our
                <a href='https://{host}/user/help/' target='_blank'>help desk</a>.
                </i></p>
                <br/>
                <p>Thanks,</p>
                <p>Chameleon Team</p>
                '''.format(first = user.first_name,
                           last = user.last_name,
                           project_charge_code = charge_code,
                           status = status,
                           decision_summary = decision_summary,
                           host = host)
        send_mail(subject, strip_tags(body), settings.DEFAULT_FROM_EMAIL, [user.email], html_message=body)

    def _get_project_allocations(self, project, fetch_balance=True):
        balance_service = BalanceServiceClient()
        reformated_allocations = []
        for alloc in project.allocations.select_related('project', 'requestor', 'reviewer').all():
            if fetch_balance and alloc.status == 'active':
                balance = balance_service.call(project.charge_code)
                if balance:
                    su_used = 0.0
                    # Total used = used in the past + "pending" (encumbered)
                    # for leases that have not yet terminated but are accruing
                    # charges.
                    for key in ['used', 'encumbered']:
                        try:
                            su_used += float(balance.get(key))
                        except (TypeError, ValueError):
                            logger.error((
                                'Can not find {} balance for project {}'
                                .format(key, project.charge_code)))
                    alloc.su_used = su_used
                else:
                    logger.warning('Couldn\'t get balance. Balance service might be down.')
            reformated_allocations.append(self.portal_to_tas_alloc_obj(alloc))
        return sorted(reformated_allocations, reverse=True, key=self.normalize_allocation_date)

    def _get_user_from_portal_db(self, username):
        UserModel = get_user_model()
        try:
            portal_user = UserModel.objects.get(username=username)
            return portal_user
        except UserModel.DoesNotExist:
            logger.error('Could not find user %s in DB', username)
            return None

    def _create_ticket_for_pi_request(self, user):
        """
        This is a stop-gap solution for https://collab.tacc.utexas.edu/issues/8327.
        """
        rt = rtUtil.DjangoRt()
        subject = "Chameleon PI Eligibility Request: %s" % user['username']
        if self.is_from_db:
            problem_description = "This PI Eligibility request can be reviewed at " +\
                "https://www.chameleoncloud.org/admin/chameleon/pieligibility/"
        else:
            problem_description = ""
        ticket = rtModels.Ticket(subject = subject,
                                 problem_description = problem_description,
                                 requestor = "us@tacc.utexas.edu")
        rt.createTicket(ticket)

    '''
    get all projects
    returns list of tas_proj_obj, sorted by most recent allocation
    allocations in each object are sorted newest to oldest
    
    '''
    def get_all_projects(self):
        #each project has many allocations; each allocation has a 'date_requested'
        #for each project, get the most recent date among its allocations, then annotate with 'newest_request'
        #sort list of projects by 'newest_request'
        sorted_projects = portal_proj.objects.annotate(newest_request=Max('allocations__date_requested')).order_by('newest_request').reverse().select_related('pi')     
        #DB hit when we create iterator
        return list(self.portal_to_tas_proj_obj(proj, fetch_balance=False) for proj in sorted_projects)

    
    '''
    Return datetime object from allocation dateRequested field for use in sorting
    '''
    def normalize_allocation_date(self, alloc):
            try:
                return datetime.strptime(alloc['dateRequested'], '%Y-%m-%dT%H:%M:%SZ')
            except:
                # if we don't have allocations or allocation requests, go to the bottom of the list
                return datetime.min

    '''
    Sort by most recent allocation request
    '''
    def sort_by_allocation_request_date(self, proj):
        latest_req_date = max([ self.normalize_allocation_date(a)
            for a in (proj.get('allocations') if proj.get('allocations') else [{"dateRequested":""}])
        ])
        return latest_req_date

    def save_allocation(self, alloc, project_charge_code, host):
        reformated_alloc = self.tas_to_portal_alloc_obj(alloc, project_charge_code)
        reformated_alloc.save()
        self._send_allocation_request_notification(project_charge_code, host)

    def save_project(self, proj, host = None):
        allocations = self.get_attr(proj, 'allocations')
        reformated_proj = self.tas_to_portal_proj_obj(proj)
        reformated_proj.save()
        if reformated_proj.charge_code.startswith(TMP_PROJECT_CHARGE_CODE_PREFIX):
            # save project in portal
            new_proj = portal_proj.objects.filter(charge_code=reformated_proj.charge_code)
            if len(new_proj) == 0:
                logger.error('Couldn\'t find project {} in portal'.format(reformated_proj.charge_code))
            else:
                new_proj = new_proj[0]
                valid_charge_code = 'CHI-' + str(datetime.today().year)[2:] + str(new_proj.id).zfill(4)
                new_proj.charge_code = valid_charge_code
                new_proj.save()
                reformated_proj.charge_code = valid_charge_code

                # create allocation
                self.save_allocation(allocations[0], valid_charge_code, host)

                # save project in keycloak
                keycloak_client = KeycloakClient()
                keycloak_client.create_project(valid_charge_code, new_proj.pi.username)

        return self.portal_to_tas_proj_obj(reformated_proj, fetch_allocations=False)

    def get_portal_user_id(self, username):
        portal_user = self._get_user_from_portal_db(username)
        if portal_user:
            return portal_user.id
        return None

    def get_user(self, username, to_pytas_model=False, role=None):
        portal_user = self._get_user_from_portal_db(username)
        if not portal_user:
            return None

        user = self.portal_user_to_tas_obj(portal_user, role=role)
        # update user metadata from keycloak
        user = self.update_user_metadata_from_keycloak(user)
        return tas_user(initial=user) if to_pytas_model else user

    def lazy_add_user_to_keycloak(self):
        keycloak_client = KeycloakClient()
        # check if user exist in keycloak
        keycloak_user = keycloak_client.get_keycloak_user_by_username(self.current_user)
        if keycloak_user:
            return
        user = self.get_user(self.current_user)
        portal_user = self._get_user_from_portal_db(self.current_user)
        join_date = None
        if portal_user:
            join_date=datetime.timestamp(portal_user.date_joined)

        kwargs = {'first_name': user['firstName'],
                  'last_name': user['lastName'],
                  'email': user['email'],
                  'affiliation_title': user['title'],
                  'affiliation_department': user['department'],
                  'affiliation_institution':user['institution'],
                  'country': user['country'],
                  'citizenship': user['citizenship'],
                  'join_date': join_date
                  }
        keycloak_client.create_user(self.current_user, **kwargs)

    @staticmethod
    def get_project_nickname(project):
        nickname = None
        if project.nickname:
            nickname = project.nickname
        else:
            try:
                project = portal_proj.objects.get(pk=project.id)
                nickname = project.nickname
            except portal_proj.DoesNotExist:
                project_extras = ProjectExtras.objects.filter(tas_project_id=project.id)
                if project_extras:
                    nickname = project_extras[0].nickname
        return nickname

    @staticmethod
    def update_project_nickname(project_id, project_charge_code, nickname):
        try:
            project = portal_proj.objects.get(pk=project_id)
            project.nickname = nickname
            project.save()
        except portal_proj.DoesNotExist:
            pextras, created = ProjectExtras.objects.get_or_create(tas_project_id=project_id)
            pextras.charge_code = project_charge_code
            pextras.nickname = nickname
            pextras.save()

    def update_user_profile(self, user, new_profile, is_request_pi_eligibililty):
        if is_request_pi_eligibililty:
            pie_request = PIEligibility()
            pie_request.requestor_id = user['id']
            pie_request.save()
            self._create_ticket_for_pi_request(user)

        keycloak_client = KeycloakClient()
        keycloak_client.update_user(user['username'],
                                    affiliation_title=new_profile.get('title'),
                                    affiliation_department=new_profile.get('department'),
                                    affiliation_institution=new_profile.get('institution'),
                                    country=new_profile.get('country'),
                                    citizenship=new_profile.get('citizenship'),
                                    phone=new_profile.get('phone'))

    @staticmethod
    def get_project_nickname_and_charge_code_for_publication(publication):
        nickname = None
        charge_code = None
        if publication.project_id:
            try:
                project = portal_proj.objects.get(pk=publication.project_id)
                nickname = project.nickname
                charge_code = project.charge_code
            except portal_proj.DoesNotExist:
                logger.warning('Couldn\'t find project with id {} in portal'.format(publication.project_id))
        elif publication.tas_project_id:
            pextras = ProjectExtras.objects.filter(tas_project_id=publication.tas_project_id)
            if pextras and pextras.count() > 0:
                nickname = pextras[0].nickname
            charge_code = publication.tas_project_id

        return nickname, charge_code

    def get_user_projects(self, username, alloc_status=[], fetch_balance=True, to_pytas_model=False):
        user_projects = {}
        # get user projects from portal
        keycloak_client = KeycloakClient()
        for charge_code in keycloak_client.get_user_projects_by_username(username):
            project = portal_proj.objects.filter(charge_code=charge_code)
            if len(project) > 0:
                project = self.portal_to_tas_proj_obj(project[0], fetch_balance=fetch_balance)
                user_projects[charge_code] = project

        if to_pytas_model:
            return [tas_proj(initial=p) for p in list(user_projects.values())]
        else:
            return list(user_projects.values())

    def get_project_members(self, tas_project):
        users = []
        # try get members from keycloak
        keycloak_client = KeycloakClient()
        pi_username = tas_project.pi.username
        for username in keycloak_client.get_project_members_by_charge_code(tas_project.chargeCode):
            if username == pi_username:
                role = 'PI'
            else:
                role = 'Standard'
            user = self.get_user(username, to_pytas_model=True, role=role)
            if user:
                users.append(user)
        return users

    def get_project(self, project_id):
        """Get a project by its ID (not charge code).

        Args:
            project_id (int): the project ID.

        Returns:
            pytas.models.Project: a TAS Project representation for the project.
        """
        project = portal_proj.objects.get(pk=project_id)
        project = self.portal_to_tas_proj_obj(project)
        return tas_proj(initial=project)

    def allocation_approval(self, data, host):
        # update allocation model
        alloc = portal_alloc.objects.get(pk=data['id'])
        data['status'] = data['status'].lower()
        data['dateReviewed'] = datetime.now(pytz.utc)
        for item in ['reviewerId', 'dateReviewed', 'start', 'end', 'status', 'decisionSummary', 'computeAllocated']:
            setattr(alloc, allocation.TAS_TO_PORTAL_MAP[item], data[item])
        alloc.save()
        logger.info('Allocation model updated: data=%s', alloc.__dict__)
        # send email to PI
        email_args = {'charge_code': data['project'],
                      'requestor_id': data['requestorId'],
                      'status': data['status'],
                      'decision_summary': data['decisionSummary'],
                      'host': host}
        self._send_allocation_decision_notification(**email_args)

    def _update_user_membership(self, tas_project, username, action=None):
        if action not in ['add', 'delete']:
            raise ValueError('Invalid membership action {}'.format(action))

        charge_code = self.get_attr(tas_project, 'chargeCode')
        keycloak_client = KeycloakClient()
        keycloak_client.update_membership(charge_code, username, action)

    def add_user_to_project(self, tas_project, username):
        return self._update_user_membership(tas_project, username, action='add')

    def remove_user_from_project(self, tas_project, username):
        return self._update_user_membership(tas_project, username, action='delete')

    def _parse_field_recursive(self, parent, level = 0):
        result = [(parent['id'], '--- ' * level + parent['name'])]
        level = level + 1
        for child in parent['children']:
            result = result + self._parse_field_recursive(child, level)
        return result

    def _portal_field_hierarchy_to_tas_format(self, parent, parent_children_map):
        parent_d = {'id': parent[0], 'name': parent[1], 'children': []}
        if parent in parent_children_map:
            for child in parent_children_map[parent]:
                child = self._portal_field_hierarchy_to_tas_format(child, parent_children_map)
                parent_d['children'].append(child)
        return parent_d

    def get_fields_choices(self):
        choices = (('', 'Choose One'),)
        fields = []
        if self.is_from_db:
            field_hierarchy = {}
            for item in FieldHierarchy.objects.all():
                key = (item.parent.id, item.parent.name)
                if key not in field_hierarchy:
                    field_hierarchy[key] = []
                field_hierarchy[key].append((item.child.id, item.child.name))
            for f in set(field_hierarchy.keys()) - set([item for sublist in list(field_hierarchy.values()) for item in sublist]):
                fields.append(self._portal_field_hierarchy_to_tas_format(f, field_hierarchy))
        else:
            fields = self.tas.fields()
        field_list = []
        for f in fields:
            field_list = field_list + self._parse_field_recursive(f)
        for item in field_list:
            choices = choices + (item,)

        return choices

    def portal_to_tas_alloc_obj(self, alloc):
        reformated_alloc = {'computeUsed': alloc.su_used,
                            'computeAllocated': alloc.su_allocated,
                            'computeRequested': alloc.su_requested,
                            'dateRequested': alloc.date_requested.strftime(allocation.TAS_DATE_FORMAT) if alloc.date_requested else None,
                            'dateReviewed': alloc.date_reviewed.strftime(allocation.TAS_DATE_FORMAT) if alloc.date_reviewed else None,
                            'decisionSummary': alloc.decision_summary,
                            'end': alloc.expiration_date.strftime(allocation.TAS_DATE_FORMAT) if alloc.expiration_date else None,
                            'id': alloc.id,
                            'justification': alloc.justification,
                            'memoryUsed': 0,
                            'memoryAllocated': 0,
                            'memoryRequested': 0,
                            'project': alloc.project.charge_code,
                            'projectId': -1,
                            'requestor': alloc.requestor.username if alloc.requestor else None,
                            'requestorId': alloc.requestor_id,
                            'resource': 'Chameleon',
                            'resourceId': 0,
                            'reviewer': alloc.reviewer.username if alloc.reviewer else None,
                            'reviewerId':alloc.reviewer_id,
                            'start': alloc.start_date.strftime(allocation.TAS_DATE_FORMAT) if alloc.start_date else None,
                            'status': alloc.status.capitalize(),
                            'storageUsed': 0,
                            'storageAllocated': 0,
                            'storageRequested': 0,
                            }
        return reformated_alloc

    def portal_to_tas_proj_obj(self, proj, fetch_allocations=True,
                               fetch_balance=True, pi_info=None):
        if not pi_info:
            pi_info = self.portal_user_to_tas_obj(proj.pi)
        tas_proj = {'description': proj.description,
                    'piId': proj.pi_id,
                    'title': proj.title,
                    'nickname': proj.nickname,
                    'chargeCode': proj.charge_code,
                    'typeId': proj.type_id,
                    'fieldId': proj.field_id,
                    'type': proj.type.name if proj.type else None,
                    'field': proj.field.name if proj.field else None,
                    'allocations': [],
                    'source': 'Chameleon',
                    'pi': pi_info,
                    'id': proj.id}
        if fetch_allocations:
            allocations = self._get_project_allocations(proj, fetch_balance=fetch_balance)
            tas_proj['allocations'] = allocations
        return tas_proj

    def tas_to_portal_alloc_obj(self, alloc, project_charge_code):
        reformated_alloc = {}
        for key, val in list(alloc.items()):
            if key in allocation.TAS_TO_PORTAL_MAP:
                reformated_alloc[allocation.TAS_TO_PORTAL_MAP[key]] = val

        portal_project = portal_proj.objects.filter(charge_code=project_charge_code)
        if len(portal_project) == 0:
            logger.error('Couldn\'t find project {} in portal'.format(alloc['project']))
        else:
            reformated_alloc['project_id'] = portal_project[0].id
        reformated_alloc['date_requested'] = datetime.now(pytz.utc)
        reformated_alloc['status'] = 'pending'

        reformated_alloc = portal_alloc(**reformated_alloc)

        return reformated_alloc

    def tas_to_portal_proj_obj(self, proj):
        reformated_proj = {}
        for key, val in list(proj.items()):
            if key in project.TAS_TO_PORTAL_MAP:
                reformated_proj[project.TAS_TO_PORTAL_MAP[key]] = val
        if 'id' in proj:
            reformated_proj['id'] = proj['id']
            reformated_proj['nickname'] = portal_proj.objects.get(pk=proj['id']).nickname
        else:
            # assign temporary charge code for new project
            dt = datetime.now()
            reformated_proj['charge_code'] = TMP_PROJECT_CHARGE_CODE_PREFIX + str(time.mktime(dt.timetuple()) + dt.microsecond/1e6).replace('.', '')

        reformated_proj = portal_proj(**reformated_proj)

        return reformated_proj

    def portal_user_to_tas_obj(self, user, role='Standard'):
        try:
            pi_eligibility = user.pi_eligibility()
        except:
            pi_eligibility = 'Ineligible'

        tas_user = {'username': user.username,
                    'firstName': user.first_name,
                    'lastName': user.last_name,
                    'source': 'Chameleon',
                    'email': user.email,
                    'id': user.id,
                    'piEligibility': pi_eligibility,
                    'citizenship': None,
                    'title': None,
                    'phone': None,
                    'country': None,
                    'department': None,
                    'institution': None,
                    'role': role}

        return tas_user

    def update_user_metadata_from_keycloak(self, tas_formatted_user):
        keycloak_client = KeycloakClient()
        keycloak_user = keycloak_client.get_keycloak_user_by_username(tas_formatted_user['username'])

        if keycloak_user:
            attrs = keycloak_user['attributes']
            tas_formatted_user.update({
                'institution': attrs.get('affiliationInstitution', None),
                'department': attrs.get('affiliationDepartment', None),
                'title': attrs.get('affiliationTitle', None),
                'country': attrs.get('country', None),
                'phone': attrs.get('phone', None),
                'citizenship': attrs.get('citizenship', None)})
        return tas_formatted_user

    def get_attr(self, obj, key):
        '''Attempt to resolve the key either as an attribute or a dict key'''
        if isinstance(obj, dict):
            return obj.get(key)
        else:
            return getattr(obj, key, None)

    def set_attr(self, obj, key, val):
        '''Attempt to resolve the key either as an attribute or a dict key'''
        if isinstance(obj, dict):
            obj[key] = val
        else:
            setattr(obj, key, val)
        return obj
