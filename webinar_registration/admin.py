from django.urls import reverse
from django.contrib import admin
from django.http import HttpResponse
from . import models
from . import forms


def download_registrants_usernames(ModelAdmin, request, queryset):
    """
    Returns a text file listing Webinar registrants, one per line.
    """
    try:
        for obj in queryset:
            participants = models.WebinarRegistrant.objects.filter(webinar__id=obj.id)
            content = list(p.user.username for p in participants)
        response = HttpResponse("\n".join(content), content_type="text/plain")
        response["Content-Disposition"] = (
            'attachment; filename="webinar_%s_participants.txt"' % id
        )
    except Exception as e:
        response = HttpResponse("Error: %s" % e)
        response.status_code = 400

    return response


download_registrants_usernames.short_description = "Download Registrant Usernames"


def download_registrants(ModelAdmin, request, queryset):
    """
    Returns a text file listing Webinar registrants, one per line.
    """
    try:
        for obj in queryset:
            participants = models.WebinarRegistrant.objects.filter(webinar__id=obj.id)
            content = list(
                p.user.first_name
                + ", "
                + p.user.last_name
                + ", "
                + p.user.username
                + ", "
                + p.user.email
                for p in participants
            )
        response = HttpResponse("\n".join(content), content_type="text/plain")
        response["Content-Disposition"] = (
            'attachment; filename="webinar_%s_participants.txt"' % id
        )
    except Exception as e:
        response = HttpResponse("Error: %s" % e)
        response.status_code = 400

    return response


download_registrants.short_description = "Download Registrant Information"


@admin.register(models.Webinar)
class WebinarAdmin(admin.ModelAdmin):
    form = forms.WebinarAdminForm
    list_display = (
        "name",
        "start_date",
        "end_date",
        "registration_open",
        "registration_closed",
        "number_of_registrants",
        "registration_limit",
        "registrants",
    )
    list_filter = ("name", "registration_open", "registration_closed")
    actions = [download_registrants_usernames, download_registrants]

    def registrants(self, obj):
        url = reverse(
            "admin:webinar_registration_webinarregistrant_changelist"
        )  # , kwargs={'program__id__exact':obj.id})
        return "<a href=%s?webinar__id__exact=%s>View Registrants</a>" % (url, obj.id)

    def number_of_registrants(self, obj):
        return models.WebinarRegistrant.objects.filter(webinar_id=obj.id).count()

    registrants.allow_tags = True


@admin.register(models.WebinarRegistrant)
class WebinarRegistrantAdmin(admin.ModelAdmin):
    form = forms.WebinarRegistrantAdminForm
    list_display = ("user_nice_name", "username", "email", "webinar", "created")
    list_filter = ("webinar",)

    def user_nice_name(self, obj):
        return obj.user.get_full_name()

    def username(self, obj):
        return obj.user.get_username()

    def email(self, obj):
        return obj.user.email

    user_nice_name.short_description = "Name"
