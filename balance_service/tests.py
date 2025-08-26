import json
from django.test import TestCase
from django.utils import timezone
from allocations.models import Charge, ChargeBudget
from balance_service.enforcement import exceptions
from balance_service.enforcement.usage_enforcement import UsageEnforcer, get_config_value
from balance_service.models import ConfigVariable
from projects.models import Project
from django.contrib.auth import get_user_model
from unittest.mock import patch, MagicMock
from datetime import timedelta

import logging

from balance_service.utils import su_calculators

LOG = logging.getLogger(__name__)

from .utils.su_calculators import (
    get_used_sus,
    get_total_sus,
    get_active_allocation,
    project_balances,
    calculate_user_total_su_usage,
)


class BalanceServiceTest(TestCase):
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
            charge_code="TEST123",
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
        self.existing_charges = []
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
        self.existing_charges.append(self.charge)
        self.existing_charges.append(
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
        )
        self.existing_charges.append(
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
        )
        self.lease_eval = MagicMock()
        self.lease_eval.user.username = "testuser"
        self.lease_eval.project.charge_code = "CC123"

    @patch("django.utils.timezone.now")  # Mocking timezone.now()
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

    @patch("django.utils.timezone.now")
    def test_project_balances(self, mock_now):
        mock_now.return_value = self.now
        # Test the project_balances function
        balances = project_balances([self.project.id])
        self.assertEqual(len(balances), 1)
        balance = balances[0]
        self.assertEqual(balance["charge_code"], "TEST123")
        self.assertAlmostEqual(balance["used"], 16.0, places=2)
        self.assertAlmostEqual(balance["total"], 41.0, places=2)
        self.assertAlmostEqual(balance["allocated"], 50)
        self.assertAlmostEqual(balance["encumbered"], 25.0, places=2)

    @patch("django.utils.timezone.now")
    def test_calculate_user_total_su_usage(self, mock_now):
        mock_now.return_value = self.now
        # Test calculate_user_total_su_usage function
        user = self.charge.user  # Assuming a user is associated with the charge
        total_su_usage = calculate_user_total_su_usage(user, self.project)
        self.assertAlmostEqual(total_su_usage, 21.0, places=2)

    @patch("django.utils.timezone.now")
    @patch("balance_service.utils.openstack.keystone.KeystoneAPI")
    @patch("balance_service.enforcement.usage_enforcement.KeycloakClient")
    def test_calculate_user_total_su_usage_deleted_leases(
        self, mock_kc, mock_ks, mock_now
    ):
        mock_now.return_value = self.now
        # Test calculate_user_total_su_usage function
        user = self.charge.user  # Assuming a user is associated with the charge

        lease_data = self._lease_data(
            timezone.timedelta(hours=5),
            reservations=3,
            pending_td=timezone.timedelta(hours=5),
        )

        ks_instance = mock_ks.return_value
        ks_instance.get_project.return_value = {"id": 123, "name": "TEST123"}
        ks_instance.get_user.return_value = {"name": "test_requestor"}

        kc_instance = mock_kc.return_value
        kc_instance.get_user_project_role_scopes.return_value = ("admin", None)

        self.allocation.su_allocated = 10000
        self.allocation.save()

        ue = UsageEnforcer(ks_instance)
        # Create charges
        ue.check_usage_against_allocation(lease_data)
        # End charges
        ue.stop_charging(lease_data)

        total_su_usage = calculate_user_total_su_usage(user, self.project)
        self.assertAlmostEqual(total_su_usage, 21.0, places=2)

    @patch("django.utils.timezone.now")
    @patch("balance_service.utils.openstack.keystone.KeystoneAPI")
    def test_usage_enforcer_get_remaining_balance(self, mock_ks, mock_now):
        mock_now.return_value = self.now
        ks_instance = mock_ks.return_value
        ue = UsageEnforcer(ks_instance)
        self.assertAlmostEqual(ue.get_remaining_balance(self.project.id), 9.0, places=2)

    def _lease_data(
        self,
        duration_td,
        reservations=1,
        allocations_per_res=2,
        su_factor=3,
        include_update=False,
        update_reservations=1,
        update_allocations_per_res=2,
        update_su_factor=3,
        update_extend=0,
        pending_td=timezone.timedelta(days=0),
    ):
        lease_start = (self.now + pending_td).strftime("%Y-%m-%d %H:%M:%S")
        lease_end = (self.now + pending_td + duration_td).strftime("%Y-%m-%d %H:%M:%S")

        update_start = (self.now + pending_td).strftime("%Y-%m-%d %H:%M:%S")
        update_end = (
            self.now + pending_td + duration_td + timezone.timedelta(days=update_extend)
        ).strftime("%Y-%m-%d %H:%M:%S")

        if not include_update:
            return {
                "context": {
                    "user_id": "c631173e-dec0-4bb7-a0c3-f7711153c06c",
                    "project_id": "a0b86a98-b0d3-43cb-948e-00689182efd4",
                    "auth_url": "https://api.example.com:5000/v3",
                    "region_name": "RegionOne",
                },
                "lease": {
                    "start_date": lease_start,
                    "end_date": lease_end,
                    "project_id": "a0b86a98-b0d3-43cb-948e-00689182efd4",
                    "user_id": "c631173e-dec0-4bb7-a0c3-f7711153c06c",
                    "name": "my_lease",
                    "reservations": [
                        {
                            "resource_type": "physical:host",
                            "min": allocations_per_res,
                            "max": allocations_per_res,
                            "hypervisor_properties": "[]",
                            "resource_properties": '["==", "$availability_zone", "az1"]',
                            "id": str(j),
                            "allocations": [
                                {
                                    "id": str(i),
                                    "hypervisor_hostname": "32af5a7a-e7a3-4883-a643-828e3f63bf54",
                                    "extra": {"availability_zone": "az1"},
                                    "su_factor": su_factor,
                                }
                                for i in range(allocations_per_res)
                            ],
                        }
                        for j in range(reservations)
                    ],
                },
            }
        else:
            return {
                "context": {
                    "user_id": "c631173e-dec0-4bb7-a0c3-f7711153c06c",
                    "project_id": "a0b86a98-b0d3-43cb-948e-00689182efd4",
                    "auth_url": "https://api.example.com:5000/v3",
                    "region_name": "RegionOne",
                },
                "current_lease": {
                    "start_date": lease_start,
                    "end_date": lease_end,
                    "project_id": "a0b86a98-b0d3-43cb-948e-00689182efd4",
                    "user_id": "c631173e-dec0-4bb7-a0c3-f7711153c06c",
                    "name": "my_lease",
                    "reservations": [
                        {
                            "resource_type": "physical:host",
                            "min": allocations_per_res,
                            "max": allocations_per_res,
                            "hypervisor_properties": "[]",
                            "resource_properties": '["==", "$availability_zone", "az1"]',
                            "id": str(j),
                            "allocations": [
                                {
                                    "id": str(i),
                                    "hypervisor_hostname": "32af5a7a-e7a3-4883-a643-828e3f63bf54",
                                    "extra": {"availability_zone": "az1"},
                                    "su_factor": su_factor,
                                }
                                for i in range(allocations_per_res)
                            ],
                        }
                        for j in range(reservations)
                    ],
                },
                "lease": {
                    "start_date": update_start,
                    "end_date": update_end,
                    "project_id": "a0b86a98-b0d3-43cb-948e-00689182efd4",
                    "user_id": "c631173e-dec0-4bb7-a0c3-f7711153c06c",
                    "name": "my_lease",
                    "reservations": [
                        {
                            "resource_type": "physical:host",
                            "min": update_allocations_per_res,
                            "max": update_allocations_per_res,
                            "hypervisor_properties": "[]",
                            "resource_properties": '["==", "$availability_zone", "az1"]',
                            "id": str(j),
                            "allocations": [
                                {
                                    "id": str(i),
                                    "hypervisor_hostname": "32af5a7a-e7a3-4883-a643-828e3f63bf54",
                                    "extra": {"availability_zone": "az1"},
                                    "su_factor": update_su_factor,
                                }
                                for i in range(update_allocations_per_res)
                            ],
                        }
                        for j in range(update_reservations)
                    ],
                },
            }

    @patch("django.utils.timezone.now")
    @patch("balance_service.utils.openstack.keystone.KeystoneAPI")
    def test_usage_enforcer_get_lease_duration_hrs(self, mock_ks, mock_now):
        mock_now.return_value = self.now
        ks_instance = mock_ks.return_value
        ue = UsageEnforcer(ks_instance)

        self.assertAlmostEqual(
            ue.get_lease_duration_hrs(
                self._lease_data(timezone.timedelta(hours=23, minutes=30))["lease"]
            ),
            23.5,
            places=2,
        )

    @patch("django.utils.timezone.now")
    @patch("balance_service.utils.openstack.keystone.KeystoneAPI")
    @patch("balance_service.enforcement.usage_enforcement.KeycloakClient")
    @patch.object(UsageEnforcer, "_check_lease_duration")
    @patch.object(UsageEnforcer, "_check_lease_update_window")
    def test_usage_enforcer_check_usage_against_allocation_insufficient_sus(
        self, mock_uw, mock_ld, mock_kc, mock_ks, mock_now
    ):
        mock_now.return_value = self.now

        ks_instance = mock_ks.return_value
        ks_instance.get_project.return_value = {"name": "TEST123"}
        ks_instance.get_user.return_value = {"name": "test_requestor"}

        kc_instance = mock_kc.return_value
        kc_instance.get_user_project_role_scopes.return_value = ("admin", None)

        ue = UsageEnforcer(ks_instance)

        with self.assertRaisesRegex(
            exceptions.BillingError, r"would spend 30.00 SUs.*only 9.00 left"
        ):
            ue.check_usage_against_allocation(
                self._lease_data(timezone.timedelta(hours=5))
            )

    @patch("django.utils.timezone.now")
    @patch("balance_service.utils.openstack.keystone.KeystoneAPI")
    @patch("balance_service.enforcement.usage_enforcement.KeycloakClient")
    @patch.object(UsageEnforcer, "_check_lease_duration")
    @patch.object(UsageEnforcer, "_check_lease_update_window")
    def test_usage_enforcer_check_usage_against_allocation_past_expiration(
        self, mock_uw, mock_ld, mock_kc, mock_ks, mock_now
    ):
        mock_now.return_value = self.now

        ks_instance = mock_ks.return_value
        ks_instance.get_project.return_value = {"name": "TEST123"}
        ks_instance.get_user.return_value = {"name": "test_requestor"}

        kc_instance = mock_kc.return_value
        kc_instance.get_user_project_role_scopes.return_value = ("admin", None)

        ue = UsageEnforcer(ks_instance)
        # Add a lot of SUs for really big lease upcoming
        self.allocation.su_allocated = 10000
        self.allocation.save()
        with self.assertRaises(exceptions.LeasePastExpirationError):
            ue.check_usage_against_allocation(
                self._lease_data(timezone.timedelta(days=35))
            )

    @patch("django.utils.timezone.now")
    @patch("balance_service.utils.openstack.keystone.KeystoneAPI")
    @patch("balance_service.enforcement.usage_enforcement.KeycloakClient")
    @patch.object(UsageEnforcer, "_check_lease_duration")
    @patch.object(UsageEnforcer, "_check_lease_update_window")
    def test_usage_enforcer_check_usage_against_allocation_charges(
        self, mock_uw, mock_ld, mock_kc, mock_ks, mock_now
    ):
        mock_now.return_value = self.now

        ks_instance = mock_ks.return_value
        ks_instance.get_project.return_value = {"name": "TEST123"}
        ks_instance.get_user.return_value = {"name": "test_requestor"}

        kc_instance = mock_kc.return_value
        kc_instance.get_user_project_role_scopes.return_value = ("admin", None)

        ue = UsageEnforcer(ks_instance)

        self.allocation.su_allocated = 10000
        self.allocation.save()

        ue.check_usage_against_allocation(self._lease_data(timezone.timedelta(hours=5)))
        new_charges = []
        for c in Charge.objects.all():
            if c not in self.existing_charges:
                new_charges.append(c)
        self.assertEqual(len(new_charges), 1)
        self.assertEqual(get_total_sus(new_charges[0]), 30)

    @patch("django.utils.timezone.now")
    @patch("balance_service.utils.openstack.keystone.KeystoneAPI")
    @patch("balance_service.enforcement.usage_enforcement.KeycloakClient")
    @patch.object(UsageEnforcer, "_check_lease_duration")
    @patch.object(UsageEnforcer, "_check_lease_update_window")
    def test_usage_enforcer_check_usage_against_allocation_multiple_reservations(
        self, mock_uw, mock_ld, mock_kc, mock_ks, mock_now
    ):
        mock_now.return_value = self.now

        ks_instance = mock_ks.return_value
        ks_instance.get_project.return_value = {"name": "TEST123"}
        ks_instance.get_user.return_value = {"name": "test_requestor"}

        kc_instance = mock_kc.return_value
        kc_instance.get_user_project_role_scopes.return_value = ("admin", None)

        ue = UsageEnforcer(ks_instance)

        self.allocation.su_allocated = 10000
        self.allocation.save()

        ue.check_usage_against_allocation(
            self._lease_data(
                timezone.timedelta(hours=5),
                reservations=3,
            )
        )
        new_charges = []
        for c in Charge.objects.all():
            if c not in self.existing_charges:
                new_charges.append(c)
        self.assertEqual(len(new_charges), 3)

    @patch("django.utils.timezone.now")
    @patch("balance_service.utils.openstack.keystone.KeystoneAPI")
    @patch("balance_service.enforcement.usage_enforcement.KeycloakClient")
    @patch.object(UsageEnforcer, "_check_lease_duration")
    @patch.object(UsageEnforcer, "_check_lease_update_window")
    def test_usage_enforcer_check_usage_against_allocation_project_budget(
        self, mock_ld, mock_uw, mock_kc, mock_ks, mock_now
    ):
        mock_now.return_value = self.now

        ks_instance = mock_ks.return_value
        ks_instance.get_project.return_value = {"name": "TEST123"}
        ks_instance.get_user.return_value = {"name": "test_requestor"}

        kc_instance = mock_kc.return_value
        kc_instance.get_user_project_role_scopes.return_value = ("admin", None)

        ue = UsageEnforcer(ks_instance)

        self.allocation.su_allocated = 10000
        self.allocation.save()

        kc_instance.get_user_project_role_scopes.return_value = ("member", None)

        self.project.default_su_budget = 50
        self.project.save()
        # User has used 21 SUs already, 50-21 = 29 left
        with self.assertRaisesRegex(
            exceptions.BillingError, "60.00 SUs.*29.00 left.*budget"
        ):
            ue.check_usage_against_allocation(
                self._lease_data(
                    timezone.timedelta(hours=5),
                    reservations=2,
                )
            )

    @patch("django.utils.timezone.now")
    @patch("balance_service.utils.openstack.keystone.KeystoneAPI")
    @patch("balance_service.enforcement.usage_enforcement.KeycloakClient")
    @patch.object(UsageEnforcer, "_check_lease_duration")
    @patch.object(UsageEnforcer, "_check_lease_update_window")
    def test_usage_enforcer_check_usage_against_allocation_user_budget(
        self, mock_ld, mock_uw, mock_kc, mock_ks, mock_now
    ):
        mock_now.return_value = self.now

        ks_instance = mock_ks.return_value
        ks_instance.get_project.return_value = {"name": "TEST123"}
        ks_instance.get_user.return_value = {"name": "test_requestor"}

        kc_instance = mock_kc.return_value
        kc_instance.get_user_project_role_scopes.return_value = ("admin", None)

        ue = UsageEnforcer(ks_instance)

        self.allocation.su_allocated = 10000
        self.allocation.save()

        kc_instance.get_user_project_role_scopes.return_value = ("member", None)

        ChargeBudget.objects.create(
            user=self.test_requestor, project=self.project, su_budget=25
        )
        with self.assertRaisesRegex(
            exceptions.BillingError, "60.00 SUs.*4.00 left.*budget"
        ):
            ue.check_usage_against_allocation(
                self._lease_data(
                    timezone.timedelta(hours=5),
                    reservations=2,
                )
            )

    @patch("django.utils.timezone.now")
    @patch("balance_service.utils.openstack.keystone.KeystoneAPI")
    @patch("balance_service.enforcement.usage_enforcement.KeycloakClient")
    @patch.object(UsageEnforcer, "_check_lease_duration")
    @patch.object(UsageEnforcer, "_check_lease_update_window")
    def test_usage_enforcer_check_usage_against_allocation_update_no_old_charges(
        self, mock_ld, mock_uw, mock_kc, mock_ks, mock_now
    ):
        mock_now.return_value = self.now

        ks_instance = mock_ks.return_value
        ks_instance.get_project.return_value = {"name": "TEST123"}
        ks_instance.get_user.return_value = {"name": "test_requestor"}

        kc_instance = mock_kc.return_value
        kc_instance.get_user_project_role_scopes.return_value = ("admin", None)

        ue = UsageEnforcer(ks_instance)

        self.allocation.su_allocated = 10000
        self.allocation.save()

        with self.assertRaisesRegex(exceptions.BillingError, "Wrong number of ongoing"):
            ue.check_usage_against_allocation_update(
                self._lease_data(
                    timezone.timedelta(hours=5), include_update=True, update_extend=1
                )
            )

    @patch("django.utils.timezone.now")
    @patch("balance_service.utils.openstack.keystone.KeystoneAPI")
    @patch("balance_service.enforcement.usage_enforcement.KeycloakClient")
    @patch.object(UsageEnforcer, "_check_lease_duration")
    @patch.object(UsageEnforcer, "_check_lease_update_window")
    def test_usage_enforcer_check_usage_against_allocation_update_charges(
        self, mock_ld, mock_uw, mock_kc, mock_ks, mock_now
    ):
        mock_now.return_value = self.now

        ks_instance = mock_ks.return_value
        ks_instance.get_project.return_value = {"name": "TEST123"}
        ks_instance.get_user.return_value = {"name": "test_requestor"}

        kc_instance = mock_kc.return_value
        kc_instance.get_user_project_role_scopes.return_value = ("admin", None)

        ue = UsageEnforcer(ks_instance)

        self.allocation.su_allocated = 10000
        self.allocation.save()

        lease_data = self._lease_data(
            timezone.timedelta(hours=5),
            reservations=3,
            include_update=True,
            update_extend=1,
            update_reservations=3,
        )
        updated_data = lease_data.pop("lease")
        lease_data["lease"] = lease_data.pop("current_lease")

        # Create charges
        ue.check_usage_against_allocation(lease_data)
        new_charges = []
        for c in Charge.objects.all():
            if c not in self.existing_charges:
                new_charges.append(c)
        self.assertEqual(len(new_charges), 3)

        lease_data["current_lease"] = lease_data["lease"]
        lease_data["lease"] = updated_data
        ue.check_usage_against_allocation_update(lease_data)

        update_new_charges = []
        for c in Charge.objects.all():
            # Get new active charges
            if c not in self.existing_charges and c.end_time > self.now:
                update_new_charges.append(c)
        self.assertEqual(len(new_charges), len(update_new_charges))

    @patch("django.utils.timezone.now")
    @patch("balance_service.utils.openstack.keystone.KeystoneAPI")
    @patch("balance_service.enforcement.usage_enforcement.KeycloakClient")
    @patch.object(UsageEnforcer, "_check_lease_duration")
    @patch.object(UsageEnforcer, "_check_lease_update_window")
    def test_usage_enforcer_check_usage_against_allocation_update_insufficient_sus_extend(
        self, mock_ld, mock_uw, mock_kc, mock_ks, mock_now
    ):
        mock_now.return_value = self.now

        ks_instance = mock_ks.return_value
        ks_instance.get_project.return_value = {"name": "TEST123"}
        ks_instance.get_user.return_value = {"name": "test_requestor"}

        kc_instance = mock_kc.return_value
        kc_instance.get_user_project_role_scopes.return_value = ("admin", None)

        ue = UsageEnforcer(ks_instance)

        # New lease uses 432 = 24*3*2*3 (time * res * allocs * su_factor)
        # existing charges use 41
        self.allocation.su_allocated = 473
        self.allocation.save()

        lease_data = self._lease_data(
            timezone.timedelta(days=1),
            reservations=3,
            include_update=True,
            update_extend=1,
            update_reservations=3,
        )
        updated_data = lease_data.pop("lease")
        lease_data["lease"] = lease_data.pop("current_lease")

        # Create charges
        ue.check_usage_against_allocation(lease_data)
        new_charges = []
        for c in Charge.objects.all():
            if c not in self.existing_charges:
                new_charges.append(c)
        self.assertEqual(len(new_charges), 3)

        lease_data["current_lease"] = lease_data["lease"]
        lease_data["lease"] = updated_data

        with self.assertRaisesRegex(
            exceptions.BillingError, "432.00 more SUs, only 0.00 left"
        ):
            ue.check_usage_against_allocation_update(lease_data)

    @patch("django.utils.timezone.now")
    @patch("balance_service.utils.openstack.keystone.KeystoneAPI")
    @patch("balance_service.enforcement.usage_enforcement.KeycloakClient")
    @patch.object(UsageEnforcer, "_check_lease_duration")
    @patch.object(UsageEnforcer, "_check_lease_update_window")
    def test_usage_enforcer_check_usage_against_allocation_update_insufficient_sus_add_hosts(
        self, mock_ld, mock_uw, mock_kc, mock_ks, mock_now
    ):
        mock_now.return_value = self.now

        ks_instance = mock_ks.return_value
        ks_instance.get_project.return_value = {"name": "TEST123"}
        ks_instance.get_user.return_value = {"name": "test_requestor"}

        kc_instance = mock_kc.return_value
        kc_instance.get_user_project_role_scopes.return_value = ("admin", None)

        ue = UsageEnforcer(ks_instance)

        # New lease uses 432 = 24*3*2*3 (time * res * allocs * su_factor)
        # existing charges use 41
        self.allocation.su_allocated = 473
        self.allocation.save()

        lease_data = self._lease_data(
            timezone.timedelta(days=1),
            reservations=3,
            include_update=True,
            update_reservations=6,
        )
        updated_data = lease_data.pop("lease")
        lease_data["lease"] = lease_data.pop("current_lease")

        # Create charges
        ue.check_usage_against_allocation(lease_data)
        new_charges = []
        for c in Charge.objects.all():
            if c not in self.existing_charges:
                new_charges.append(c)
        self.assertEqual(len(new_charges), 3)

        lease_data["current_lease"] = lease_data["lease"]
        lease_data["lease"] = updated_data

        with self.assertRaisesRegex(
            exceptions.BillingError, "432.00 more SUs, only 0.00 left"
        ):
            ue.check_usage_against_allocation_update(lease_data)

    @patch("django.utils.timezone.now")
    @patch("balance_service.utils.openstack.keystone.KeystoneAPI")
    @patch("balance_service.enforcement.usage_enforcement.KeycloakClient")
    @patch.object(UsageEnforcer, "_check_lease_duration")
    @patch.object(UsageEnforcer, "_check_lease_update_window")
    def test_usage_enforcer_stop_charging(self, mock_ld, mock_uw, mock_kc, mock_ks, mock_now):
        mock_now.return_value = self.now

        ks_instance = mock_ks.return_value
        ks_instance.get_project.return_value = {"name": "TEST123"}
        ks_instance.get_user.return_value = {"name": "test_requestor"}

        kc_instance = mock_kc.return_value
        kc_instance.get_user_project_role_scopes.return_value = ("admin", None)

        ue = UsageEnforcer(ks_instance)

        self.allocation.su_allocated = 10000
        self.allocation.save()

        lease_data = self._lease_data(
            timezone.timedelta(hours=5),
            reservations=3,
        )

        # Create charges
        ue.check_usage_against_allocation(lease_data)
        # End charges
        ue.stop_charging(lease_data)
        # Ensure all charges end now, when stopped
        for c in Charge.objects.all():
            if c not in self.existing_charges:
                self.assertEqual(c.end_time, self.now)

    @patch("django.utils.timezone.now")
    @patch("balance_service.utils.openstack.keystone.KeystoneAPI")
    @patch("balance_service.enforcement.usage_enforcement.KeycloakClient")
    @patch.object(UsageEnforcer, "_check_lease_duration")
    @patch.object(UsageEnforcer, "_check_lease_update_window")
    def test_usage_enforcer_check_usage_against_allocation_charges_flavor_res(
        self, mock_ld, mock_uw, mock_kc, mock_ks, mock_now
    ):
        mock_now.return_value = self.now

        ks_instance = mock_ks.return_value
        ks_instance.get_project.return_value = {"name": "TEST123"}
        ks_instance.get_user.return_value = {"name": "test_requestor"}

        kc_instance = mock_kc.return_value
        kc_instance.get_user_project_role_scopes.return_value = ("admin", None)

        ue = UsageEnforcer(ks_instance)

        self.allocation.su_allocated = 10000
        self.allocation.save()
        # Overwrite some lease data for one-off flavor use
        lease_data = self._lease_data(
            timezone.timedelta(hours=5),
            reservations=1,
            allocations_per_res=1,
        )
        lease_data["lease"]["reservations"][0]["resource_type"] = "flavor:instance"
        lease_data["lease"]["reservations"][0]["vcpus"] = 10
        lease_data["lease"]["reservations"][0]["allocations"][0]["vcpus"] = 100

        ue.check_usage_against_allocation(lease_data)
        new_charges = []
        for c in Charge.objects.all():
            if c not in self.existing_charges:
                new_charges.append(c)
        self.assertEqual(len(new_charges), 1)
        # su_factor = 3
        # 5 hrs * 3 su_factor * 10/100 vcpus = 1.5
        self.assertAlmostEqual(get_total_sus(new_charges[0]), 1.5)

    @patch("django.utils.timezone.now")
    @patch("balance_service.utils.openstack.keystone.KeystoneAPI")
    @patch("balance_service.enforcement.usage_enforcement.KeycloakClient")
    @patch.object(UsageEnforcer, "_check_lease_duration")
    @patch.object(UsageEnforcer, "_check_lease_update_window")
    def test_usage_enforcer_stop_charging_pending_lease(
        self, mock_ld, mock_uw, mock_kc, mock_ks, mock_now
    ):
        mock_now.return_value = self.now

        ks_instance = mock_ks.return_value
        ks_instance.get_project.return_value = {"id": 123, "name": "TEST123"}

        ks_instance.get_user.return_value = {"name": "test_requestor"}

        kc_instance = mock_kc.return_value
        kc_instance.get_user_project_role_scopes.return_value = ("admin", None)

        ue = UsageEnforcer(ks_instance)

        self.allocation.su_allocated = 10000
        self.allocation.save()
        lease_data = self._lease_data(
            timezone.timedelta(hours=5),
            reservations=3,
            pending_td=timezone.timedelta(hours=5),
        )

        # Create charges
        ue.check_usage_against_allocation(lease_data)
        # End charges
        ue.stop_charging(lease_data)
        # mock_now.return_value = self.now + timezone.timedelta(hours=24)

        # Ensure all charges end now, when stopped
        for c in Charge.objects.all():
            if c not in self.existing_charges:
                self.assertEqual(su_calculators.get_total_sus(c), 0)
                self.assertEqual(c.end_time, self.now)

    @patch("balance_service.utils.openstack.keystone.KeystoneAPI")
    @patch("balance_service.enforcement.usage_enforcement.get_config_value")
    def test_usage_enforcer_check_lease_duration_exceeds_max(self, mock_get_config_value, mock_ks):
        ks_instance = mock_ks.return_value
        mock_get_config_value.return_value = 60 * 60 * 24 * 7  # 7 days
        sd = (self.now).strftime("%Y-%m-%d %H:%M:%S")
        duration_td = timedelta(days=6, hours=23, minutes=59)
        ed = (self.now + duration_td).strftime("%Y-%m-%d %H:%M:%S")

        ue = UsageEnforcer(ks_instance)
        ue._check_lease_duration(
            {},
            {},
            start_date_str=sd,
            end_date_str=ed,
        )

        duration_td = timedelta(days=7, minutes=1)
        ed = (self.now + duration_td).strftime("%Y-%m-%d %H:%M:%S")

        with self.assertRaises(exceptions.MaxLeaseDurationError):
            ue._check_lease_duration(
                {},
                {},
                start_date_str=sd,
                end_date_str=ed,
            )

    @patch("balance_service.utils.openstack.keystone.KeystoneAPI")
    @patch("balance_service.enforcement.usage_enforcement.get_config_value")
    @patch("django.utils.timezone.now")  # Mocking timezone.now()
    def test_usage_enforcement_check_lease_update_window(self, mock_now, mock_get_config_value, mock_ks):
        permitted_lease_duration = 7

        def fake_get_config_value(key, lease, lease_eval, default):
            if key == "max_lease_length":
                return 60 * 60 * 24 * permitted_lease_duration
            elif key == "lease_update_window":
                return 60 * 60 * 24 * 2
            return None

        ks_instance = mock_ks.return_value
        mock_get_config_value.side_effect = fake_get_config_value

        # Extend a lease for 7 days within the update window
        mock_now.return_value = self.now
        sd = self.now.strftime("%Y-%m-%d %H:%M:%S")
        ed = (self.now + timedelta(days=1, hours=23, minutes=59)).strftime("%Y-%m-%d %H:%M:%S")
        new_ed = (self.now + timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
        ue = UsageEnforcer(ks_instance)
        ue._check_lease_update_window(
            {
                "start_date": sd,
                "end_date": ed,
            },
            {
                "start_date": sd,
                "end_date": new_ed,
            },
            None,
        )

        # Extend a 4 week lease lease for 7 days within 8 day window
        permitted_lease_duration = 28
        mock_now.return_value = self.now + timedelta(days=20)
        sd = self.now.strftime("%Y-%m-%d %H:%M:%S")
        ed = (self.now + timedelta(days=27, hours=23, minutes=59)).strftime("%Y-%m-%d %H:%M:%S")
        new_ed = (self.now + timedelta(days=35)).strftime("%Y-%m-%d %H:%M:%S")
        ue = UsageEnforcer(ks_instance)
        ue._check_lease_update_window(
            {
                "start_date": sd,
                "end_date": ed,
            },
            {
                "start_date": sd,
                "end_date": new_ed,
            },
            None,
        )

        with self.assertRaises(exceptions.MaxLeaseUpdateWindowException):
            permitted_lease_duration = 7
            mock_now.return_value = self.now
            sd = self.now.strftime("%Y-%m-%d %H:%M:%S")
            ed = (self.now + timedelta(days=3)).strftime("%Y-%m-%d %H:%M:%S")
            new_ed = (self.now + timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
            ue = UsageEnforcer(ks_instance)
            ue._check_lease_update_window(
                {
                    "start_date": sd,
                    "end_date": ed,
                },
                {
                    "start_date": sd,
                    "end_date": new_ed,
                },
                None,
            )

    @patch("balance_service.enforcement.usage_enforcement.ConfigVariable")
    def test_get_config_value_returns_min_value_from_multiple_reservations(self, mock_config_var):
        lease = {
            "reservations": [
                {
                    "resource_type": "flavor:instance",
                    "resource_properties": json.dumps({"flavor_id": "flavor1"}),
                },
                {
                    "resource_type": "flavor:instance",
                    "resource_properties": json.dumps({"flavor_id": "flavor2"}),
                },
            ]
        }

        # Configure mock return values
        mock_config_var.get_value.side_effect = [50, 20]

        result = get_config_value("limit", lease, self.lease_eval, default=999)

        # It should return the minimum value
        self.assertEqual(result, 20)
        self.assertEqual(mock_config_var.get_value.call_count, 2)

    @patch("balance_service.enforcement.usage_enforcement.ConfigVariable")
    def test_get_config_value_returns_value_from_single_reservation(self, mock_config_var):
        lease = {
            "reservations": [
                {
                    "resource_type": "flavor:instance",
                    "resource_properties": json.dumps({"flavor_id": "flavor1"}),
                }
            ]
        }

        mock_config_var.get_value.return_value = 42

        result = get_config_value("limit", lease, self.lease_eval, default=999)

        self.assertEqual(result, 42)
        mock_config_var.get_value.assert_called_once_with(
            "limit",
            flavor_id="flavor1",
            username="testuser",
            charge_code="CC123",
        )

    @patch("balance_service.enforcement.usage_enforcement.ConfigVariable")
    def test_get_config_value_returns_default_when_all_values_none(self, mock_config_var):
        lease = {
            "reservations": [
                {
                    "resource_type": "flavor:instance",
                    "resource_properties": json.dumps({"flavor_id": "flavor1"}),
                }
            ]
        }

        mock_config_var.get_value.return_value = None

        result = get_config_value("limit", lease, self.lease_eval, default=1234)

        self.assertEqual(result, 1234)

    @patch("balance_service.enforcement.usage_enforcement.ConfigVariable")
    def test_get_config_value_physical_host(self, mock_config_var):
        lease = {
            "reservations": [
                {
                    "resource_type": "physical:host",
                    "resource_properties": "[]",
                }
            ]
        }

        mock_config_var.get_value.return_value = None

        result = get_config_value("limit", lease, self.lease_eval, default=1234)

        self.assertEqual(result, 1234)

    def test_ConfigVarible_get_value_returns_none_when_no_match(self):
        result = ConfigVariable.get_value("lease_limit", flavor_id="f1", username="user1", charge_code="CC123")
        self.assertIsNone(result)

    def test_ConfigVarible_get_value_returns_match_by_flavor(self):
        ConfigVariable.objects.create(
            key="lease_limit",
            flavor_id="f1",
            value="10",
        )
        result = ConfigVariable.get_value("lease_limit", flavor_id="f1")
        self.assertAlmostEqual(result, 10)

    def test_ConfigVarible_get_value_returns_match_by_project(self):
        ConfigVariable.objects.create(
            key="lease_limit",
            project_charge_code="CC123",
            value=20,
        )
        result = ConfigVariable.get_value("lease_limit", charge_code="CC123")
        self.assertAlmostEqual(result, 20)

    def test_ConfigVarible_get_value_returns_match_by_username(self):
        ConfigVariable.objects.create(
            key="lease_limit",
            username="alice",
            value=30,
        )
        result = ConfigVariable.get_value("lease_limit", username="alice")
        self.assertAlmostEqual(result, 30)

    def test_ConfigVarible_get_value_ranks_user_over_project_over_flavor(self):
        # Create one for each specificity
        ConfigVariable.objects.create(
            key="lease_limit",
            flavor_id="f1",
            value=1234,
        )
        ConfigVariable.objects.create(
            key="lease_limit",
            project_charge_code="CC123",
            value=2345,
        )
        ConfigVariable.objects.create(
            key="lease_limit",
            username="alice",
            value=3456,
        )
        ConfigVariable.objects.create(
            key="window_duration",
            flavor_id="f1",
            username="alice",
            project_charge_code="CC123",
            value=4567,
        )

        # Should return the most specific (username) when all match
        result = ConfigVariable.get_value(
            "lease_limit",
            flavor_id="f1",
            username="alice",
            charge_code="CC123",
        )
        self.assertAlmostEqual(result, 3456)

        # If username doesn’t match, should fall back to project
        result = ConfigVariable.get_value(
            "lease_limit",
            flavor_id="f1",
            username="bob",
            charge_code="CC123",
        )
        self.assertAlmostEqual(result, 2345)

        # If project doesn’t match, should fall back to flavor
        result = ConfigVariable.get_value(
            "lease_limit",
            flavor_id="f1",
            username="bob",
            charge_code="DIFFERENT",
        )
        self.assertAlmostEqual(result, 1234)
