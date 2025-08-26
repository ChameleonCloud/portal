from itertools import combinations
from django.db import models
from django.db.models import Q


def generate_constraints():
    """
    Generate all combinations of the constraint dimensions to ensure
    that there are no duplicate ConfigVariable entries for the same scope.

    The issue is that databases do not consider NULL values as equal, and
    so we must manually specify these constraints. In future versions of
    django, there exists `UniqueConstraint.nulls_distinct` which could help
    but at the moment only PostgreSQL supports it.
    """

    constraint_dimensions = ["flavor_id", "username", "project_charge_code"]
    constraints = []
    for r in range(len(constraint_dimensions) + 1):
        for subset in combinations(constraint_dimensions, r):
            fields = ["key", *subset]

            # Any dimension not in this subset must be NULL
            nulls = {
                dim + "__isnull": True
                for dim in constraint_dimensions
                if dim not in subset
            }
            condition = Q(**nulls) if nulls else None

            label = "__".join(["key", *subset]) if subset else "key"
            constraints.append(
                models.UniqueConstraint(
                    fields=fields,
                    condition=condition,
                    name=f"uniq_config_{label}",
                    violation_error_message=f"Configuration exists for same {label.replace('__', ' & ')}",
                )
            )
    return constraints


class ConfigVariable(models.Model):
    KEY_CHOICES = [
        ("max_lease_length", "Maximum lease length (seconds)"),
        ("lease_update_window", "Lease update window"),
        ("su_factor", "SU factor (hourly cost)"),
    ]

    key = models.CharField(max_length=255, choices=KEY_CHOICES)
    value = models.DecimalField(max_digits=20, decimal_places=6)

    # Optional fields to scope the variable to
    flavor_id = models.CharField(max_length=255, blank=True, null=True)
    username = models.CharField(max_length=1024, blank=True, null=True)
    project_charge_code = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        constraints = generate_constraints()

    def __str__(self):
        parts = [self.key, str(self.value)]
        if self.flavor_id:
            parts.append(f"flavor={self.flavor_id}")
        if self.username:
            parts.append(f"user={self.username}")
        if self.project_charge_code:
            parts.append(f"project={self.project_charge_code}")
        return " | ".join(parts)

    @classmethod
    def get_value(cls, key, flavor_id=None, username=None, charge_code=None):
        """
        Look up the most specific configuration variable for the given parameters,
        returning none if not found.

        Finds all ConfigVariables matching the key and any of the optional parameters,
        then ranks by specificity (i.e. user > project > flavor), and gets the value
        for the most specific match.
        """
        matching = cls.objects.filter(key=key).filter(
            Q(username__isnull=True) | Q(username=username),
            Q(project_charge_code__isnull=True) | Q(project_charge_code=charge_code),
            Q(flavor_id__isnull=True) | Q(flavor_id=flavor_id),
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
            )

        ranked = sorted(matching, key=lambda c: rank(c), reverse=True)
        return ranked[0].value if ranked else None
