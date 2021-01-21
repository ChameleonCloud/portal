from rest_framework import serializers
from django.contrib.auth import get_user_model
from projects.models import Project
from allocations.models import Allocation

# from allocations.allocations_api import BalanceServiceClient


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()

        fields = [
            "username",
            "first_name",
            "last_name",
            "email",
        ]


class AllocationSerializer(serializers.ModelSerializer):
    """Serialize Allocation object"""

    """
    keys in the array "fields" can be queried in URL by "?key=value"
    Their format can be overridden by defining it outside the "Meta" class.
    """

    class Meta:
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


class NestedAllocationSerializer(AllocationSerializer):
    requestor = UserSerializer()
    reviewer = UserSerializer()


class ProjectSerializer(serializers.ModelSerializer):
    """Serialize project object"""

    class Meta:
        model = Project
        fields = [
            "charge_code",
            "title",
            "nickname",
            "type",
            "field",
            "description",
            "pi",
            "allocations",
        ]


class NestedProjectSerializer(ProjectSerializer):
    """Serialize project object, recursively nesting values"""

    project_type = serializers.CharField(source="type.name")
    field = serializers.CharField(source="field.name")
    pi = UserSerializer()
    allocations = NestedAllocationSerializer(many=True)
