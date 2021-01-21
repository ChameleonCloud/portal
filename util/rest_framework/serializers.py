from rest_framework import serializers
from django.contrib.auth import get_user_model
from projects.models import Project
from allocations.models import Allocation

from allocations.allocations_api import BalanceServiceClient


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
    requestor = UserSerializer()
    reviewer = UserSerializer()
    charge_code = serializers.CharField(source="project.charge_code")

    start_date = serializers.DateTimeField(
        format="%Y-%m-%d",
    )
    expiration_date = serializers.DateTimeField(
        format="%Y-%m-%d",
    )
    date_requested = serializers.DateTimeField(
        format="%Y-%m-%d",
    )
    date_reviewed = serializers.DateTimeField(
        format="%Y-%m-%d",
    )

    class Meta:
        model = Allocation
        fields = [
            "id",
            "charge_code",
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


class ProjectSerializer(serializers.ModelSerializer):
    project_type = serializers.CharField(source="type.name")
    field = serializers.CharField(source="field.name")
    pi = UserSerializer()
    allocations = AllocationSerializer(many=True)

    class Meta:
        model = Project
        fields = [
            "charge_code",
            "title",
            "nickname",
            "project_type",
            "field",
            "description",
            "pi",
            "allocations",
        ]
