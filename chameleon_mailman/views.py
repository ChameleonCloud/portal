
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render
from django.template.response import TemplateResponse
from .models import MailmanSubscription
from .forms import MailmanSubscriptionForm
import logging

logger = logging.getLogger('default')

# TODO this needs access restrictions
def mailman_export(request):
    subscriptions = MailmanSubscription.objects.all()

    content = list(sub.user.email for sub in subscriptions if sub.outage_notifications)

    response = HttpResponse('\n'.join(content), content_type='text/plain')
    # response['Content-Disposition'] = 'attachment; filename="mailman.txt"'
    return response

@login_required
def manage_mailman_subscriptions(request):
    user_sub = MailmanSubscription.objects.get(user=request.user)
    if request.method == 'POST':
        form = MailmanSubscriptionForm(request.POST, instance=user_sub)
        if form.is_valid():
            logger.debug('saving subscriptions...')
            form.save()
        else:
            logger.debug(form.errors)
    else:
        form = MailmanSubscriptionForm(instance=user_sub)

    context = {'form': form}
    return render(request, 'chameleon_admin/manage_mailman_subscriptions.html', context)
