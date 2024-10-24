from django.contrib import admin

from util.keycloak_client import KeycloakClient

from .models import Allocation, Charge


class ChargeInline(admin.TabularInline):
    model = Charge
    extra = 1
    fields = ["region_name", "user"]


class AllocationAdmin(admin.ModelAdmin):
    def project_description(self, obj):
        return str(obj.project.description)

    def project_title(self, obj):
        return str(obj.project.title)

    def pi_name(self, obj):
        return f"{obj.project.pi.first_name} {obj.project.pi.last_name}"

    def pi_email(self, obj):
        return f"{obj.project.pi.email}"

    def pi_institution(self, obj):
        keycloak_client = KeycloakClient()
        uname = obj.project.pi.username
        user = keycloak_client.get_user_by_username(uname)
        return user.get("attributes", {}).get("affiliationInstitution", "")

    list_display = (
        "project_title",
        "project",
        "status",
        "date_requested",
        "date_reviewed",
        "reviewer",
    )
    fields = (
        "pi_name",
        "pi_email",
        "pi_institution",
        "project",
        "project_title",
        "project_description",
        "justification",
        "status",
        "requestor",
        "decision_summary",
        "reviewer",
        "date_requested",
        "date_reviewed",
        "start_date",
        "expiration_date",
        "su_allocated",
    )
    readonly_fields = [
        "pi_name",
        "pi_email",
        "pi_institution",
        "project",
        "project_title",
        "project_description",
        "justification",
        "status",
        "requestor",
        "decision_summary",
        "reviewer",
        "date_requested",
        "date_reviewed",
    ]
    ordering = ["-date_requested"]
    search_fields = [
        "project__charge_code",
        "project__pi__first_name",
        "project__pi__last_name",
    ]
    list_filter = ["status", "date_requested"]
    inlines = [ChargeInline]


admin.site.register(Allocation, AllocationAdmin)
