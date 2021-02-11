import json

from django import template

register = template.Library()


@register.filter
def to_json(value, indent=None):
    return json.dumps(value, indent=indent)
