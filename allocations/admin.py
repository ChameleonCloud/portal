from django.contrib import admin
from .models import Charge, Allocation


class AllocationAdmin(admin.ModelAdmin):
    def has_change_permission(self, request, obj=None):
        return False

    list_display = (
        'project',
        'status',
        'date_requested',
        'date_reviewed',
        'reviewer',
    )
    ordering = ["-date_requested"]


admin.site.register(Charge)
admin.site.register(Allocation, AllocationAdmin)
