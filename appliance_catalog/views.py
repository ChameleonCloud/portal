from django.shortcuts import render, get_object_or_404
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
from .forms import ApplianceForm
from .models import Appliance
import logging

logger = logging.getLogger('default')


def create(request):
	if request.method == 'POST':
		form = ApplianceForm(request.POST, request.FILES)
		logger.info(request.FILES)
		if form.is_valid():
			post = form.save(commit=False)
			post.created_user = request.user
			post.save()
		return HttpResponseRedirect(reverse('appliance_catalog:list'))

	else:
		form = ApplianceForm()
		return render(request, 'appliance_catalog/create.html', {'appliance_form': form})


def list(request):
	appliances = Appliance.objects.all()
	logger.info(appliances)
	return render(request, 'appliance_catalog/list.html', {'appliances': appliances})


def detail(request, pk):
	appliance = get_object_or_404(Appliance, pk=pk)
	logger.info(appliance)
	return render(request, 'appliance_catalog/detail.html', {'appliance': appliance})


def edit(request, pk):
	if request.method == 'POST':
		appliance = get_object_or_404(Appliance, pk=pk)
		form = ApplianceForm(request.POST, instance=appliance)
		if form.is_valid():
			post = form.save(commit=False)
			post.updated_user = request.user
			post.save()
			return HttpResponseRedirect(reverse('appliance_catalog:list'))
	else:
		appliance = get_object_or_404(Appliance, pk=pk)
		logger.info(appliance)
		form = ApplianceForm(instance=appliance)
		return render(request, 'appliance_catalog/create.html', {'appliance_form': form})


def delete(request, pk):
	appliance = get_object_or_404(Appliance, pk=pk)
	logger.info(appliance)
	appliance.delete()
	return HttpResponseRedirect(reverse('appliance_catalog:list'))
