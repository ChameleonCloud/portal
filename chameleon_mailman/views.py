from chameleon_token.decorators import token_required
from datetime import datetime, timedelta
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

@token_required
def mailman_export_list(request):
    """
    Returns a text file, listing the email addresses, one per line, of all
    users who joined in the last day.
    """
    try:
        # Ignoring complexity of timezones because we just want a fuzzy range
        # that is limited to a recent window
        start_of_yesterday = datetime.today() - timedelta(days=1)
        users = get_user_model().objects.filter(is_active=True,
                                                date_joined__gte=start_of_yesterday)
        content = list(u.email for u in users)
        response = HttpResponse('\n'.join(content), content_type='text/plain')
        response['Content-Disposition'] = 'attachment; filename="new_members.txt"'
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
