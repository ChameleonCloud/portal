from chameleon_token.decorators import token_required
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import render
from django.template.response import TemplateResponse
from .models import MailmanSubscription
from .forms import MailmanSubscriptionForm
import logging


logger = logging.getLogger('default')

def is_user_subscribed_to_list(user, list_name):
    try:
        if list_name == 'users_list':
            subscribed = user.subscriptions.users_list
        elif list_name == 'outages_list':
            subscribed = user.subscriptions.outage_notifications
        else:
            raise Exception('Unknown list "%s"' % list_name)
    except MailmanSubscription.DoesNotExist:
        subscribed = True # users are subscribed by default

    return subscribed

@token_required
def mailman_export_list(request, list_name):
    """
    Returns a text file, listing the email addresses, one per line, of all
    active (in Chamelon portal) Chameleon Users subscribed to the given list.
    """
    try:
        users = get_user_model().objects.filter(is_active=True)
        content = list(u.email for u in users if is_user_subscribed_to_list(u, list_name))
        response = HttpResponse('\n'.join(content), content_type='text/plain')
        response['Content-Disposition'] = 'attachment; filename="%s.txt"' % list_name
    except Exception as e:
        response = HttpResponse('Error: %s' % e)
        response.status_code = 400

    return response

@login_required
def manage_mailman_subscriptions(request):
    try:
        user_sub = MailmanSubscription.objects.get(user=request.user)
    except MailmanSubscription.DoesNotExist:
        user_sub = MailmanSubscription(user=request.user)

    if request.method == 'POST':
        form = MailmanSubscriptionForm(request.POST, instance=user_sub)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your email subscription preferences have been updated.')
    else:
        form = MailmanSubscriptionForm(instance=user_sub)

    context = {'form': form}
    return render(request, 'chameleon_mailman/manage_mailman_subscriptions.html', context)
