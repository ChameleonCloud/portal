# Copyright (c) 2018 University of Chicago
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import datetime
import collections
import logging
import pytz

from django.contrib.auth import get_user_model
from django.utils import timezone
from balance_service.enforcement import exceptions
from balance_service.utils import su_calculators
from projects.models import Project
from allocations.models import Charge

LOG = logging.getLogger(__name__)

DEFAULT_SU_FACTOR = 1.0

LeaseEval = collections.namedtuple(
    "LeaseEval", ["project", "user", "region", "duration", "total_su_factor", "amount"]
)

TMP_RESOURCE_ID_PREFIX = "TMP"
TMP_RESOURCE_ID = "{prefix}/{project_id}/{user_id}/{start_date}/{name}"


def dt_hours(dt):
    return dt.total_seconds() / 3600.0


def debug_lease_reservations(msg, lease):
    for r in lease["reservations"]:
        _r = r.copy()
        _r["num_allocations"] = len(_r.pop("allocations"))
        LOG.debug(f"{msg}: {_r}")


class UsageEnforcer(object):
    def __init__(self, keystone_api_client):
        self.keystone_api = keystone_api_client

    def get_remaining_balance(self, project_id):
        balances = su_calculators.project_balances([project_id])[0]
        remaining = balances["allocated"] - balances["total"]
        LOG.info(
            "Remaining balance for project {}: {:.2f}".format(project_id, remaining)
        )

        return remaining

    def _get_project_charge_code(self, keystone_project_id):
        """Get project charge code from Keystone"""
        keystone_project = self.keystone_api.get_project(keystone_project_id)
        enforcement_key = "name"

        charge_code = keystone_project.get(enforcement_key)

        if not charge_code:
            raise exceptions.BillingError(
                message=(
                    f"Enforcement attribute '{enforcement_key}' is not defined for "
                    f"project {keystone_project.name} ({keystone_project.id})"
                )
            )

        return charge_code

    def _get_username(self, keystone_user_id):
        """Get username from Keystone"""
        keystone_user = self.keystone_api.get_user(keystone_user_id)
        username = keystone_user.get("name")
        if not username:
            raise exceptions.BillingError(
                message=(f"Username is not found for {keystone_user_id}")
            )

        return username

    def _get_portal_project(self, charge_code):
        return Project.objects.get(charge_code=charge_code)

    def _get_portal_user(self, username):
        return get_user_model().objects.get(username=username)

    def _get_charges_by_reservation(self, resource_id, region):
        return Charge.objects.filter(resource_id=resource_id).filter(region_name=region)

    def get_lease_duration_hrs(self, lease_values):
        start_date = self._date_from_string(lease_values["start_date"])
        end_date = self._date_from_string(lease_values["end_date"])

        return dt_hours(end_date - start_date)

    def evaluate_lease(self, context, lease_values):
        project_charge_code = self._get_project_charge_code(context["project_id"])
        duration = self.get_lease_duration_hrs(lease_values)
        total_su_factor = self._total_su_factor(lease_values)
        amount = duration * total_su_factor
        username = self._get_username(context["user_id"])

        return LeaseEval(
            self._get_portal_project(project_charge_code),
            self._get_portal_user(username),
            context["region_name"],
            duration,
            total_su_factor,
            amount,
        )

    def get_balance_service_version(self, data):
        """Get the balance service version of the project"""
        keystone_project_id = data["context"]["project_id"]
        project_charge_code = self._get_project_charge_code(keystone_project_id)
        proj = self._get_portal_project(project_charge_code)
        alloc = su_calculators.get_active_allocation(proj)
        if alloc:
            return alloc.balance_service_version
        else:
            return 2

    def check_usage_against_allocation(self, data):
        """Check if we have enough available SUs for this reservation

        Raises a BillingError if we don't have enough available SUs.
        """
        lease = data["lease"]
        lease_eval = self.evaluate_lease(data["context"], lease)

        LOG.debug(f"Evaluating new lease request: {lease} ({lease_eval})")
        debug_lease_reservations("New reservation", lease)

        left = self.get_remaining_balance(lease_eval.project.id)

        if left - lease_eval.amount < 0:
            raise exceptions.BillingError(
                message=(
                    "Reservation for project {} would spend {:.2f} SUs, "
                    "only {:.2f} left".format(
                        lease_eval.project.charge_code, lease_eval.amount, left
                    )
                )
            )

        alloc = su_calculators.get_active_allocation(lease_eval.project)
        approved_alloc = su_calculators.get_consecutive_approved_allocation(
            lease_eval.project, alloc
        )
        self._check_alloc_expiration_date(lease, alloc, approved_alloc)

        # create new charges
        for reservation in lease["reservations"]:
            new_charge = Charge(
                allocation=alloc,
                user=lease_eval.user,
                region_name=lease_eval.region,
                resource_id=TMP_RESOURCE_ID.format(
                    prefix=TMP_RESOURCE_ID_PREFIX,
                    project_id=lease["project_id"],
                    user_id=lease["user_id"],
                    start_date=lease["start_date"],
                    name=lease["name"],
                ),
                resource_type=reservation["resource_type"],
                start_time=self._convert_to_localtime(
                    self._date_from_string(lease["start_date"])
                ),
                end_time=self._convert_to_localtime(
                    self._date_from_string(lease["end_date"])
                ),
                hourly_cost=self._get_reservation_sus(
                    reservation["resource_type"], reservation["allocations"]
                ),
            )
            new_charge.save()

    def check_usage_against_allocation_update(self, data):
        """Check if we have enough available SUs for update"""
        context = data["context"]
        old_lease = data["current_lease"]
        new_lease = data["lease"]

        old_lease_eval = self.evaluate_lease(context, old_lease)
        new_lease_eval = self.evaluate_lease(context, new_lease)

        LOG.debug(
            (
                "Evaluating lease update request: "
                f"old_lease={old_lease_eval}, new_lease={new_lease_eval}"
            )
        )
        debug_lease_reservations("Old reservation", old_lease)
        debug_lease_reservations("New reservation", new_lease)

        left = self.get_remaining_balance(old_lease_eval.project.id)

        change_amount = new_lease_eval.amount - old_lease_eval.amount

        if change_amount > left:
            raise exceptions.BillingError(
                "Reservation update would spend {:.2f} more SUs, only "
                "{:.2f} left".format(change_amount, left)
            )

        # create/update charges
        now = timezone.now()
        end_date_changed = old_lease["end_date"] != new_lease["end_date"]
        alloc = su_calculators.get_active_allocation(new_lease_eval.project)
        approved_alloc = su_calculators.get_consecutive_approved_allocation(
            new_lease_eval.project, alloc
        )
        self._check_alloc_expiration_date(new_lease, alloc, approved_alloc)
        for reservation in new_lease["reservations"]:
            new_hourly_cost = self._get_reservation_sus(
                reservation["resource_type"], reservation["allocations"]
            )
            if not end_date_changed:
                # check if hourly_cost changed
                old_reservation = [
                    r for r in old_lease["reservations"] if r["id"] == reservation["id"]
                ]
                old_hourly_cost = None
                if len(old_reservation) > 0:
                    old_reservation = old_reservation[0]
                    old_hourly_cost = self._get_reservation_sus(
                        old_reservation["resource_type"], old_reservation["allocations"]
                    )
                if new_hourly_cost == old_hourly_cost:
                    # nothing changed
                    continue
            reservation_charges = self._get_charges_by_reservation(
                reservation["id"], new_lease_eval.region
            )

            # get the ongoing charge
            ongoing_charge = [c for c in reservation_charges if c.end_time > now]
            # should have exactly one ongoing charge
            if len(ongoing_charge) == 1:
                ongoing_charge = ongoing_charge[0]
                ongoing_charge.end_time = now
                ongoing_charge.save()
            else:
                raise exceptions.BillingError(
                    message=(
                        f"Wrong number of ongoing charges for reservation {reservation['id']}"
                    )
                )
            new_charge = Charge(
                allocation=alloc,
                user=new_lease_eval.user,
                region_name=new_lease_eval.region,
                resource_id=reservation["id"],
                resource_type=reservation["resource_type"],
                start_time=max(
                    now,
                    self._convert_to_localtime(
                        self._date_from_string(new_lease["start_date"])
                    ),
                ),
                end_time=self._convert_to_localtime(
                    self._date_from_string(new_lease["end_date"])
                ),
                hourly_cost=new_hourly_cost,
            )
            new_charge.save()

    def stop_charging(self, data):
        """Stop charging SUs"""
        context = data["context"]
        lease = data["lease"]

        lease_eval = self.evaluate_lease(context, lease)

        LOG.debug(f"Stop charging for lease: {lease} ({lease_eval})")
        debug_lease_reservations("Ending reservation", lease)

        now = timezone.now()
        for reservation in lease["reservations"]:
            reservation_charges = self._get_charges_by_reservation(
                reservation["id"], lease_eval.region
            )

            for charge in reservation_charges:
                if charge.end_time > now:
                    charge.end_time = now
                    charge.save()

    def __get_billrate(self, resource, resource_type=None):

        su_factor = resource.get("su_factor")

        if su_factor:
            return float(su_factor)

        return DEFAULT_SU_FACTOR

    def _get_reservation_sus(self, resource_type, allocations):
        return sum(self.__get_billrate(a, resource_type) for a in allocations)

    def _total_su_factor(self, lease_values):

        total_su_factor = 0

        for reservation in lease_values["reservations"]:
            resource_type = reservation["resource_type"]
            allocations = reservation["allocations"]
            total_su_factor += self._get_reservation_sus(resource_type, allocations)

        return total_su_factor

    def _date_from_string(self, date_string, date_format="%Y-%m-%d %H:%M:%S"):
        date = datetime.datetime.strptime(date_string, date_format)
        return date

    def _convert_to_localtime(self, utctime):
        utc = utctime.replace(tzinfo=pytz.UTC)
        localtz = utc.astimezone(timezone.get_current_timezone())
        return localtz

    def _check_alloc_expiration_date(self, lease, alloc, approved_alloc):
        lease_end = self._convert_to_localtime(
            self._date_from_string(lease["end_date"])
        )
        if (approved_alloc and lease_end > approved_alloc.expiration_date) or (
            not approved_alloc and lease_end > alloc.expiration_date
        ):
            raise exceptions.LeasePastExpirationError()
