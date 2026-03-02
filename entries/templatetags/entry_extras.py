from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """
    Allows dictionary lookup in Django templates.
    Usage: {{ my_dict|get_item:key }}
    """
    return dictionary.get(key)

@register.filter
def extract_uuid(url):
    if not url:
        return ""
    return url.rstrip("/").split("/")[-1]