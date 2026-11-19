import logging

from datetime import timedelta
from unittest import mock

from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model

from projects.models import Project
from util.keycloak_client import KeycloakClient

from allocations import tasks
from allocations.models import Allocation

LOG = logging.getLogger(__name__)


class StatusTests(TestCase):
    def setUp(self):
        User = get_user_model()

        self.test_requestor = User.objects.create_user(
            username="test_requestor",
            password="test_password",
        )

        self.test_reviewer = User.objects.create_user(
            username="test_reviewer",
            password="test_password",
        )

        self.test_project = Project(
            tag=None,
            automatically_tagged=False,
            description="This is a test project for allocations.",
            pi=self.test_requestor,
            title="Test Project",
            nickname="test_project",
            charge_code="TEST123",
        )

        self.test_project.save()

    def tearDown(self):
        self.test_requestor.delete()
        self.test_reviewer.delete()
        self.test_project.delete()

    @mock.patch.object(
        KeycloakClient,
        "_lookup_group",
        return_value={"attributes": {"has_active_allocation": False}},
    )
    @mock.patch.object(KeycloakClient, "update_project", return_value=None)
    def test_deactivate_active_allocation(self, update_project_mock, lookup_group_mock):
        """Tests whether deactivate_active_allocation()
        updates an active allocation's status to inactive
        """
        test_active_allocation = Allocation(
            project=self.test_project,
            status="active",
            justification="This is a test allocation.",
            requestor=self.test_requestor,
            date_requested=timezone.now(),
            decision_summary="Test decision summary.",
            reviewer=self.test_reviewer,
            date_reviewed=timezone.now(),
            expiration_date=timezone.now(),
            su_requested=100.0,
            start_date=timezone.now(),
            su_allocated=50.0,
            su_used=25.0,
            balance_service_version=2,
        )
        sample_dict = {"has_active_allocation": False}
        sample_dict.get("has_active_allocation")
        tasks._deactivate_allocation(test_active_allocation)

        update_project_mock.assert_called_once_with(
            test_active_allocation.project.charge_code, has_active_allocation="false"
        )
        lookup_group_mock.assert_called_once_with(
            test_active_allocation.project.charge_code
        )

        self.assertEqual(test_active_allocation.status, "inactive")

    @mock.patch.object(
        KeycloakClient,
        "_lookup_group",
        return_value={"attributes": {"has_active_allocation": False}},
    )
    @mock.patch.object(KeycloakClient, "update_project", return_value=None)
    def test_deactivate_inactive_allocation(
        self, update_project_mock, lookup_group_mock
    ):
        """Tests whether deactivate_active_allocation() does not update
        an inactive allocation's status
        """
        test_inactive_allocation = Allocation(
            project=self.test_project,
            status="inactive",
            justification="This is a test allocation.",
            requestor=self.test_requestor,
            date_requested=timezone.now(),
            decision_summary="Test decision summary.",
            reviewer=self.test_reviewer,
            date_reviewed=timezone.now(),
            expiration_date=timezone.now(),
            su_requested=100.0,
            start_date=timezone.now(),
            su_allocated=50.0,
            su_used=25.0,
            balance_service_version=2,
        )
        sample_dict = {"has_active_allocation": False}
        sample_dict.get("has_active_allocation")
        tasks._deactivate_allocation(test_inactive_allocation)

        update_project_mock.assert_called_once_with(
            test_inactive_allocation.project.charge_code, has_active_allocation="false"
        )
        lookup_group_mock.assert_called_once_with(
            test_inactive_allocation.project.charge_code
        )

        self.assertEqual(test_inactive_allocation.status, "inactive")

    def test_deactivate_multiple_allocations_of_projects(self):
        """Tests whether deactivate_multiple_active_allocations_of_projects()
        deactivates all allocations but the latest expiry date one
        """
        test_project_multiple_alloc = Project(
            tag=None,  # You can set the tag if necessary
            automatically_tagged=False,
            description="This is a test project for allocations.",
            pi=self.test_requestor,  # Replace my_user with an actual User instance
            title="Multiple Alloc Project",
            nickname="multiple_alloc_project",
            charge_code="multiple_alloc",  # You can set a unique charge code
        )

        test_project_multiple_alloc.save()

        test_active_allocation_1 = Allocation(
            project=test_project_multiple_alloc,
            status="active",
            justification="later alloc",
            requestor=self.test_requestor,
            date_requested=timezone.now(),
            decision_summary="Test decision summary.",
            reviewer=self.test_reviewer,
            date_reviewed=timezone.now(),
            expiration_date=timezone.now() + timedelta(hours=1, minutes=0),
            su_requested=100.0,
            start_date=timezone.now(),
            su_allocated=50.0,
            su_used=25.0,
            balance_service_version=2,
        )

        test_active_allocation_2 = Allocation(
            project=test_project_multiple_alloc,
            status="active",
            justification="earlier alloc",
            requestor=self.test_requestor,
            date_requested=timezone.now(),
            decision_summary="Test decision summary.",
            reviewer=self.test_reviewer,
            date_reviewed=timezone.now(),
            expiration_date=timezone.now(),
            su_requested=100.0,
            start_date=timezone.now(),
            su_allocated=50.0,
            su_used=25.0,
            balance_service_version=2,
        )

        test_active_allocation_1.save()
        test_active_allocation_2.save()

        tasks.deactivate_multiple_active_allocations_of_projects()

        inactive_allocs = Allocation.objects.filter(project=test_project_multiple_alloc)

        passed_assertions = 0
        for alloc in inactive_allocs:
            if alloc.justification == "earlier alloc":
                self.assertEqual(alloc.status, "inactive")
                passed_assertions += 1
                alloc.delete()
            if alloc.justification == "later alloc":
                self.assertEqual(alloc.status, "active")
                passed_assertions += 1
                alloc.delete()

        test_project_multiple_alloc.delete()

        self.assertEqual(passed_assertions, 2)

    @mock.patch.object(
        KeycloakClient,
        "_lookup_group",
        return_value={"attributes": {"has_active_allocation": True}},
    )
    @mock.patch.object(KeycloakClient, "update_project", return_value=None)
    def test_active_approved_allocations(self, update_project_mock, lookup_group_mock):
        """Tests that active_approved_allocations() changes the status of
        approved allocations to active
        """
        test_approved_allocation = Allocation(
            project=self.test_project,
            status="approved",
            justification="approved alloc",
            requestor=self.test_requestor,
            date_requested=timezone.now(),
            decision_summary="Test decision summary.",
            reviewer=self.test_reviewer,
            date_reviewed=timezone.now(),
            expiration_date=timezone.now(),
            su_requested=100.0,
            start_date=timezone.now(),
            su_allocated=50.0,
            su_used=25.0,
            balance_service_version=2,
        )

        test_approved_allocation.save()
        tasks.active_approved_allocations()

        test_allocations = Allocation.objects.filter(
            project=self.test_project, justification="approved alloc"
        )

        update_project_mock.assert_called_once_with(
            test_approved_allocation.project.charge_code, has_active_allocation="true"
        )
        lookup_group_mock.assert_called_once_with(
            test_approved_allocation.project.charge_code
        )

        for alloc in test_allocations:
            self.assertEqual(alloc.status, "active")
            alloc.delete()

        test_approved_allocation.delete()

    @mock.patch.object(
        KeycloakClient,
        "_lookup_group",
        return_value={"attributes": {"has_active_allocation": False}},
    )
    @mock.patch.object(KeycloakClient, "update_project", return_value=None)
    def test_nonapproved_active_approved_allocation(
        self, update_project_mock, lookup_group_mock
    ):
        """Tests that active_approved_allocations() does not change
        the status of non-approved allocations
        """
        test_nonapproved_allocation = Allocation(
            project=self.test_project,
            status="pending",
            justification="pending alloc",
            requestor=self.test_requestor,
            date_requested=timezone.now(),
            decision_summary="Test decision summary.",
            reviewer=self.test_reviewer,
            date_reviewed=timezone.now(),
            expiration_date=timezone.now() + timedelta(hours=1, minutes=0),
            su_requested=100.0,
            start_date=timezone.now(),
            su_allocated=50.0,
            su_used=25.0,
            balance_service_version=2,
        )

        test_nonapproved_allocation.save()
        tasks.active_approved_allocations()

        test_allocations = Allocation.objects.filter(
            project=self.test_project, justification="pending alloc"
        )

        for alloc in test_allocations:
            self.assertEqual(alloc.status, "pending")
            alloc.delete()

        update_project_mock.assert_not_called()
        lookup_group_mock.assert_not_called()

        test_nonapproved_allocation.delete()


class ExpireTests(TestCase):
    def setUp(self):
        User = get_user_model()

        self.test_requestor = User.objects.create_user(
            username="test_requestor",
            password="test_password",
        )

        self.test_reviewer = User.objects.create_user(
            username="test_reviewer",  # Replace with the desired username
            password="test_password",  # Replace with the desired password
        )

        self.test_project = Project(
            tag=None,  # You can set the tag if necessary
            automatically_tagged=False,
            description="This is a test project for allocations.",
            pi=self.test_requestor,  # Replace my_user with an actual User instance
            title="Test Project",
            nickname="test_project",
            charge_code="TEST123",  # You can set a unique charge code
        )

        self.test_project.save()

    def tearDown(self):
        self.test_requestor.delete()
        self.test_reviewer.delete()
        self.test_project.delete()

    @mock.patch.object(
        KeycloakClient,
        "_lookup_group",
        return_value={"attributes": {"has_active_allocation": False}},
    )
    @mock.patch.object(KeycloakClient, "update_project", return_value=None)
    def test_expire_expired_alloc_allocations(
        self, update_project_mock, lookup_group_mock
    ):
        """Tests that expore_allocations() changes the status
        of all expired allocations to inactive
        """
        test_expired_allocation = Allocation(
            project=self.test_project,
            status="active",
            justification="expired allocation",
            requestor=self.test_requestor,
            date_requested=timezone.now(),
            decision_summary="Test decision summary.",
            reviewer=self.test_reviewer,
            date_reviewed=timezone.now(),
            expiration_date=timezone.now() - timedelta(hours=1, minutes=0),
            su_requested=100.0,
            start_date=timezone.now(),
            su_allocated=50.0,
            su_used=25.0,
            balance_service_version=2,
        )

        test_expired_allocation.save()

        tasks.expire_allocations()

        update_project_mock.assert_called_once_with(
            test_expired_allocation.project.charge_code, has_active_allocation="false"
        )
        lookup_group_mock.assert_called_once_with(
            test_expired_allocation.project.charge_code
        )

        expired_allocations = Allocation.objects.filter(
            project=self.test_project,
            justification="expired allocation",
            expiration_date__lte=timezone.now(),
        )

        for alloc in expired_allocations:
            self.assertTrue(alloc.status, "inactive")
            alloc.delete()

    @mock.patch.object(
        KeycloakClient,
        "_lookup_group",
        return_value={"attributes": {"has_active_allocation": False}},
    )
    @mock.patch.object(KeycloakClient, "update_project", return_value=None)
    def test_expire_non_expired_alloc_allocations(
        self, update_project_mock, lookup_group_mock
    ):
        """Tests that expore_allocations() does not change the status
        of unexpired allocations
        """
        test_expired_allocation = Allocation(
            project=self.test_project,
            status="active",
            justification="non expired allocation",
            requestor=self.test_requestor,
            date_requested=timezone.now(),
            decision_summary="Test decision summary.",
            reviewer=self.test_reviewer,
            date_reviewed=timezone.now(),
            expiration_date=timezone.now() + timedelta(hours=1, minutes=0),
            su_requested=100.0,
            start_date=timezone.now(),
            su_allocated=50.0,
            su_used=25.0,
            balance_service_version=2,
        )

        test_expired_allocation.save()

        tasks.expire_allocations()

        update_project_mock.assert_not_called()
        lookup_group_mock.assert_not_called()

        expired_allocations = Allocation.objects.filter(
            project=self.test_project,
            justification="non expired allocation",
        )

        for alloc in expired_allocations:
            self.assertTrue(alloc.status, "active")
            alloc.delete()


class WarningTests(TestCase):
    def setUp(self):
        self.test_pi = get_user_model().objects.create_user(
            username="test_pi",
            password="test_password",
            email="pi@example.com",
        )
        self.test_project = Project.objects.create(
            automatically_tagged=False,
            description="This is a test project for allocations.",
            pi=self.test_pi,
            title="Test Project",
            nickname="test_project",
            charge_code="TEST123",
        )
        self.test_allocation = Allocation.objects.create(
            project=self.test_project,
            status="active",
            requestor=self.test_pi,
            date_requested=timezone.now(),
            expiration_date=timezone.now() + timedelta(days=5),
            su_requested=100.0,
            start_date=timezone.now(),
            su_allocated=100.0,
        )

    @mock.patch.object(tasks, "send_mail", return_value=1)
    def test_warn_user_for_expiring_allocation(self, send_mail_mock):
        tasks.warn_user_for_expiring_allocation()

        send_mail_mock.assert_called_once()
        self.test_allocation.refresh_from_db()
        self.assertIsNotNone(self.test_allocation.expiration_warning_issued)

    @mock.patch.object(tasks, "send_mail", return_value=1)
    @mock.patch.object(
        tasks, "project_balances", return_value=[{"total": 95.0, "allocated": 100.0}]
    )
    def test_warn_user_for_low_allocations(self, balances_mock, send_mail_mock):
        tasks.warn_user_for_low_allocations()

        send_mail_mock.assert_called_once()
        self.test_allocation.refresh_from_db()
        self.assertIsNotNone(self.test_allocation.low_allocation_warning_issued)

    @mock.patch.object(tasks, "send_mail", side_effect=Exception("SMTP down"))
    @mock.patch.object(
        tasks, "project_balances", return_value=[{"total": 95.0, "allocated": 100.0}]
    )
    def test_warn_user_for_low_allocations_send_failure(
        self, balances_mock, send_mail_mock
    ):
        with self.assertLogs(tasks.LOG, "ERROR") as logs:
            tasks.warn_user_for_low_allocations()

        self.assertIsNotNone(logs.records[0].exc_info)
        self.assertIn("low allocation warning", logs.records[-1].getMessage())
        self.test_allocation.refresh_from_db()
        self.assertIsNone(self.test_allocation.low_allocation_warning_issued)
