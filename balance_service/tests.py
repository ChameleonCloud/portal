import json
import requests
from django.contrib import admin
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from allocations.models import Charge, ChargeBudget
from balance_service.enforcement import exceptions
from balance_service.enforcement.usage_enforcement import (
    GPU_NODE_UIDS_CACHE_KEY,
    REFERENCE_API_URL,
    LeaseEval,
    UsageEnforcer,
    _fetch_gpu_node_uids,
    get_config_value,
)
from balance_service.models import ConfigVariable
from projects.admin import ProjectAdmin
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
    def test_usage_enforcer_stop_charging(
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
    def test_usage_enforcer_check_lease_duration_exceeds_max(
        self, mock_get_config_value, mock_ks
    ):
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
    def test_usage_enforcement_check_lease_update_window(
        self, mock_now, mock_get_config_value, mock_ks
    ):
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
        ed = (self.now + timedelta(days=1, hours=23, minutes=59)).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
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
        ed = (self.now + timedelta(days=27, hours=23, minutes=59)).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
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
    def test_get_config_value_returns_min_value_from_multiple_reservations(
        self, mock_config_var
    ):
        lease = {
            "reservations": [
                {
                    "resource_type": "flavor:instance",
                    "resource_properties": json.dumps({"id": "flavor1"}),
                },
                {
                    "resource_type": "flavor:instance",
                    "resource_properties": json.dumps({"id": "flavor2"}),
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
    def test_get_config_value_returns_value_from_single_reservation(
        self, mock_config_var
    ):
        lease = {
            "reservations": [
                {
                    "resource_type": "flavor:instance",
                    "resource_properties": json.dumps({"id": "flavor1"}),
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
            region=self.lease_eval.region,
        )

    @patch("balance_service.enforcement.usage_enforcement.ConfigVariable")
    def test_get_config_value_returns_default_when_all_values_none(
        self, mock_config_var
    ):
        lease = {
            "reservations": [
                {
                    "resource_type": "flavor:instance",
                    "resource_properties": json.dumps({"id": "flavor1"}),
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

    def test_ConfigVariable_clean_rejects_duplicate_scope(self):
        ConfigVariable.objects.create(key="su_factor", value=1, region="CHI@UC")
        with self.assertRaises(ValidationError):
            ConfigVariable(key="su_factor", value=2, region="chi@uc").clean()
        ConfigVariable(key="su_factor", value=2).clean()
        ConfigVariable(
            key="su_factor", value=2, region="CHI@UC", project_charge_code="CC123"
        ).clean()

    def test_ConfigVarible_get_value_returns_none_when_no_match(self):
        result = ConfigVariable.get_value(
            "lease_limit", flavor_id="f1", username="user1", charge_code="CC123"
        )
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

    def test_ConfigVariable_get_value_returns_match_by_region(self):
        ConfigVariable.objects.create(key="lease_limit", region="CHI@UC", value=40)
        result = ConfigVariable.get_value("lease_limit", region="CHI@UC")
        self.assertAlmostEqual(result, 40)

    def test_ConfigVariable_get_value_region_case_insensitive(self):
        ConfigVariable.objects.create(key="lease_limit", region="CHI@UC", value=40)
        result = ConfigVariable.get_value("lease_limit", region="chi@uc")
        self.assertAlmostEqual(result, 40)

    def test_ConfigVariable_get_value_region_no_match_other_region(self):
        ConfigVariable.objects.create(key="lease_limit", region="CHI@UC", value=40)
        result = ConfigVariable.get_value("lease_limit", region="CHI@TACC")
        self.assertIsNone(result)

    def test_ConfigVariable_get_value_flavor_ranks_above_region(self):
        ConfigVariable.objects.create(key="lease_limit", region="CHI@UC", value=10)
        ConfigVariable.objects.create(key="lease_limit", flavor_id="f1", value=20)
        result = ConfigVariable.get_value(
            "lease_limit", flavor_id="f1", region="CHI@UC"
        )
        self.assertAlmostEqual(result, 20)

    def _make_lease_eval(self, region):
        return LeaseEval(
            project=MagicMock(),
            user=MagicMock(),
            region=region,
            duration=0,
            total_su_factor=0,
            amount=0,
        )

    def test_check_region_end_date_blocks_lease_past_retirement(self):
        region = "DEV@UC"
        retirement = self.now + timezone.timedelta(days=5)
        ConfigVariable.objects.create(
            key="region_end_date",
            region=region,
            value=int(retirement.timestamp()),
        )
        ue = UsageEnforcer(MagicMock())
        lease_end = (self.now + timezone.timedelta(days=10)).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        with self.assertRaises(exceptions.BillingError):
            ue._check_region_end_date(
                {"end_date": lease_end}, self._make_lease_eval(region)
            )

    def test_check_region_end_date_allows_lease_before_retirement(self):
        region = "DEV@UC"
        retirement = self.now + timezone.timedelta(days=5)
        ConfigVariable.objects.create(
            key="region_end_date",
            region=region,
            value=int(retirement.timestamp()),
        )
        ue = UsageEnforcer(MagicMock())
        lease_end = (self.now + timezone.timedelta(days=3)).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        ue._check_region_end_date(
            {"end_date": lease_end}, self._make_lease_eval(region)
        )

    def test_check_region_end_date_other_region_unaffected(self):
        retirement = self.now + timezone.timedelta(days=5)
        ConfigVariable.objects.create(
            key="region_end_date",
            region="DEV@UC",
            value=int(retirement.timestamp()),
        )
        ue = UsageEnforcer(MagicMock())
        lease_end = (self.now + timezone.timedelta(days=10)).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        ue._check_region_end_date(
            {"end_date": lease_end}, self._make_lease_eval("OTHER@REGION")
        )

    def _check_gpu_restriction(self, *hostnames):
        cache.clear()
        self.lease_eval.region = "CHI@UC"
        allocations = [{"hypervisor_hostname": h} for h in hostnames]
        with patch(
            "balance_service.enforcement.usage_enforcement._fetch_gpu_node_uids",
            return_value={"gpu-node"},
        ) as mock_fetch:
            UsageEnforcer(MagicMock())._check_gpu_restriction(
                {"reservations": [{"allocations": allocations}]}, self.lease_eval
            )
        return mock_fetch

    def test_check_gpu_restriction_blocks_gpu_for_project(self):
        ConfigVariable.objects.create(
            key="block_gpu", value=1, project_charge_code="CC123"
        )
        with self.assertRaisesRegex(exceptions.BillingError, "GPU"):
            self._check_gpu_restriction("cpu-node", "gpu-node")

    def test_check_gpu_restriction_allows_non_gpu(self):
        ConfigVariable.objects.create(
            key="block_gpu", value=1, project_charge_code="CC123"
        )
        self._check_gpu_restriction("cpu-node").assert_called_once()

    def test_check_gpu_restriction_project_overrides_global(self):
        ConfigVariable.objects.create(key="block_gpu", value=1)
        ConfigVariable.objects.create(
            key="block_gpu", value=0, project_charge_code="CC123"
        )
        self._check_gpu_restriction("gpu-node").assert_not_called()

    def test_check_gpu_restriction_other_project_unaffected(self):
        ConfigVariable.objects.create(
            key="block_gpu", value=1, project_charge_code="OTHER"
        )
        self._check_gpu_restriction("gpu-node").assert_not_called()

    @patch("balance_service.enforcement.usage_enforcement.requests.get")
    def test_fetch_gpu_node_uids(self, mock_get):
        mock_get.return_value.json.side_effect = [
            {"total": 2, "items": [{"uid": "gpu-1"}]},
            {"total": 2, "items": [{"uid": "gpu-2"}]},
        ]
        self.assertEqual(_fetch_gpu_node_uids(), {"gpu-1", "gpu-2"})
        self.assertEqual(mock_get.call_args.kwargs["params"]["offset"], 1)

    def _project_admin_form(self, block_gpu=None):
        request = RequestFactory().get("/")
        request.user = self.test_requestor
        form_class = ProjectAdmin(Project, admin.site).get_form(request, self.project)
        if block_gpu is None:
            return form_class(instance=self.project)
        data = {
            "title": self.project.title,
            "nickname": self.project.nickname,
            "description": self.project.description,
            "pi": self.project.pi.id,
        }
        if block_gpu:
            data["block_gpu"] = "on"
        form = form_class(data, instance=self.project)
        self.assertTrue(form.is_valid(), form.errors)
        form.save()

    def test_project_admin_block_gpu_checkbox(self):
        rows = ConfigVariable.objects.filter(
            key="block_gpu", project_charge_code="TEST123"
        )
        self._project_admin_form(block_gpu=False)
        self.assertFalse(rows.exists())

        self._project_admin_form(block_gpu=True)
        self.assertEqual(rows.get().value, 1)
        self.assertTrue(self._project_admin_form().initial["block_gpu"])

        self._project_admin_form(block_gpu=False)
        self.assertFalse(rows.exists())
        self.assertFalse(self._project_admin_form().initial["block_gpu"])


AUTH_URL = "https://chi.uc.example.org:5000/v3"
SERVICE_TOKEN = "gAAAAABblazar-service-token"
KS_PROJECT_ID = "a0b86a98b0d343cb948e00689182efd4"
KS_USER_ID = "c631173edec04bb7a0c3f7711153c06c"
LEASE_ID = "2bb8720a-0873-4d97-babf-0d906851a1eb"
RESERVATION_ID = "8f1f0b8c-5c6e-4ea1-a9b5-6e7b0e1b3d42"
TRUST_ID = "5ba3a6d6f3b54dfa8a4f2c0e0b6c9d11"


def _blazar_host(host_id, hypervisor_hostname, node_name, node_type, **extra):
    # A Blazar computehost row merged with its extra capabilities, as returned
    # by the host plugin's get() for each allocation
    return {
        "id": host_id,
        "hypervisor_hostname": hypervisor_hostname,
        "hypervisor_type": "ironic",
        "hypervisor_version": 1,
        "service_name": hypervisor_hostname,
        "vcpus": 48,
        "memory_mb": 196608,
        "local_gb": 240,
        "cpu_info": "baremetal cpu",
        "availability_zone": "nova",
        "status": None,
        "reservable": True,
        "disabled": False,
        "trust_id": TRUST_ID,
        "node_name": node_name,
        "node_type": node_type,
        "su_factor": "1.0",
        **extra,
    }


CPU_HOST = _blazar_host(
    "1", "0b8f6c4e-3d3b-4c1a-9a43-6f4c4a1d2e01", "P3-CPU-001", "compute_skylake"
)
GPU_HOST = _blazar_host(
    "2",
    "5d1f7e2a-8c6b-4e7f-b0a1-2c3d4e5f6a7b",
    "P3-GPU-001",
    "gpu_rtx_6000",
    su_factor="2.0",
)
KVM_HOST = _blazar_host(
    "3",
    "kvm-compute-01",
    "kvm-compute-01",
    "compute_cascadelake",
    hypervisor_type="QEMU",
)


@override_settings(
    OPENSTACK_AUTH_REGIONS={"CHI@UC": AUTH_URL},
    ALLOWED_OPENSTACK_SERVICE_USERS=["blazar"],
    ENFORCEMENT_MAX_LEASE_LENGTH_SECONDS=7 * 24 * 3600,
    ENFORCEMENT_LEASE_UPDATE_WINDOW_SECONDS=2 * 24 * 3600,
)
class BalanceServiceAPITest(TestCase):
    def setUp(self):
        self.now = timezone.now().replace(second=0, microsecond=0)
        self.utcnow = self.now.replace(tzinfo=None)
        self.user = get_user_model().objects.create_user(
            username="alice", email="alice@example.com"
        )
        self.project = Project.objects.create(
            pi=self.user,
            title="API Project",
            nickname="api_project",
            description="Project for balance service API tests.",
            charge_code="CHI-123456",
        )
        self.allocation = self.project.allocations.create(
            status="active",
            requestor=self.user,
            date_requested=self.now,
            start_date=self.now - timedelta(days=1),
            expiration_date=self.now + timedelta(days=30),
            su_requested=1000,
            su_allocated=1000,
        )
        cache.delete(GPU_NODE_UIDS_CACHE_KEY)

        self.service_user = "blazar"
        self.http = MagicMock()
        self.http.get.side_effect = self._http_get
        self.http.post.side_effect = self._http_post
        self.keycloak = MagicMock()
        self.keycloak.get_user_project_role_scopes.return_value = ("admin", [])
        for target, new in [
            ("django.utils.timezone.now", MagicMock(return_value=self.now)),
            ("balance_service.utils.openstack.keystone.requests", self.http),
            ("balance_service.enforcement.usage_enforcement.requests", self.http),
            (
                "balance_service.enforcement.usage_enforcement.KeycloakClient",
                MagicMock(return_value=self.keycloak),
            ),
        ]:
            patcher = patch(target, new)
            patcher.start()
            self.addCleanup(patcher.stop)

    @staticmethod
    def _response(status_code, body):
        response = requests.Response()
        response.status_code = status_code
        response._content = json.dumps(body).encode()
        return response

    def _http_post(self, url, **kwargs):
        token = kwargs["json"]["auth"]["identity"]["token"]["id"]
        if url != f"{AUTH_URL}/auth/tokens" or token != SERVICE_TOKEN:
            return self._response(401, {"error": {"code": 401}})
        user = {"id": "e2f1c0b4", "name": self.service_user}
        return self._response(201, {"token": {"methods": ["token"], "user": user}})

    def _http_get(self, url, **kwargs):
        resources = {
            f"{AUTH_URL}/projects/{KS_PROJECT_ID}": {
                "project": {
                    "id": KS_PROJECT_ID,
                    "name": "CHI-123456",
                    "domain_id": "default",
                    "enabled": True,
                }
            },
            f"{AUTH_URL}/users/{KS_USER_ID}": {
                "user": {
                    "id": KS_USER_ID,
                    "name": "alice",
                    "email": "alice@example.com",
                    "domain_id": "default",
                    "enabled": True,
                }
            },
            f"{REFERENCE_API_URL}/nodes/search": {
                "total": 1,
                "items": [{"uid": GPU_HOST["hypervisor_hostname"]}],
            },
        }
        return self._response(200, resources[url])

    def _reservation(self, resource_type, allocations, **fields):
        return {
            "id": RESERVATION_ID,
            "lease_id": LEASE_ID,
            "resource_id": "c3a4e1f2-7b8d-4e9f-a0b1-c2d3e4f5a6b7",
            "resource_type": resource_type,
            "status": "pending",
            "missing_resources": False,
            "resources_changed": False,
            "created_at": self.utcnow,
            "updated_at": None,
            "allocations": list(allocations),
            **fields,
        }

    def _lease(self, reservations, start=None, days=1):
        start = start or self.utcnow
        return {
            "name": "my-lease",
            "start_date": start,
            "end_date": start + timedelta(days=days),
            "user_id": KS_USER_ID,
            "project_id": KS_PROJECT_ID,
            "trust_id": TRUST_ID,
            "status": "CREATING",
            "reservations": reservations,
        }

    def _host_lease(self, *hosts, **lease):
        reservation = self._reservation(
            "physical:host",
            hosts,
            min=len(hosts),
            max=len(hosts),
            hypervisor_properties="",
            resource_properties='["==", "$node_type", "compute_skylake"]',
            before_end="default",
            on_start="default",
        )
        return self._lease([reservation], **lease)

    def _post(self, endpoint, token=SERVICE_TOKEN, auth_url=AUTH_URL, **body):
        body["context"] = {
            "user_id": KS_USER_ID,
            "project_id": KS_PROJECT_ID,
            "auth_url": auth_url,
            "region_name": "CHI@UC",
        }
        return self.client.post(
            reverse(f"balance_service:{endpoint}"),
            json.dumps(body, default=lambda d: d.isoformat()),
            content_type="application/json",
            headers={"X-Auth-Token": token} if token else {},
        )

    def _get(self, endpoint, *args, **params):
        return self.client.get(
            reverse(f"balance_service:{endpoint}", args=args),
            params,
            headers={"X-Auth-Token": SERVICE_TOKEN, "X-Auth-URL": AUTH_URL},
        )

    def _create_and_extend(self, lease, days):
        self.assertEqual(self._post("check_create", lease=lease).status_code, 204)
        return self._post(
            "check_update",
            current_lease={**lease, "id": LEASE_ID, "status": "ACTIVE"},
            lease={
                "start_date": lease["start_date"],
                "end_date": lease["end_date"] + timedelta(days=days),
                "reservations": lease["reservations"],
            },
        )

    def _assert_denied(self, response, message):
        self.assertEqual(response.status_code, 403)
        self.assertRegex(response.json()["message"], message)

    def test_rejects_missing_token(self):
        lease = self._host_lease(CPU_HOST)
        response = self._post("check_create", token=None, lease=lease)
        self.assertEqual(response.status_code, 403)
        self.http.post.assert_not_called()

    def test_rejects_unlisted_auth_url(self):
        response = self._post(
            "check_create",
            auth_url="https://keystone.example.com:5000/v3",
            lease=self._host_lease(CPU_HOST),
        )
        self.assertEqual(response.status_code, 403)
        self.http.post.assert_not_called()

    def test_rejects_invalid_token(self):
        lease = self._host_lease(CPU_HOST)
        response = self._post("check_create", token="bad", lease=lease)
        self.assertEqual(response.status_code, 403)
        self.http.get.assert_not_called()

    def test_rejects_non_service_user(self):
        self.service_user = "alice"
        response = self._post("check_create", lease=self._host_lease(CPU_HOST))
        self.assertEqual(response.status_code, 403)
        self.http.get.assert_not_called()

    def test_rejects_wrong_method(self):
        response = self.client.get(reverse("balance_service:check_create"))
        self.assertEqual(response.status_code, 405)
        response = self.client.post(
            reverse("balance_service:get_project_allocation", args=[self.project.id])
        )
        self.assertEqual(response.status_code, 405)

    def test_get_project_allocation(self):
        Charge.objects.create(
            allocation=self.allocation,
            user=self.user,
            region_name="CHI@UC",
            resource_id=RESERVATION_ID,
            resource_type="physical:host",
            start_time=self.now - timedelta(hours=2),
            end_time=self.now + timedelta(hours=3),
            hourly_cost=2,
        )
        response = self._get("get_project_allocation", self.project.id)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "id": self.project.id,
                "charge_code": "CHI-123456",
                "used": 4.0,
                "total": 10.0,
                "encumbered": 6.0,
                "allocated": 1000.0,
            },
        )

    def test_get_unknown_project_allocation(self):
        self.assertEqual(self._get("get_project_allocation", 999999).status_code, 404)

    def test_batch_get_project_allocations(self):
        response = self._get(
            "batch_get_project_allocations", projects=f"{self.project.id},999999"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [p["charge_code"] for p in response.json()["projects"]], ["CHI-123456"]
        )

    def test_check_create_records_charge(self):
        response = self._post(
            "check_create", lease=self._host_lease(CPU_HOST, GPU_HOST)
        )
        self.assertEqual(response.status_code, 204)
        charge = Charge.objects.get()
        self.assertEqual(charge.allocation, self.allocation)
        self.assertEqual(charge.user, self.user)
        self.assertEqual(charge.region_name, "CHI@UC")
        self.assertEqual(charge.resource_id, RESERVATION_ID)
        self.assertEqual(charge.resource_type, "physical:host")
        self.assertEqual(charge.hourly_cost, 3)
        self.assertEqual(charge.start_time, self.now)
        self.assertEqual(charge.end_time, self.now + timedelta(days=1))

    def test_check_create_prices_flavor_by_vcpu_share(self):
        ConfigVariable.objects.create(key="su_factor", value=0.96, flavor_id="4")
        flavor = {
            "id": "4",
            "name": "m1.large",
            "vcpus": 4,
            "ram": 8192,
            "disk": 40,
            "swap": "",
            "OS-FLV-EXT-DATA:ephemeral": 0,
            "os-flavor-access:is_public": True,
            "rxtx_factor": 1.0,
            "extra_specs": {},
        }
        reservation = self._reservation(
            "flavor:instance",
            [KVM_HOST, KVM_HOST],
            amount=2,
            vcpus=4,
            memory_mb=8192,
            disk_gb=40,
            affinity=None,
            flavor_id=RESERVATION_ID,
            aggregate_id=7,
            server_group_id=None,
            resource_properties=json.dumps(flavor),
        )
        response = self._post("check_create", lease=self._lease([reservation]))
        self.assertEqual(response.status_code, 204)
        self.assertAlmostEqual(Charge.objects.get().hourly_cost, 2 * 0.96 * 4 / 48)

    def test_check_create_denies_insufficient_balance(self):
        self.allocation.su_allocated = 10
        self.allocation.save()
        response = self._post(
            "check_create", lease=self._host_lease(CPU_HOST, GPU_HOST)
        )
        self._assert_denied(response, r"would spend 72.00 SUs, only 10.00 left")
        self.assertFalse(Charge.objects.exists())

    def test_check_create_denies_member_over_user_budget(self):
        self.keycloak.get_user_project_role_scopes.return_value = ("member", [])
        ChargeBudget.objects.create(user=self.user, project=self.project, su_budget=10)
        response = self._post("check_create", lease=self._host_lease(CPU_HOST))
        self._assert_denied(
            response, r"alice would spend 24.00 SUs, only 10.00 left in user budget"
        )

    def test_check_create_denies_lease_past_allocation_expiration(self):
        self.allocation.expiration_date = self.now + timedelta(hours=12)
        self.allocation.save()
        response = self._post("check_create", lease=self._host_lease(CPU_HOST))
        self._assert_denied(response, "beyond Chameleon project expiration date")

    def test_check_create_denies_lease_over_max_duration(self):
        lease = self._host_lease(CPU_HOST, days=8)
        response = self._post("check_create", lease=lease)
        self._assert_denied(response, "maximum lease duration of 604800 seconds")

    def test_check_create_blocks_gpu_hosts_for_restricted_project(self):
        ConfigVariable.objects.create(
            key="block_gpu", value=1, project_charge_code="CHI-123456"
        )
        response = self._post("check_create", lease=self._host_lease(CPU_HOST))
        self.assertEqual(response.status_code, 204)
        response = self._post(
            "check_create", lease=self._host_lease(CPU_HOST, GPU_HOST)
        )
        self._assert_denied(response, "CHI-123456 is not permitted to reserve GPU")
        self.assertEqual(Charge.objects.count(), 1)

    def test_check_update_extends_charge(self):
        lease = self._host_lease(CPU_HOST, start=self.utcnow - timedelta(hours=1))
        self.assertEqual(self._create_and_extend(lease, days=1).status_code, 204)
        old, new = Charge.objects.order_by("start_time")
        self.assertEqual(old.end_time, self.now)
        self.assertEqual(new.start_time, self.now)
        self.assertEqual(new.end_time, self.now + timedelta(days=1, hours=23))
        self.assertEqual(new.hourly_cost, old.hourly_cost)

    def test_check_update_denies_extension_beyond_balance(self):
        self.allocation.su_allocated = 30
        self.allocation.save()
        lease = self._host_lease(CPU_HOST, start=self.utcnow - timedelta(hours=1))
        response = self._create_and_extend(lease, days=1)
        self._assert_denied(response, r"would spend 24.00 more SUs, only 6.00 left")
        self.assertEqual(Charge.objects.get().end_time, self.now + timedelta(hours=23))

    def test_check_update_denies_extension_outside_window(self):
        lease = self._host_lease(
            CPU_HOST, start=self.utcnow - timedelta(hours=1), days=6
        )
        response = self._create_and_extend(lease, days=1)
        self._assert_denied(response, "only be extended within 172800 seconds")

    def test_check_update_denies_pending_lease_over_max_duration(self):
        lease = self._host_lease(
            CPU_HOST, start=self.utcnow + timedelta(days=3), days=7
        )
        response = self._create_and_extend(lease, days=7)
        self._assert_denied(response, "maximum lease duration of 604800 seconds")

    def test_check_update_allows_running_lease_past_max_duration(self):
        lease = self._host_lease(
            CPU_HOST, start=self.utcnow - timedelta(days=5), days=6
        )
        self.assertEqual(self._create_and_extend(lease, days=2).status_code, 204)

    def test_on_end_stops_charging(self):
        lease = self._host_lease(CPU_HOST, start=self.utcnow - timedelta(hours=1))
        self.assertEqual(self._post("check_create", lease=lease).status_code, 204)
        response = self._post(
            "on_end", lease={**lease, "id": LEASE_ID, "status": "TERMINATING"}
        )
        self.assertEqual(response.status_code, 204)
        self.assertEqual(Charge.objects.get().end_time, self.now)
