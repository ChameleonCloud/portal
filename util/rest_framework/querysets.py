from projects.models import Project
from allocations.models import Allocation
from django.db.models import Max


class AllocationQuerySets:
    def orderedAllocationsQuerySet(self):
        """Get all allocations from django DB."""

        return Allocation.objects.order_by("-date_requested")


class ProjectQuerySets:
    def orderedProjectsQuerySet(self):
        """Get all project data from django DB."""

        output_qs = (
            Project.objects.annotate(
                latest_request=Max("allocations__date_requested")
            )
            .select_related("type", "pi", "field")
            .order_by("latest_request")
            .reverse()
        )
        return output_qs
