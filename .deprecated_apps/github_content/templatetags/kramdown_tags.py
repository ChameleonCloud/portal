from django import template
from django.utils.safestring import mark_safe
from subprocess import Popen, PIPE, STDOUT

register = template.Library()

@register.filter
def kramdown(value):
    p = Popen(['kramdown'], stdout=PIPE, stdin=PIPE, stderr=PIPE)
    stdout_data = p.communicate(input=value)[0]
    return mark_safe( stdout_data )
