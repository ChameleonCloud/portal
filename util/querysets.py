import logging

from django.db.models import Max, Prefetch

from allocations.models import Allocation
from projects.models import Project

logger = logging.getLogger(__name__)


class CCQuerySets:
    def allocationsQuerySet(self):
        """Get all allocations from django DB."""
        logger.debug("Allocations QS INIT")
        alloc_qs = Allocation.objects.select_related("requestor", "reviewer")
        return alloc_qs

    def orderedAllocations(self):
        """Sort allocations by date requested."""
        output_qs = self.allocationsQuerySet().order_by("date_requested").reverse()
        return output_qs

    def prefetchAllocations(self, filtered_qs, input_qs):
        """Prefetch allocations, for use by other querysets"""
        pf = Prefetch("allocations", queryset=filtered_qs)
        output_qs = input_qs.prefetch_related(pf)
        return output_qs

    def projectsQuerySet(self):
        """Get all projects from django DB."""
        logger.debug("Projects QS INIT")
        output_qs = Project.objects.select_related("type", "pi", "field")
        return output_qs

    def orderedProjects(self):
        """Get projects, sorted by latest allocation."""
        filtered_qs = self.orderedAllocations()
        project_qs = self.projectsQuerySet()
        output_qs = (
            self.prefetchAllocations(filtered_qs, project_qs)
            .annotate(latest_request=Max("allocations__date_requested"))
            .order_by("-latest_request")
        )
        return output_qs
