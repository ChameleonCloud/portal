from django.test import TestCase
from django.utils import timezone
from allocations.models import Charge
from projects.models import Project
from django.contrib.auth import get_user_model
from unittest.mock import patch

from .utils.su_calculators import get_used_sus, get_total_sus, get_active_allocation, project_balances, calculate_user_total_su_usage

class SUCalculatorsTest(TestCase):
    def setUp(self):
        # Set up data for the tests
        User = get_user_model()
        self.now = timezone.now()
        self.test_requestor = User.objects.create_user(
            username="test_requestor",
            password="test_password",
        )
        self.test_user_2 = User.objects.create_user(
            username="test_user_2",
            password="test_password",
        )

        self.project = Project.objects.create(
            tag=None,
            automatically_tagged=False,
            description="This is a test project for allocations.",
            pi=self.test_requestor,
            title="Test Project",
            nickname="test_project",
            charge_code="TEST123"
        )
        self.allocation = self.project.allocations.create(
            project=self.project,
            status="active",
            justification="This is a test allocation.",
            requestor=self.test_requestor,
            date_requested=self.now,
            decision_summary="Test decision summary.",
            reviewer=self.test_requestor,
            date_reviewed=self.now,
            expiration_date=self.now + timezone.timedelta(days=30),
            su_requested=100.0,
            start_date=self.now,
            su_allocated=50.0,
            su_used=25.0,
            balance_service_version=2,
        )
        # Charge is 1/3 through
        self.charge = Charge.objects.create(
            allocation=self.allocation,
            user=self.test_requestor,
            region_name="DEV@UC",
            resource_id="123",
            resource_type="baremetal",
            start_time=self.now - timezone.timedelta(hours=3),
            end_time=self.now + timezone.timedelta(hours=6),
            hourly_cost=2.0,
        )
        Charge.objects.create(
            allocation=self.allocation,
            user=self.test_requestor,
            region_name="DEV@UC",
            resource_id="123",
            resource_type="baremetal",
            start_time=self.now + timezone.timedelta(hours=1),
            end_time=self.now + timezone.timedelta(hours=2),
            hourly_cost=3.0,
        )
        Charge.objects.create(
            allocation=self.allocation,
            user=self.test_user_2,
            region_name="DEV@UC",
            resource_id="123",
            resource_type="baremetal",
            start_time=self.now - timezone.timedelta(hours=2),
            end_time=self.now + timezone.timedelta(hours=2),
            hourly_cost=5.0,
        )

    @patch('django.utils.timezone.now')  # Mocking timezone.now()
    def test_get_used_sus(self, mock_now):
        mock_now.return_value = self.now
        # Test the get_used_sus function
        used_sus = get_used_sus(self.charge)
        self.assertAlmostEqual(used_sus, 6.0, places=2)

    def test_get_total_sus(self):
        # Test the get_total_sus function
        total_sus = get_total_sus(self.charge)
        self.assertAlmostEqual(total_sus, 18.0, places=2)

    def test_get_active_allocation(self):
        # Test the get_active_allocation function
        active_allocation = get_active_allocation(self.project)
        self.assertIsNotNone(active_allocation)
        self.assertEqual(active_allocation.status, "active")

    @patch('django.utils.timezone.now')  # Mocking timezone.now()
    def test_project_balances(self, mock_now):
        mock_now.return_value = self.now
        # Test the project_balances function
        balances = project_balances([self.project.id])
        self.assertEqual(len(balances), 1)
        balance = balances[0]
        self.assertEqual(balance['charge_code'], 'TEST123')
        self.assertAlmostEqual(balance['used'], 16.0, places=2)
        self.assertAlmostEqual(balance['total'], 41.0, places=2)
        self.assertAlmostEqual(balance['allocated'], 50)
        self.assertAlmostEqual(balance['encumbered'], 25.0, places=2)

    @patch('django.utils.timezone.now')  # Mocking timezone.now()
    def test_calculate_user_total_su_usage(self, mock_now):
        mock_now.return_value = self.now
        # Test calculate_user_total_su_usage function
        user = self.charge.user  # Assuming a user is associated with the charge
        total_su_usage = calculate_user_total_su_usage(user, self.project)
        self.assertAlmostEqual(total_su_usage, 21.0, places=2)
