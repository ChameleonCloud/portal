from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from chameleon.decorators import terms_required
from django.contrib import messages
from django.http import (Http404, HttpResponseForbidden, HttpResponse,
                         HttpResponseRedirect, HttpResponseNotAllowed, JsonResponse)
from django.core.urlresolvers import reverse
from django.core.exceptions import PermissionDenied
from django import forms
from datetime import datetime
from django.conf import settings
from pytas.http import TASClient
from pytas.models import Project
from models import ProjectExtras, Publication
from projects.serializer import ProjectExtrasJSONSerializer
from django.contrib.auth.models import User
from django.views.decorators.http import require_POST
from forms import ProjectCreateForm, ProjectAddUserForm,\
    AllocationCreateForm, EditNicknameForm, AddBibtexPublicationForm
from django.db import IntegrityError
import re
import logging
import json
from keystoneclient.v3 import client as ks_client
from keystoneauth1 import adapter
from django.conf import settings
import uuid
import sys
from allocations.allocation_mapper import ProjectAllocationMapper
from util.auth.keystone_auth import get_ks_auth_and_session

logger = logging.getLogger('projects')


def project_pi_or_admin_or_superuser(user, project):
    if user.is_superuser:
        return True

    if user.groups.filter(name='Allocation Admin').count() == 1:
        return True

    if user.username == project.pi.username:
        return True

    return False

def project_member_or_admin_or_superuser(user, project, project_user):
    if project_pi_or_admin_or_superuser(user, project):
        return True

    for pu in project_user:
        if user.username == pu.username:
            return True

    return False

@login_required
def user_projects(request):
    context = {}

    tas = TASClient()
    user = tas.get_user(username=request.user)
    
    context['is_pi_eligible'] = user['piEligibility'] == 'Eligible'
    context['username'] = request.user.username

    projects = get_projects(request)

    context['projects'] = projects

    return render(request, 'projects/user_projects.html', context)

def get_unique_projects(projects, alloc_status=[]):
    charge_codes = []
    unique_projects = []
    if not projects:
        return unique_projects
    for p in projects:
        if p.source == 'Chameleon':
            if alloc_status:
                for a in p.allocations:
                    if a.status in alloc_status:
                        if p.chargeCode not in charge_codes:
                            unique_projects.append(p)
                            charge_codes.append(p.chargeCode)
            else:
                if p.chargeCode not in charge_codes:
                    unique_projects.append(p)
                    charge_codes.append(p.chargeCode)
    return unique_projects

def get_projects(request, alloc_status=[]):
    projects = Project.list(username=request.user)
    projects = get_unique_projects(projects, alloc_status)
    projects = list(p for p in projects if p.source == 'Chameleon')

    for proj in projects:
        try:
            extras = ProjectExtras.objects.get(tas_project_id=proj.id)
            proj.__dict__['nickname'] = extras.nickname
        except ProjectExtras.DoesNotExist:
            project_nickname = None

    return projects

@login_required
def view_project(request, project_id):
    try:
        project = Project(project_id)
        if project.source != 'Chameleon':
            raise Http404('The requested project does not exist!')
    except Exception as e:
        logger.error(e)
        raise Http404('The requested project does not exist!')

    form = ProjectAddUserForm()
    nickname_form = EditNicknameForm()
    pubs_form = AddBibtexPublicationForm()
    if request.POST and project_pi_or_admin_or_superuser(request.user, project):
        if 'add_user' in request.POST:
            form = ProjectAddUserForm(request.POST)
            if form.is_valid():
                # try to add user
                try:
                    add_username = form.cleaned_data['username']
                    if project.add_user(add_username):
                        update_user_keystone_project_membership(project.pi.username, project, add_member=True)
                        update_user_keystone_project_membership(add_username, project, add_member=True)
                        messages.success(request,
                            'User "%s" added to project!' % add_username)
                        form = ProjectAddUserForm()
                except Exception as e:
                    logger.error(e)
                    logger.exception('Failed adding user')
                    form.add_error('username', '')
                    form.add_error('__all__', 'Unable to add user. Confirm that the '
                        'username is correct.')
            else:
                form.add_error('__all__', 'There were errors processing your request. '
                    'Please see below for details.')
        elif 'nickname' in request.POST:
            nickname_form = edit_nickname(request, project_id)
        else:
            form = ProjectAddUserForm()

        if 'del_user' in request.POST:
            # try to remove user
            try:
                del_username = request.POST['username']
                if project.remove_user(del_username):
                    update_user_keystone_project_membership(del_username, project, add_member=False)
                    messages.success(request, 'User "%s" removed from project' % del_username)
            except:
                logger.exception('Failed removing user')
                messages.error(request, 'An unexpected error occurred while attempting '
                    'to remove this user. Please try again')

    users = project.get_users()

    if not project_member_or_admin_or_superuser(request.user, project, users):
        raise PermissionDenied
    
    mapper = ProjectAllocationMapper(request)
    project = mapper.map(project)

    for a in project.allocations:
        if a.start and isinstance(a.start, basestring):
            a.start = datetime.strptime(a.start, '%Y-%m-%dT%H:%M:%SZ')
        if a.dateRequested:
            if isinstance(a.dateRequested, basestring):
                a.dateRequested = datetime.strptime(a.dateRequested, '%Y-%m-%dT%H:%M:%SZ')
        if a.dateReviewed:
            if isinstance(a.dateReviewed, basestring):
                a.dateReviewed = datetime.strptime(a.dateReviewed, '%Y-%m-%dT%H:%M:%SZ')
        if a.end:
            if isinstance(a.end, basestring):
                a.end = datetime.strptime(a.end, '%Y-%m-%dT%H:%M:%SZ')

    try:
        extras = ProjectExtras.objects.get(tas_project_id=project_id)
        project_nickname = extras.nickname
    except ProjectExtras.DoesNotExist:
        project_nickname = None

    user_mashup = []
    for u in users:
        if u.role == 'PI': # Exclude PI from member list
            continue
        user = {}
        user['username'] = u.username
        user['role'] = u.role
        try:
            portal_user = User.objects.get(username=u.username)
            user['email'] = portal_user.email
            user['first_name'] = portal_user.first_name
            user['last_name'] = portal_user.last_name
        except User.DoesNotExist:
            logger.info('user: ' + u.username + ' not found')
        user_mashup.append(user)

    return render(request, 'projects/view_project.html', {
        'project': project,
        'project_nickname': project_nickname,
        'users': user_mashup,
        'is_pi': request.user.username == project.pi.username,
        'form': form,
        'nickname_form': nickname_form,
        'pubs_form': pubs_form
    })

def get_admin_ks_client():
    auth, sess = get_ks_auth_and_session()
    sess = adapter.Adapter(sess, interface='public', region_name=settings.OPENSTACK_TACC_REGION)
    return ks_client.Client(session=sess, interface='public', region_name=settings.OPENSTACK_TACC_REGION)

def set_ks_project_nickname(chargeCode, nickname):
    ks = get_admin_ks_client()
    project_list = ks.projects.list()
    project = filter(lambda this: getattr(this, 'charge_code', None) == chargeCode, project_list)
    logger.info('Assigning nickname {0} to project with charge code {1}'.format(nickname, chargeCode))
    if project and project[0]:
        project = project[0]
    ks.projects.update(project, name=nickname)
    logger.info('Successfully assigned nickname {0} to project with charge code {1}'.format(nickname, chargeCode))

def create_user(username, email, password, ks_client):
    ks_user = None
    try:
        logger.info('Creating user with username: {0}, email:{1}, domain_id: {2} '.format(username,email,ks_client.user_domain_id))
        if not password:
            password = str(uuid.uuid4())
        ks_user_options = {'lock_password':True}
        ks_user = ks_client.users.create(username, domain=ks_client.user_domain_id, email=email,\
            password=password, options=ks_user_options)
        logger.info('Created user with username: {0}, email:{1}, domain_id: {2} '.format(ks_user.name, ks_user.email, ks_client.user_domain_id))
    except Exception as e:
        logger.error('Error creating user with username: {0}, email:{1}, domain_id: {2} '.format(username, email, ks_client.user_domain_id))
        logger.error(e)
    return ks_user

def update_user_keystone_project_membership(username, tas_project, add_member=True):
    ks_client = get_admin_ks_client()
    # then get domain id from keystone, domain_id = keystone.user_domain_id
    domain_id = ks_client.user_domain_id
    # then get member roles, member_role = keystone.roles.list(name='_member_',domain=domain_id)[0]
    member_role = ks_client.roles.list(name='_member_',domain=domain_id)[0]
    # now get project by charge_code:
    project_list = ks_client.projects.list(domain=domain_id)
    project = filter(lambda this: getattr(this, 'charge_code', None) == tas_project.chargeCode, project_list)
    if project and project[0]:
        project = project[0]
    else:
        project = None

   # Get user from keystone
    ks_user = get_keystone_user(ks_client, username)
    if add_member:
        # If we're adding a member to a project, let's make sure the user exists and is enabled
        if ks_user:
            if not ks_user.enabled:
                ks_client.users.update(ks_user,enabled=True)
        else:
            email = TASClient().get_user(username=username).get('email')
            ks_user = create_user(username, email, None, ks_client)
        if not project:
            project = create_ks_project(tas_project, ks_client)
        ks_client.roles.grant(member_role.id, user=ks_user, project=project)
    else:
        if project and ks_user:
            ks_client.roles.revoke(member_role.id, user=ks_user, project=project)

def create_ks_project(tas_project, ks_client):
    project_extras = ProjectExtras.objects.filter(tas_project_id=tas_project.id)
    name = tas_project.chargeCode
    if project_extras:
        name = project_extras[0].nickname
    ks_project = ks_client.projects.create(charge_code=tas_project.chargeCode,name=name, \
        domain=ks_client.user_domain_id,description=tas_project.description)
    return ks_project

def get_keystone_user(ks_client, username):
    try:
        logger.debug('Getting user from keystone: ' + username)
        user = ks_client.users.list(name=username)
        if user and user[0]:
            logger.debug('User found in keystone : ' + username)
            return user[0]
        else:
            logger.info('User not found in keystone: ' + username)
            return None
    except Exception as e:
        logger.error('Error retrieving user: {}'.format(username + ': ' + e.message) + str(sys.exc_info()[0]))
        return None

def update_keystone_user_status(username, enabled=False):
    ks_client = get_admin_ks_client()
    # then get domain id from keystone, domain_id = keystone.user_domain_id
    domain_id = ks_client.user_domain_id
    # then get member roles, member_role = keystone.roles.list(name='_member_',domain=domain_id)[0]
    member_role = ks_client.roles.list(name='_member_',domain=domain_id)[0]

   # Get user from keystone
    ks_user = get_keystone_user(ks_client, username)
    if ks_user:
        logger.info('Updating keystone user status for: ' + username + ' to: ' + str(enabled))
        ks_client.users.update(ks_user, enabled=enabled)
    else:
        logger.info('Tried disabling keystone user: ' + username+ ' to: ' + str(enabled) + ' but user not found')


@login_required
@terms_required('project-terms')
def create_allocation(request, project_id, allocation_id=-1):
    tas = TASClient()

    user = tas.get_user(username=request.user)
    if user['piEligibility'] != 'Eligible':
        messages.error(request,
                       'Only PI Eligible users can request allocations. If you would '
                       'like to request PI Eligibility, please '
                       '<a href="/user/profile/edit/">submit a PI Eligibility '
                       'request</a>.')
        return HttpResponseRedirect(reverse('projects:user_projects'))

    project = Project(project_id)
    allocation = None
    if allocation_id > 0:
        for a in project.allocations:
            if a.id == int(allocation_id):
                allocation = a

    # goofiness that we should clean up later; requires data cleansing
    abstract = project.description
    if '--- Supplemental details ---' in abstract:
        additional = abstract.split('\n\n--- Supplemental details ---\n\n')
        abstract = additional[0]
        additional = additional[1].split('\n\n--- Funding source(s) ---\n\n')
        justification = additional[0]
        if len(additional) > 1:
            funding_source = additional[1]
        else:
            funding_source = ''
    elif allocation:
        justification = allocation.justification
        if '--- Funding source(s) ---' in justification:
            parts = justification.split('\n\n--- Funding source(s) ---\n\n')
            justification = parts[0]
            funding_source = parts[1]
        else:
            funding_source = ''
    else:
        justification = ''
        funding_source = ''

    if request.POST:
        form = AllocationCreateForm(request.POST,
                                    initial={'description': abstract,
                                             'supplemental_details': justification,
                                             'funding_source': funding_source})
        if form.is_valid():
            allocation = form.cleaned_data.copy()
            allocation['computeRequested'] = 20000

            # Also update the project
            project.description = allocation.pop('description', None)

            supplemental_details = allocation.pop('supplemental_details', None)

            logger.error(supplemental_details)
            funding_source = allocation.pop('funding_source', None)

            #if supplemental_details == None:
            #    raise forms.ValidationError("Justifcation is required")
            # This is required
            if not supplemental_details:
                supplemental_details = '(none)'

            logger.error(supplemental_details)

            if funding_source:
                allocation['justification'] = '%s\n\n--- Funding source(s) ---\n\n%s' % (
                    supplemental_details, funding_source)
            else:
                allocation['justification'] = supplemental_details

            allocation['projectId'] = project_id
            allocation['requestorId'] = tas.get_user(username=request.user)['id']
            allocation['resourceId'] = '39'

            if allocation_id > 0:
                allocation['id'] = allocation_id

            try:
                logger.info('Submitting allocation request for project %s: %s' %
                            (project.id, allocation))
                updated_project = tas.edit_project(project.as_dict())
                tas.create_allocation(allocation)
                messages.success(request, 'Your allocation request has been submitted!')
                return HttpResponseRedirect(
                    reverse('projects:view_project', args=[updated_project['id']]))
            except:
                logger.exception('Error creating allocation')
                form.add_error('__all__',
                               'An unexpected error occurred. Please try again')
        else:
            form.add_error('__all__',
                           'There were errors processing your request. '
                           'Please see below for details.')
    else:
        form = AllocationCreateForm(initial={'description': abstract,
                                             'supplemental_details': justification,
                                             'funding_source': funding_source})
    context = {
        'form': form,
        'project': project,
        'alloc_id': allocation_id,
        'alloc': allocation
    }
    return render(request, 'projects/create_allocation.html', context)


@login_required
@terms_required('project-terms')
def create_project(request):
    tas = TASClient()
    user = tas.get_user(username=request.user)
    if user['piEligibility'] != 'Eligible':
        messages.error(request,
                       'Only PI Eligible users can create new projects. '
                       'If you would like to request PI Eligibility, please '
                       '<a href="/user/profile/edit/">submit a PI Eligibility '
                       'request</a>.')
        return HttpResponseRedirect(reverse('projects:user_projects'))
    if request.POST:
        form = ProjectCreateForm(request.POST)
        if form.is_valid():
            # title, description, typeId, fieldId
            project = form.cleaned_data.copy()
            # let's check that any provided nickname is unique
            nickname = project.pop('nickname').strip()
            nickname_valid = nickname and ProjectExtras.objects.filter(nickname=nickname).count() < 1

            if not nickname_valid:
                form.add_error('__all__',
                            'Project nickname unavailable')
                return render(request, 'projects/create_project.html', {'form': form})

            project.pop('accept_project_terms', None)

            # pi
            pi_user = tas.get_user(username=request.user)
            project['piId'] = pi_user['id']

            # allocations
            allocation = {
                'resourceId': 39,
                'requestorId': pi_user['id'],
                'computeRequested': 20000,
            }

            supplemental_details = project.pop('supplemental_details', None)
            funding_source = project.pop('funding_source', None)

            #if supplemental_details == None:
            #    raise forms.ValidationError("Justifcation is required")
            if not supplemental_details:
                supplemental_details = '(none)'

            if funding_source:
                allocation['justification'] = '%s\n\n--- Funding source(s) ---\n\n%s' % (
                    supplemental_details, funding_source)
            else:
                allocation['justification'] = supplemental_details

            project['allocations'] = [allocation]

            # startup
            project['typeId'] = 2

            # source
            project['source'] = 'Chameleon'
            try:
                created_project = tas.create_project(project)
                logger.info('newly created project: ' + json.dumps(created_project))
                tas_project_id = created_project['id']
                charge_code = created_project['chargeCode']
                pextras = ProjectExtras.objects.create(tas_project_id=tas_project_id, nickname=nickname,charge_code=charge_code)
                pextras.save()
                messages.success(request, 'Your project has been created!')
                return HttpResponseRedirect(
                    reverse('projects:view_project', args=[created_project['id']]))
            except:
                logger.exception('Error creating project')
                form.add_error('__all__',
                               'An unexpected error occurred. Please try again')
        else:
            form.add_error('__all__',
                           'There were errors processing your request. '
                           'Please see below for details.')
    else:
        form = ProjectCreateForm()

    return render(request, 'projects/create_project.html', {'form': form})


@login_required
def edit_project(request):
    context = {}
    return render(request, 'projects/edit_project.html', context)

@require_POST
def edit_nickname(request, project_id):
    project = Project(project_id)
    if not project_pi_or_admin_or_superuser(request.user, project):
       messages.error(request, 'Only the project PI can update nickname.')
       return EditNicknameForm()

    form = EditNicknameForm(request.POST)
    if form.is_valid():
        # try to update nickname
        try:
            nickname = form.cleaned_data['nickname']
            pextras, created = ProjectExtras.objects.get_or_create(tas_project_id=project_id)
            pextras.charge_code = project.chargeCode
            pextras.nickname = nickname
            pextras.save()
            form = EditNicknameForm()
            set_ks_project_nickname(project.chargeCode, nickname)
            messages.success(request, 'Update Successful')
        except:
            messages.error(request, 'Nickname not available')
        return form
    else:
        messages.error(request, 'Nickname not available')
    return form

def get_extras(request):
    provided_token = request.GET.get('token') if request.GET.get('token') else None
    stored_token = getattr(settings, 'PROJECT_EXTRAS_API_TOKEN', None)
    if not provided_token or not stored_token or provided_token != stored_token:
        logger.error('Project Extras json api Access Token validation failed')
        return HttpResponseForbidden()

    logger.info('Get all project extras json endpoint requested')
    response = {
        'status': 'success'
    }
    try:
        serializer = ProjectExtrasJSONSerializer()
        response['message'] = ''
        extras = json.loads(serializer.serialize(ProjectExtras.objects.all()))
        response['result'] = extras
    except ProjectExtras.DoesNotExist:
        response['message'] = 'Does not exist.'
        response['result'] = None
    return JsonResponse(response)
