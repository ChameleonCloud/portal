from django.urls import reverse
from django.contrib import admin
from . import models
from . import forms


@admin.register(models.EarlyUserProgram)
class EarlyUserProgramAdmin(admin.ModelAdmin):
    form = forms.EarlyUserProgramAdminForm
    list_display = ("name", "state", "participants")
    list_filter = ("state",)

    def participants(self, obj):
        url = reverse(
            "admin:cc_early_user_support_earlyuserparticipant_changelist"
        )  # , kwargs={'program__id__exact':obj.id})
        return "<a href=%s?program__id__exact=%s>View Participants</a>" % (url, obj.id)

    participants.allow_tags = True


@admin.register(models.EarlyUserParticipant)
class EarlyUserParticipantAdmin(admin.ModelAdmin):
    form = forms.EarlyUserParticipantAdminForm
    list_display = ("user_nice_name", "program", "created", "participant_status")
    list_filter = (
        "program",
        "participant_status",
    )

    def user_nice_name(self, obj):
        return obj.user.get_full_name()

    user_nice_name.short_description = "Name"
