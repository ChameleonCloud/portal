from django.contrib import admin
from django.db import models
from django import forms
from django.utils.safestring import mark_safe
from django.urls import reverse

from balance_service.utils import su_calculators
from util.keycloak_client import KeycloakClient

from .models import Allocation, Charge


class ChargeInline(admin.TabularInline):
    model = Charge
    extra = 1
    fields = [
        "region_name",
        "user",
        "resource_type",
        "resource_id",
        "start_time",
        "end_time",
        "hourly_cost",
    ]
    readonly_fields = ["region_name", "user"]

    formfield_overrides = {
        models.TextField: {"widget": forms.TextInput(attrs={"size": "10"})},
    }

    def has_change_permission(self, request, obj):
        return False


class AllocationAdmin(admin.ModelAdmin):
    def project_title(self, obj):
        return str(obj.project.title)

    def pi_name(self, obj):
        return f"{obj.project.pi.first_name} {obj.project.pi.last_name}"

    def pi_email(self, obj):
        return f"{obj.project.pi.email}"

    def pi_info(self, obj):
        keycloak_client = KeycloakClient()
        kc_user = keycloak_client.get_user_by_username(obj.project.pi.username)
        if not kc_user:
            kc_user = {}
        institution = kc_user.get("attributes", {}).get("affiliationInstitution")
        country = kc_user.get("attributes", {}).get("country")

        return mark_safe(
            f"""<table>
        <tr>
            <td><b>Name</b></td>
            <td>{obj.project.pi.first_name} {obj.project.pi.last_name}</td>
        </tr>
        <tr>
        <td><b>Email</b></td><td>
        <a href="mailto:{obj.project.pi.email}">
            <i class="fa fa-envelope-o"></i> {obj.project.pi.email}
        </a></td>
        </tr>
        <tr>
            <td><b>Institution</b></td><td>{institution}</td>
        </tr>
        <tr>
            <td><b>Country</b></td><td>{country}</td>
        </tr>
        </table>
        """
        )

    def project_info(self, obj):
        return mark_safe(
            f"""<table>
            <tr>
                <td><b>Charge Code</b></td><td>{obj.project.charge_code}</td>
            </tr>
            <tr>
                <td><b>Title</b></td><td>{obj.project.title}</td>
            </tr>
            <tr>
                <td><b>Abstract</b></td><td>{obj.project.description}</td>
            </tr>
            <tr>
                <td><b>Tag</b></td><td>{obj.project.tag.name} - {obj.project.tag.description}</td>
            </tr>
        <table>"""
        )

    def allocation_status(self, obj):
        if obj.status not in ["pending", "waiting"]:
            return f"This allocation is {obj.status}."

        rows = []
        rows.append(
            f"""<tr>
            <td>{obj.id}</td>
            <td>{obj.requestor}</td>
            <td>{obj.date_requested.date()}</td>
            <td><input id="allocationStatus" disabled value="{obj.status}"/></td>
            <td style="min-width: 50ch;">{obj.justification}</td>
            <td>
                <button id="approve-btn" type="button" class="btn btn-success">
                    Approve
                </button>
                <button id="reject-btn" type="button" class="btn btn-danger">
                    Reject
                </button>
                <button id="contact-btn" type="button" class="btn btn-warning">
                    Contact PI
                </button>
            </td>
        </tr>"""
        )

        styles = """
        <style>
            .admin-modal {
                display: none;
                position: fixed;
                z-index: 100;
                left: 0;
                top: 0;
                width: 100%;
                height: 100%;
                background-color: rgba(0,0,0,0.4);
            }
            .modal-content {
                background-color: #fefefe;
                margin: 5% auto;
                padding: 20px;
                border: 1px solid #888;
                width: 40%;
            }
            .modal-content table {
                width: 100%;
            }
            .modal-footer {
                display: flex;
                flex-direction: row-reverse;
            }
            button.btn-danger {
                background-color: rgb(197, 60, 54) !important;
                color: white !important;
            }
            button.btn-warning {
                background-color: rgb(248, 148, 6) !important;
                color: white !important;
            }
            button.btn-success {
                background-color: rgb(89, 178, 89) !important;
                color: white !important;
            }
        </style>
        """
        approve_modal = f"""<div id="alloc-modal-approve" class="admin-modal">
            <div class="modal-content">
                <h4>Allocation Approval</h4>
                <table>
                    <tr><td>Project</td><td><input disabled id="chargeCode" value="{obj.project.charge_code}" /></td></tr>
                    <tr><td>Allocation ID</td><td><input disabled id="allocationId" value="{obj.id}" /></td></tr>
                    <tr><td>Requestor</td><td><input disabled id="requestor" value="{obj.requestor}" /><input disabled id="requestorId" hidden value="{obj.requestor.id}" /><input disabled hidden id="piEmail" value="{obj.project.pi.email}" /></td></tr>
                    
                    <tr><td>Date Requested</td><td>{obj.date_requested.date()}</td></tr>
                    <tr><td>Compute Requested</td><td>{obj.su_requested}</td></tr>
                    <tr><td>Compute Allocated</td><td><input type="number" value="{obj.su_requested}" id="alloc-compute-allocated"></input></td></tr>
                    <tr><td>Start Date</td><td><input id="alloc-start-date" type="date"></input></td></tr>
                    <tr><td>End Date</td><td><input id="alloc-end-date" type="date"></input></td></tr>
                    <tr>
                        <td>Type</td>
                        <td>
                            <select name="allocationApprovalType" id="allocationApprovalType">
                                <option value="default">Not Selected</option>
                                <option value="new">New</option>
                                <option value="renewal">Renewal</option>
                                <option value="recharge">Recharge</option>
                            </select>
                        </td>
                    </tr>
                    <tr>
                        <td>Decision Summary</td>
                        <td>
                            <textarea id="idDecisionSummary" name="decisionSummary" rows="4" cols="53" ></textarea>
                        </td>
                    </tr>
                </table>
                <div class="modal-footer">
                    <button type="button" class="btn-success" id="approve-submit-btn">Approve</button>
                    <button type="button" class="btn-danger" id="close-btn">Cancel</button>
                </div>
            </div>
        </div>
        """
        reject_modal = f"""<div id="alloc-modal-reject" class="admin-modal">
            <div class="modal-content">
                <h4>Allocation Approval</h4>
                <table>
                    <tr><td>Project</td><td>{obj.project.charge_code}</td></tr>
                    <tr><td>Allocation ID</td><td>{obj.id}</td></tr>
                    <tr><td>Requestor</td><td>{obj.requestor}</td></tr>
                    <tr><td>Date Requested</td><td>{obj.date_requested.date()}</td></tr>
                    <tr><td>Compute Requested</td><td>{obj.su_requested}</td></tr>
                    <tr>
                        <td>Decision Summary</td>
                        <td>
                            <textarea id="idDecisionSummaryReject" rows="4" cols="53" ></textarea>
                        </td>
                    </tr>
                </table>
                <div class="modal-footer">
                    <button type="button" class="btn-success" id="reject-submit-btn">Reject</button>
                    <button type="button" class="btn-danger" id="close-btn-reject">Cancel</button>
                </div>
            </div>
        </div>
        """
        contact_modal = """<div id="alloc-modal-contact" class="admin-modal">
            <div class="modal-content">
                <h4>Allocation Approval</h4>
                <table>
                    <tr>
                        <td>Message</td>
                        <td>
                            <textarea id="idContactMessage" rows="4" cols="53" ></textarea>
                        </td>
                    </tr>
                </table>
                <div class="modal-footer">
                    <button type="button" class="btn-success" id="contact-submit-btn">Contact</button>
                    <button type="button" class="btn-danger" id="close-btn-contact">Cancel</button>
                </div>
            </div>
        </div>
        """

        return mark_safe(
            f"""
        <table>
            <thead>
                <tr>
                    <td>ID</td>
                    <th>Requestor</th>
                    <th>Date Requested</th>
                    <th>Status</th>
                    <th>Justification</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tr>
            {"".join(rows)}
            </tr>
        </table>
        {styles}
        {approve_modal}
        {reject_modal}
        {contact_modal}
        """
        )

    def previous_allocations(self, obj):
        rows = []
        for alloc in sorted(
            obj.project.allocations.exclude(status="pending"),
            reverse=True,
            key=lambda x: x.date_requested,
        ):
            real_su_used = alloc.su_used if alloc.su_used else ""
            if not real_su_used:
                balance = su_calculators.project_balances([alloc.project.id])[0]
                real_su_used = balance["total"]
            rows.append(
                f"""<tr>
                <td><a href="{reverse("admin:allocations_allocation_change", args=[alloc.id])}">{alloc.id}</a></td>
                <td>{alloc.requestor}</td>
                <td>{alloc.date_requested.date()}</td>
                <td>{alloc.status}</td>
                <td>{alloc.start_date.date() if alloc.start_date else ""}</td>
                <td>{alloc.expiration_date.date() if alloc.expiration_date else ""}</td>
                <td>
                    <div>
                        <label>
                            {real_su_used} / {alloc.su_allocated if alloc.su_allocated else ""}
                        </label>
                    </div>
                    <progress value="{real_su_used}" max="{alloc.su_allocated}">{real_su_used}</progress>
                </td>
            </tr>
            <tr>
            <td colspan="2"></td>
                <td colspan="4" style="min-width: 50ch;"><details {"open" if alloc.status == "pending" else ""}><summary>Justification (expand)</summary>{alloc.justification}</details></td>
                <td colspan="4" style="min-width: 50ch;">
                    <details {"open" if alloc.status == "pending" else ""}>
                    <summary>Decision Summary (expand)</summary>
                    <ul>
                    <li>Reviewer - {alloc.reviewer if alloc.reviewer else ""}</li>
                    <li>Date Reviewed - {alloc.date_reviewed.date() if alloc.date_reviewed else ""}</li>
                    <li>Summary - {alloc.decision_summary}</li>
                    </ul>
                    </details>
                </td>
            </tr>"""
            )
        return mark_safe(
            f"""
        <table>
            <thead>
                <tr>
                    <th>ID</th>
                    <th>Requestor</th>
                    <th>Date Requested</th>
                    <th>Status</th>
                    <th>Start</th>
                    <th>End</th>
                    <th>SU Usage</th>
                </tr>
            </thead>
            <tr>
            {"".join(rows)}
            </tr>
        </table>
        """
        )

    def alloc_count(self, obj):
        return obj.project.allocations.count()

    def last_su_used(self, obj):
        """Either su used for this alloc, if it isn't pending,
        or the previous allocs su_used
        """
        prev_used = None
        if obj.status == "pending":
            allocs = obj.project.allocations.all().order_by("-date_requested")
            if len(allocs) > 1:
                balance = su_calculators.project_balances([allocs[1].project.id])[0]
                prev_used = balance["total"]
        else:
            balance = su_calculators.project_balances([obj.project.id])[0]
            prev_used = balance["total"]
        return prev_used

    list_display = (
        "date_requested",
        "pi_name",
        "pi_email",
        "project",
        "project_title",
        "alloc_count",
        "status",
        "last_su_used",
        "justification",
    )
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "project_info",
                    "pi_info",
                    "allocation_status",
                    "previous_allocations",
                    "status",
                    "start_date",
                    "expiration_date",
                ),
            },
        ),
    )
    readonly_fields = [
        "pi_info",
        "project_info",
        "allocation_status",
        "previous_allocations",
    ]
    ordering = ["-date_requested"]
    search_fields = [
        "project__charge_code",
        "project__pi__first_name",
        "project__pi__last_name",
    ]
    list_filter = ["status", "date_requested"]
    inlines = [ChargeInline]
    # form = ReviewAllocationForm

    class Media:
        js = (
            "/static/allocations/js/admin.js",
            "/static/scripts/cannedresponses.js",
        )


admin.site.register(Allocation, AllocationAdmin)
