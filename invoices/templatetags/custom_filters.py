from django import template

register = template.Library()

@register.filter
def divide(value, arg):
    try:
        return value / arg
    except (TypeError, ZeroDivisionError):
        return 0  # Return 0 or any default value in case of an error

@register.filter
def add(value, arg):
    try:
        return value + arg
    except TypeError:
        return 0  # Return 0 or any default value in case of an error