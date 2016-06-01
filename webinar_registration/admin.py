from django.core.urlresolvers import reverse
from django.contrib import admin
from . import models
from . import forms

@admin.register(models.Webinar)
class WebinarAdmin(admin.ModelAdmin):
    form = forms.WebinarAdminForm
    list_display = ('name', 'start_date', 'end_date', 'registration_open', 'registration_closed', 'registrants')
    list_filter = ('name', 'registration_open', 'registration_closed')

    # TODO get this worked out
    def registrants(self, obj):
        url = reverse('admin:webinar_registration_webinarregistrant_changelist')#, kwargs={'program__id__exact':obj.id})
        return '<a href=%s?webinar__id__exact=%s>View Participants</a>' % (url, obj.id)

    registrants.allow_tags = True


@admin.register(models.WebinarRegistrant)
class WebinarRegistrantAdmin(admin.ModelAdmin):
    form = forms.WebinarRegistrantAdminForm
    list_display = ('user_nice_name', 'webinar', 'created')
    list_filter = ('webinar',)

    def user_nice_name(self, obj):
        return obj.user.get_full_name()

    user_nice_name.short_description = 'Name'
