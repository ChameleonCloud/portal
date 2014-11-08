from django import template
import json

register = template.Library()

@register.filter
def to_json(value):
    return json.dumps(value)
