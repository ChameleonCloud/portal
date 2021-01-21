from projects.models import Project
from allocations.models import Allocation
from django_filters.rest_framework import (
    FilterSet,
    filters,
)


class AllocationFilter(FilterSet):
    status = filters.AllValuesFilter()
    su_used = filters.NumericRangeFilter()
    requestor__username = filters.CharFilter()
    requestor__email = filters.CharFilter()

    class Meta:
        model = Allocation
        fields = [
            "id",
            "status",
            "start_date",
            "expiration_date",
            "su_used",
            "requestor",
            "date_requested",
            "su_requested",
            "justification",
            "reviewer",
            "su_allocated",
            "decision_summary",
        ]


class ProjectFilter(FilterSet):
    type__name = filters.AllValuesFilter()
    field__name = filters.AllValuesFilter()
    pi__username = filters.CharFilter()
    pi__email = filters.CharFilter()

    allocations__status = filters.AllValuesFilter()
    allocations__su_used = filters.NumericRangeFilter()

    class Meta:
        model = Project
        fields = ["charge_code", "title", "nickname", "description"]
