from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q


class ConfigVariable(models.Model):
    KEY_CHOICES = [
        ("max_lease_length", "Maximum lease length (seconds)"),
        ("lease_update_window", "Lease update window"),
        ("su_factor", "SU factor (hourly cost)"),
        ("region_end_date", "Region end date (Unix UTC timestamp)"),
    ]

    key = models.CharField(max_length=255, choices=KEY_CHOICES)
    value = models.DecimalField(max_digits=20, decimal_places=6)

    # Optional fields to scope the variable to
    flavor_id = models.CharField(max_length=255, blank=True, null=True)
    username = models.CharField(max_length=1024, blank=True, null=True)
    project_charge_code = models.CharField(max_length=255, blank=True, null=True)
    region = models.CharField(max_length=100, blank=True, null=True)

    def clean(self):
        duplicates = ConfigVariable.objects.filter(
            key=self.key,
            flavor_id=self.flavor_id,
            username=self.username,
            project_charge_code=self.project_charge_code,
            region__iexact=self.region,
        ).exclude(pk=self.pk)
        if duplicates.exists():
            raise ValidationError("Configuration exists for the same key and scope")

    def __str__(self):
        parts = [self.key, str(self.value)]
        if self.flavor_id:
            parts.append(f"flavor={self.flavor_id}")
        if self.username:
            parts.append(f"user={self.username}")
        if self.project_charge_code:
            parts.append(f"project={self.project_charge_code}")
        if self.region:
            parts.append(f"region={self.region}")
        return " | ".join(parts)

    @classmethod
    def get_value(
        cls, key, flavor_id=None, username=None, charge_code=None, region=None
    ):
        """
        Look up the most specific configuration variable for the given parameters,
        returning none if not found.

        Finds all ConfigVariables matching the key and any of the optional parameters,
        then ranks by specificity (i.e. user > project > flavor > region), and gets
        the value for the most specific match. Region matching is case-insensitive.
        """
        matching = cls.objects.filter(key=key).filter(
            Q(username__isnull=True) | Q(username=username),
            Q(project_charge_code__isnull=True) | Q(project_charge_code=charge_code),
            Q(flavor_id__isnull=True) | Q(flavor_id=flavor_id),
            Q(region__isnull=True) | Q(region__iexact=region),
        )

        def rank(c):
            return (
                1 if c.username and c.username == username else 0,
                (
                    1
                    if c.project_charge_code and c.project_charge_code == charge_code
                    else 0
                ),
                1 if c.flavor_id and c.flavor_id == flavor_id else 0,
                1 if c.region and c.region.lower() == (region or "").lower() else 0,
            )

        ranked = sorted(matching, key=lambda c: rank(c), reverse=True)
        return ranked[0].value if ranked else None
