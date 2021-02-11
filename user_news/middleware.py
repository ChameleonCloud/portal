from .models import Notification
from django.contrib import messages
from django.utils import timezone
from django.utils.deprecation import MiddlewareMixin

class UserNewsNotificationMiddleware(MiddlewareMixin):

    def process_view(self, request, view_func, view_args, view_kwargs):
        notifications = Notification.objects.filter(schedule_on__lt=timezone.now()).filter(schedule_off__gt=timezone.now())
        for notif in notifications:
            if notif.limit_pages:
                display = request.path in notif.limit_pages.splitlines()
            else:
                display = True

            if display:
                messages.add_message(
                    request,
                    notif.level,
                    notif.display()
                )
        return None
