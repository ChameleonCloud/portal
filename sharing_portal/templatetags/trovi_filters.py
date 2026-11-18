from django.conf import settings
from django import template
from django.template.defaultfilters import stringfilter

from datetime import datetime

register = template.Library()


@register.filter(name="trovi_date_format")
@stringfilter
def trovi_date_format(value):
    dt = datetime.strptime(value, settings.ARTIFACT_DATETIME_FORMAT)
    return dt.strftime("%b. %-d, %Y, %-I:%M %p")


@register.simple_tag
def trovi_dashboard_url(*parts):
    return "/".join([settings.TROVI_DASHBOARD_URL_BASE, *map(str, parts)])


@register.filter
def launch_status_class(status):
    """The Bootstrap label class for a launch's status"""
    return {
        "ready": "success",
        "failed": "danger",
        "cancelled": "warning",
        "pending": "info",
        "running": "info",
    }.get(status, "default")
