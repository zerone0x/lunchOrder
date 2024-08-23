from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """Retrieve item from a dictionary."""
    return dictionary.get(key)


@register.filter
def make_tuple(value1, value2):
    return (value1, value2)
