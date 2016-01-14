from django.shortcuts import render, get_object_or_404
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.contrib.auth.decorators import login_required
from .forms import ApplianceForm
from .models import Appliance, Keyword, ApplianceTagging
import logging

logger = logging.getLogger('default')

def list(request):
	appliances = Appliance.objects.all()
	logger.info(appliances)
	return render(request, 'appliance_catalog/list.html', {'appliances': appliances})


def detail(request, pk):
	appliance = get_object_or_404(Appliance, pk=pk)
	logger.info(appliance)
	return render(request, 'appliance_catalog/detail.html', {'appliance': appliance})


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
def create(request):
	if request.method == 'POST':
		form = ApplianceForm(request.user, request.POST, request.FILES)
		logger.info(form.is_valid())
		if form.is_valid():
			appliance = form.save(commit=False)
			appliance.created_user = request.user.username
			appliance.save()
			_add_keywords(form.cleaned_data, appliance)
			return HttpResponseRedirect(reverse('appliance_catalog:list'))
	else:
		form = ApplianceForm(request.user)
	return render(request, 'appliance_catalog/create.html', {'appliance_form': form})

@login_required
def edit(request, pk):
	if request.method == 'POST':
		appliance = get_object_or_404(Appliance, pk=pk)
		form = ApplianceForm(request.user, request.POST, instance=appliance)
		if form.is_valid():
			post = form.save(commit=False)
			post.updated_user = request.user.username
			logger.info(post.appliance_icon)
			if not post.appliance_icon:
				post.appliance_icon = 'appliance_catalog/icons/default.png'
			post.save()
			_add_keywords(form.cleaned_data, appliance)
			return HttpResponseRedirect(reverse('appliance_catalog:list'))
	else:
		appliance = get_object_or_404(Appliance, pk=pk)
		form = ApplianceForm(request.user, instance=appliance)
	return render(request, 'appliance_catalog/create.html', {'appliance_form': form, 'edit': True})

@login_required
def delete(request, pk):
	appliance = get_object_or_404(Appliance, pk=pk)
	logger.info(appliance)
	appliance.delete()
	return HttpResponseRedirect(reverse('appliance_catalog:list'))
