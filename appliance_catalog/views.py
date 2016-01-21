from django.shortcuts import render, get_object_or_404
from django.http import HttpResponseRedirect, HttpResponse
from django.core.urlresolvers import reverse
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Q
from .forms import ApplianceForm
from .models import Appliance, Keyword, ApplianceTagging
from .serializers import MyJSONSerialiser
import logging
import json

logger = logging.getLogger('default')

def app_list(request):
	appliances = Appliance.objects.all()
	logger.info(appliances)
	return render(request, 'appliance_catalog/list.html', {'appliances': appliances})

def get_appliances(request):
	keywords = request.GET.getlist('keywords')
	search = request.GET.get('search')
	appliances = None
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
	response = {}
	response['status'] = 'success'
	response['message'] = ''
	serializer = MyJSONSerialiser()
	response['result'] = json.loads(serializer.serialize(appliances))
	return HttpResponse(json.dumps(response), content_type="application/json")

def app_detail(request, pk):
	appliance = get_object_or_404(Appliance, pk=pk)
	logger.info(appliance)
	return render(request, 'appliance_catalog/detail.html', {'appliance': appliance})

def get_appliance(request, pk):
	response = {}
	response['status'] = 'success'
	try:
		serializer = MyJSONSerialiser()
		response['message'] = ''
		response['result'] = json.loads(serializer.serialize(Appliance.objects.filter(pk=pk)))
	except Appliance.DoesNotExist:
		response['message'] = 'Does not exist.'
		response['result'] = None
	return HttpResponse(json.dumps(response), content_type="application/json")

def _add_keywords(cleaned_data, appliance):
	keywords = cleaned_data['keywords']
	new_keywords = cleaned_data['new_keywords']
	ApplianceTagging.objects.filter(appliance_id=appliance.id).delete()
	for keyword in keywords:
		ApplianceTagging.objects.create(keyword=keyword, appliance=appliance)

	if new_keywords:
		new_keywords = new_keywords.split(',')
		for keyword in new_keywords:
			keyword = keyword.strip()
			try:
				existing_keyword = Keyword.objects.get(name=keyword)
				appliance_tagging = ApplianceTagging(keyword=existing_keyword, appliance=appliance)
				appliance_tagging.save()
			except Keyword.DoesNotExist:
				kw = Keyword(name=keyword)
				kw.save()
				appliance_tagging = ApplianceTagging(keyword=kw, appliance=appliance)
				appliance_tagging.save()

@login_required
def app_create(request):
	if request.method == 'POST':
		form = ApplianceForm(request.user, request.POST, request.FILES)
		logger.info(form.is_valid())
		if form.is_valid():
			appliance = form.save(commit=False)
			appliance.created_user = request.user.username
			appliance.save()
			_add_keywords(form.cleaned_data, appliance)
			return HttpResponseRedirect(reverse('appliance_catalog:app_list'))
	else:
		form = ApplianceForm(request.user)
	return render(request, 'appliance_catalog/create.html', {'appliance_form': form})

@login_required
def app_edit(request, pk):
	appliance = get_object_or_404(Appliance, pk=pk)
	if request.method == 'POST':
		form = ApplianceForm(request.user, request.POST, request.FILES, instance=appliance)
		if form.is_valid():
			post = form.save(commit=False)
			post.updated_user = request.user.username
			post.save()
			_add_keywords(form.cleaned_data, appliance)
			return HttpResponseRedirect(reverse('appliance_catalog:app_list'))
	else:
		form = ApplianceForm(request.user, instance=appliance)
	return render(request, 'appliance_catalog/create.html', {'appliance_form': form, 'edit': True})

@login_required
@staff_member_required
def app_delete(request, pk):
	appliance = get_object_or_404(Appliance, pk=pk)
	appliance.delete()
	return HttpResponseRedirect(reverse('appliance_catalog:app_list'))


def get_keywords(request, appliance_id=None):
	response = {}
	response['status'] = 'success'
	response['message'] = ''
	keywords = None
	if appliance_id is not None:
		appliance = get_object_or_404(Appliance, pk=appliance_id)
		keywords = appliance.keywords.all()
	else:
		keywords = Keyword.objects.all()
	serializer = MyJSONSerialiser()
	response['result'] = json.loads(serializer.serialize(keywords))
	return HttpResponse(json.dumps(response), content_type="application/json")

