from django.shortcuts import render, get_object_or_404
from django.http import HttpResponseRedirect, HttpResponse
from django.core.urlresolvers import reverse, reverse_lazy
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Q
from django.utils.decorators import method_decorator
from django.shortcuts import render_to_response
from django.views.generic.edit import DeleteView
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from .forms import ApplianceForm
from .models import Appliance, Keyword, ApplianceTagging
from .serializers import MyJSONSerialiser
import markdown_deux
import logging
import json

logger = logging.getLogger('default')


def app_list(request):
    logger.info('App catalog requested.')
    return render(request, 'appliance_catalog/list.html')


def get_appliances(request):
    logger.info('Get appliances json endpoint requested.')
    keywords = request.GET.getlist('keywords')
    search = request.GET.get('search')
    logger.debug('URL query params: search=%s, keywords=%s', search, keywords)
    if keywords:
        appliances = Appliance.objects.filter(keywords__in=keywords)
        if appliances and search:
            appliances = appliances.filter(
                    Q(name__icontains=search) | Q(description__icontains=search) | Q(author_name__icontains=search))
        elif search:
            appliances = Appliance.objects.filter(
            Q(name__icontains=search) | Q(description__icontains=search) | Q(author_name__icontains=search))
    else:
        appliances = Appliance.objects.all()

    for appliance in appliances:
        appliance.description = markdown_deux.markdown(appliance.description)
    logger.debug('Total matching appliances found: %d.', appliances.count())
    response = {
        'status': 'success',
        'message': ''
    }
    serializer = MyJSONSerialiser()
    response['result'] = json.loads(serializer.serialize(appliances))

    logger.info('Returning json response.')
    return HttpResponse(json.dumps(response), content_type="application/json")


def app_detail(request, pk):
    logger.info('Detail requested for appliance id: %s.', pk)
    appliance = get_object_or_404(Appliance, pk=pk)
    logger.debug('Appliance found. Fetching it\'s keywords.')
    keywords = appliance.keywords.all()
    logger.debug('This appliance has %d keywords.', keywords.count())
    editable = request.user.is_staff or request.user == appliance.created_user
    try:
        validate_email(appliance.author_url)
        appliance.author_contact_type = 'email'
    except ValidationError:
        appliance.author_contact_type = 'url'
    try:
        validate_email(appliance.support_contact_url)
        appliance.support_contact_type = 'email'
    except ValidationError:
        appliance.support_contact_type = 'url'
    context = {
        'appliance': appliance,
        'keywords': keywords,
        'editable': editable
    }
    return render(request, 'appliance_catalog/detail.html', context)


def app_documentation(request, pk):
    logger.info('Documentation requested for appliance id: %s.', pk)
    appliance = get_object_or_404(Appliance, pk=pk)
    logger.debug('Appliance found.')
    context = {
        'appliance': appliance,
    }
    return render(request, 'appliance_catalog/documentation.html', context)


def get_appliance(request, pk):
    logger.info('Get appliance json endpoint requested for id: %s.', pk)
    response = {
        'status': 'success'
    }
    try:
        serializer = MyJSONSerialiser()
        response['message'] = ''
        app = json.loads(serializer.serialize(Appliance.objects.filter(pk=pk)))
        logger.debug('Appliance found. Fetching keywords...')
        keywords = Appliance.objects.get(pk=pk).keywords.all()
        logger.debug('This appliance has %d keyword(s).', keywords.count())
        app[0]['keywords'] = json.loads(serializer.serialize(keywords))
        response['result'] = app
    except Appliance.DoesNotExist:
        response['message'] = 'Does not exist.'
        response['result'] = None
    return HttpResponse(json.dumps(response), content_type="application/json")


def _add_keywords(request, cleaned_data, appliance):
    logger.info('Add keyword requested by user %s with data: %s. Appliance %s will be tagged with this keyword.', request.user.username, cleaned_data, appliance)
    keywords = cleaned_data['keywords']
    new_keywords = cleaned_data['new_keywords']
    ApplianceTagging.objects.filter(appliance_id=appliance.id).delete()
    for keyword in keywords:
        ApplianceTagging.objects.create(keyword=keyword, appliance=appliance)
        logger.info('Appliance %s successfully tagged as: %s.', appliance, keyword)
    if new_keywords:
        new_keywords = new_keywords.split(',')
        for keyword in new_keywords:
            keyword = keyword.strip()
            try:
                existing_keyword = Keyword.objects.get(name=keyword)
                appliance_tagging = ApplianceTagging(keyword=existing_keyword, appliance=appliance)
                appliance_tagging.save()
                logger.info('Appliance %s successfully tagged as: %s.', appliance, existing_keyword)
            except Keyword.DoesNotExist:
                kw = Keyword(name=keyword)
                kw.save()
                logger.info('New tag %s created.', appliance, keyword)
                appliance_tagging = ApplianceTagging(keyword=kw, appliance=appliance)
                appliance_tagging.save()
                logger.info('Appliance %s successfully tagged as: %s.', appliance, kw)


@login_required
def app_create(request):
    if request.method == 'POST':
        logger.info('Appliance create posted by user %s with data %s and files %s', request.user.username, request.POST, request.FILES)
        form = ApplianceForm(request.user, request.POST, request.FILES)
        if form.is_valid():
            logger.debug('Applicate create form is valid. Creating new appliance...')
            appliance = form.save(commit=False)
            appliance.created_user = request.user.username
            appliance.save()
            logger.debug('New appliance successfully created. Adding keywords...')
            _add_keywords(request, form.cleaned_data, appliance)
            logger.debug('Keywords assigned to this appliance successfully.')
            return HttpResponseRedirect(reverse('appliance_catalog:app_list'))
    else:
        logger.info('Appliance create page requested.')
        form = ApplianceForm(request.user)
    return render(request, 'appliance_catalog/create-edit.html', {'appliance_form': form})


@login_required
def app_edit(request, pk):
    logger.info('Appliance edit requested for appliance id: %s', pk)
    appliance = get_object_or_404(Appliance, pk=pk)
    logger.debug('Appliance found.')
    if request.method == 'POST':
        logger.info('Appliance edit posted by user %s with data %s and files %s', request.user.username, request.POST, request.FILES)
        form = ApplianceForm(request.user, request.POST, request.FILES, instance=appliance)
        if form.is_valid():
            logger.debug('Appliance edit form is valid. Updating this appliance...')
            post = form.save(commit=False)
            post.updated_user = request.user.username
            post.save()
            logger.debug('Appliance successfully updated. Updating keywords...')
            _add_keywords(request, form.cleaned_data, appliance)
            logger.debug('Keywords updated for this appliance successfully.')
            return HttpResponseRedirect(reverse('appliance_catalog:app_detail', kwargs={'pk':pk}))
    else:
        logger.info('Appliance edit page requested.')
        form = ApplianceForm(request.user, instance=appliance)
    return render(request, 'appliance_catalog/create-edit.html', {'appliance_form': form, 'edit': True, 'pk': pk})


def get_keywords(request, appliance_id=None):
    if appliance_id:
        logger.info('Get keywords requested for appliance id: %s', appliance_id)
    else:
        logger.info('Get keywords requested')
    response = {}
    response['status'] = 'success'
    response['message'] = ''
    keywords = None
    if appliance_id is not None:
        appliance = get_object_or_404(Appliance, pk=appliance_id)
        logger.debug('Appliance found.')
        keywords = appliance.keywords.all()
    else:
        keywords = Keyword.objects.all()
    serializer = MyJSONSerialiser()
    logger.debug('Total keywords found: %d', keywords.count())
    response['result'] = json.loads(serializer.serialize(keywords))
    return HttpResponse(json.dumps(response), content_type="application/json")

def app_template(request, resource):
    logger.debug('Template requested: %s.html', resource)
    templateUrl = 'appliance_catalog/%s.html' %resource
    return render_to_response(templateUrl)

@login_required
@staff_member_required
def app_delete(request, pk):
    response = {}
    response['result'] = None
    if request.method == 'DELETE':
        logger.info('Appliance delete requested for appliance id: %s by user: %s', pk, request.user.username)
        try:
            appliance = Appliance.objects.get(pk=pk)
            appliance.delete()
            logger.info('Appliance deleted successfully.')
            logger.debug('Appliance found.')
            response['status'] = 'success'
            response['message'] = 'Deleted Successfully'
        except Appliance.DoesNotExist:
            appliance = None;
            response['status'] = 'error'
            response['message'] = 'Appliance with id %s, not found' %pk
        return HttpResponse(json.dumps(response), content_type="application/json")
    else:
        response['status'] = 'error'
        response['message'] = 'Invalid method'
        return HttpResponse(json.dumps(response), content_type="application/json", status=405)

class ApplianceDeleteView(DeleteView):
    model = Appliance
    success_url = reverse_lazy('appliance_catalog:app_list')
    @method_decorator(login_required)
    @method_decorator(staff_member_required)
    def dispatch(self, *args, **kwargs):
        return super(ApplianceDeleteView, self).dispatch(*args, **kwargs)

