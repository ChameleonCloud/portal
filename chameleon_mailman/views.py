from chameleon_token.decorators import token_required
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import render
from django.template.response import TemplateResponse
from .models import MailmanSubscription
from .forms import MailmanSubscriptionForm
import logging


logger = logging.getLogger('default')

@token_required
def mailman_export_outage_notifications(request):
    """
    Returns a text file, listing the email addresses, one per line, of all
    Chameleon Users subscribed to outage notifications.

    This method is protected by Token Authorization from the chameleon_token
    app.
    """
    subscriptions = MailmanSubscription.objects.all()
    content = list(sub.user.email for sub in subscriptions if sub.outage_notifications)
    response = HttpResponse('\n'.join(content), content_type='text/plain')
    response['Content-Disposition'] = 'attachment; filename="outage_notifications.txt"'
    return response

@token_required
def mailman_export_users_list(request):
    """
    Returns a text file, listing the email addresses, one per line, of all
    Chameleon Users subscribed to outage notifications.

    This method is protected by Token Authorization from the chameleon_token
    app.
    """
    subscriptions = MailmanSubscription.objects.all()
    content = list(sub.user.email for sub in subscriptions if sub.users_list)
    response = HttpResponse('\n'.join(content), content_type='text/plain')
    response['Content-Disposition'] = 'attachment; filename="users_list.txt"'
    return response

@login_required
def manage_mailman_subscriptions(request):
    user_sub = MailmanSubscription.objects.get(user=request.user)
    if request.method == 'POST':
        form = MailmanSubscriptionForm(request.POST, instance=user_sub)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your email subscription preferences have been updated.')
    else:
        form = MailmanSubscriptionForm(instance=user_sub)

    context = {'form': form}
    return render(request, 'chameleon_mailman/manage_mailman_subscriptions.html', context)
