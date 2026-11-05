from django.core.exceptions import ValidationError
from django.db import models


class ConfigVariable(models.Model):
    KEY_CHOICES = [
        ("max_lease_length", "Maximum lease length (seconds)"),
        ("lease_update_window", "Lease update window"),
        ("su_factor", "SU factor (hourly cost)"),
        ("region_end_date", "Region end date (Unix UTC timestamp)"),
        ("block_gpu", "Block GPU nodes (1 = blocked, 0 = allowed)"),
    ]
    RESOURCE_TYPE_CHOICES = [
        ("physical:host", "Bare metal host"),
        ("flavor:instance", "VM flavor"),
        ("network", "Network"),
        ("virtual:floatingip", "Floating IP"),
        ("device", "Device"),
    ]
    # Rows are ranked by who they apply to, then by what they cover, from one
    # resource up to a whole region. So a project's row overrides every rate for
    # that project, and a region's row only overrides rows that cover more.
    WHO_SCOPES = ["username", "project_charge_code"]
    WHAT_SCOPES = [
        "resource_name",
        "flavor_id",
        "resource_class",
        "resource_type",
        "region",
    ]

    key = models.CharField(max_length=255, choices=KEY_CHOICES)
    value = models.DecimalField(max_digits=20, decimal_places=6)

    # Optional fields to scope the variable to
    flavor_id = models.CharField(max_length=255, blank=True, null=True)
    username = models.CharField(max_length=1024, blank=True, null=True)
    project_charge_code = models.CharField(max_length=255, blank=True, null=True)
    region = models.CharField(max_length=100, blank=True, null=True)
    resource_type = models.CharField(
        max_length=255, choices=RESOURCE_TYPE_CHOICES, blank=True, null=True
    )
    resource_class = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="node_type for hosts, stitch_provider for networks, "
        "machine_name for devices",
    )
    resource_name = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="One specific resource: its node_name, name, uid or "
        "hypervisor_hostname",
    )

    def clean(self):
        duplicates = ConfigVariable.objects.filter(
            key=self.key,
            flavor_id=self.flavor_id,
            username=self.username,
            project_charge_code=self.project_charge_code,
            region__iexact=self.region,
            resource_type=self.resource_type,
            resource_class=self.resource_class,
            resource_name=self.resource_name,
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
        if self.resource_type:
            parts.append(f"type={self.resource_type}")
        if self.resource_class:
            parts.append(f"class={self.resource_class}")
        if self.resource_name:
            parts.append(f"resource={self.resource_name}")
        return " | ".join(parts)

    @classmethod
    def get_value(cls, key, **scope):
        """
        Look up the most specific configuration variable for the given parameters,
        returning none if not found. See pick_value for the parameters.
        """
        return cls.pick_value(cls.objects.filter(key=key), **scope)

    @classmethod
    def pick_value(
        cls,
        variables,
        flavor_id=None,
        username=None,
        charge_code=None,
        region=None,
        resource_type=None,
        resource_class=None,
        resource_names=(),
    ):
        """
        Return the value of the most specific of the given variables that applies
        to the parameters, or None if none apply.

        A variable applies if each of its scope fields is unset or matches, where
        resource_name matches any of resource_names and region matching is
        case-insensitive. Applicable variables are ranked by the scope fields they
        set, in the order of WHO_SCOPES then WHAT_SCOPES.
        """

        def applies(c):
            return (
                c.username in (None, username)
                and c.project_charge_code in (None, charge_code)
                and c.flavor_id in (None, flavor_id)
                and (c.resource_name is None or c.resource_name in resource_names)
                and c.resource_class in (None, resource_class)
                and c.resource_type in (None, resource_type)
                and (c.region is None or c.region.lower() == (region or "").lower())
            )

        def rank(c):
            scopes = cls.WHO_SCOPES + cls.WHAT_SCOPES
            return [getattr(c, f) is not None for f in scopes]

        matching = [c for c in variables if applies(c)]
        return max(matching, key=rank).value if matching else None
