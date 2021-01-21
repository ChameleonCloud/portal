from django_filters.rest_framework import DjangoFilterBackend

from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAdminUser
from rest_framework.generics import ListAPIView
from rest_framework.pagination import LimitOffsetPagination

from rest_framework.renderers import (
    BrowsableAPIRenderer,
    JSONRenderer,
)

from .serializers import (
    AllocationSerializer,
    ProjectSerializer,
    NestedProjectSerializer,
)
from .querysets import CCQuerySets
from .filters import AllocationFilter, ProjectFilter


class PaginationBaseView(LimitOffsetPagination):
    default_limit = 100


class ListBaseView(ListAPIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAdminUser]

    pagination_class = PaginationBaseView
    renderer_classes = [
        BrowsableAPIRenderer,
        JSONRenderer,
    ]
    filter_backends = [DjangoFilterBackend]


class AllocationAppView(ListBaseView):
    """chosen for compatibility with existing allocation app."""

    # Pagination breaks the app
    pagination_class = None
    # Force only JSON renderer for app compatibility
    renderer_classes = [JSONRenderer, BrowsableAPIRenderer]

    serializer_class = NestedProjectSerializer
    filterset_class = ProjectFilter

    def get_queryset(self):
        qs = CCQuerySets()
        return qs.orderedProjects()


class AllocationListView(ListBaseView):
    serializer_class = AllocationSerializer
    filterset_class = AllocationFilter

    def get_queryset(self):
        qs = CCQuerySets()
        return qs.orderedAllocations()


class ProjectListView(ListBaseView):
    serializer_class = ProjectSerializer
    filterset_class = ProjectFilter

    def get_queryset(self):
        qs = CCQuerySets()
        return qs.orderedProjects()
