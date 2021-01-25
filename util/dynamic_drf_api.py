from allocations.allocations_api import BalanceServiceClient
from allocations.models import Allocation
from django.contrib.auth import get_user_model
from dynamic_rest.serializers import DynamicModelSerializer
from dynamic_rest.viewsets import DynamicModelViewSet
from projects.models import Field, Project, Type


class UserSerializer(DynamicModelSerializer):
    """Serialize user object."""

    class Meta:
        """default properties to serialize."""

        model = get_user_model()

        fields = [
            "username",
            "first_name",
            "last_name",
            "email",
        ]


class UserViewSet(DynamicModelViewSet):
    """Project field names API."""

    queryset = get_user_model().objects.all()
    serializer_class = UserSerializer


class AllocationSerializer(DynamicModelSerializer):
    """Serialize Allocation object."""

    """
    keys in the array "fields" can be queried in URL by "?key=value"
    Their format can be overridden by defining it outside the "Meta" class.
    """

    # if self.instance.status == "active":
    #     bsc = BalanceServiceClient()
    #     su_usage = bsc.get_balance(project)

    class Meta:
        """default properties to serialize."""

        model = Allocation
        fields = [
            "id",
            "project",
            "status",
            "start_date",
            "expiration_date",
            "su_used",
            "requestor",
            "date_requested",
            "su_requested",
            "justification",
            "reviewer",
            "date_reviewed",
            "su_allocated",
            "decision_summary",
        ]


class AllocationViewSet(DynamicModelViewSet):
    """Project field names API."""

    queryset = Allocation.objects.all()
    serializer_class = AllocationSerializer


class ProjectSerializer(DynamicModelSerializer):
    """Serializer for project obeects, using dynamic REST."""

    class Meta:
        """Default class properties."""

        model = Project
        name = "project"
        fields = [
            "charge_code",
            "title",
            "nickname",
            "type",
            "field",
            "description",
            "pi",
        ]


class ProjectViewSet(DynamicModelViewSet):
    """Projects API."""

    queryset = Project.objects.all()
    serializer_class = ProjectSerializer


class ProjectTypeSerializer(DynamicModelSerializer):
    """Serialize project type object with dynamic filters."""

    class Meta:
        """Default class properties."""

        model = Type
        name = "type"
        fields = ["name"]


class TypeViewSet(DynamicModelViewSet):
    """Viewset for project types."""

    queryset = Type.objects.all()
    serializer_class = ProjectTypeSerializer


class ProjectFieldSerializer(DynamicModelSerializer):
    """Viewset for project field names."""

    class Meta:
        """Default class properties."""

        model = Field
        name = "field"
        fields = ["name"]


class FieldViewSet(DynamicModelViewSet):
    """Project field names API."""

    queryset = Field.objects.all()
    serializer_class = ProjectFieldSerializer
