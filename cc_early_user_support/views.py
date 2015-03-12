from django.shortcuts import render
from . import forms
# Create your views here.

def index(request):
    return render(request, 'cc_early_user_support/index.html')

def request_early_user(request):
    context = {}

    if request.POST:
        form = forms.EarlyUserRequestForm(request.POST)
        if form.is_valid():
            join_request = form.save(commit=False)
            join_request.user = request.user
            join_request.save()
            context['form'] = forms.EarlyUserRequestForm()
        else:
            pass

        context['form'] = form
    else:
        context['form'] = forms.EarlyUserRequestForm()

    return render(request, 'cc_early_user_support/request_early_user.html', context)
