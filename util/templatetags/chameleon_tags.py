from django import template
import json

register = template.Library()


@register.filter
def to_json(value, indent=None):
    return json.dumps(value, indent=indent)
