from django import template

register = template.Library()

@register.filter
def max_value(oil_meter, fuel_meter):
    return max(oil_meter, fuel_meter)