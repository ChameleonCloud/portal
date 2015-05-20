from django.core.urlresolvers import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render

@login_required
def dashboard(request):
    actions = [
        {'name': 'Manage your Projects', 'url': reverse('projects:user_projects')},
        {'name': 'Help Desk Tickets', 'url': reverse('djangoRT:mytickets')},
        {'name': 'Manage Your Account', 'url': reverse('tas:profile')},
    ]
    return render(request, 'dashboard.html', {'actions': actions})

# TODO this needs access restrictions
def mailing_list_subscription(request):
    users = get_user_model().objects.all()

    content = list(u.email for u in users)

    response = HttpResponse('\n'.join(content), content_type='text/plain')
    # response['Content-Disposition'] = 'attachment; filename="mailman.txt"'
    return response
