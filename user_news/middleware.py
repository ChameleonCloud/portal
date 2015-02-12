from datetime import datetime
from .models import Notification
from django.contrib import messages

class UserNewsNotificationMiddleware:

    def process_view(self, request, view_func, view_args, view_kwargs):
        notifications = Notification.objects.filter(schedule_on__lt=datetime.now()).filter(schedule_off__gt=datetime.now())
        for notif in notifications:
            if notif.limit_pages:
                display = request.path in notif.limit_pages.splitlines()
            else:
                display = True

            if display:
                if notif.title:
                    message = '<h4>{0}</h4>{1}'.format(notif.title.encode('utf-8'), notif.message.encode('utf-8'))
                else:
                    message = notif.message

                messages.add_message(
                    request,
                    notif.level,
                    message
                )
        return None
