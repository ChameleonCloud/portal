from django.conf import settings
from django import template
from django.template.defaultfilters import stringfilter

from datetime import datetime

register = template.Library()

@register.filter(name='trovi_date_format')
@stringfilter
def trovi_date_format(value):
    dt = datetime.strptime(value, settings.ARTIFACT_DATETIME_FORMAT)
    return dt.strftime("%b. %-d, %Y, %-I:%M %p")
