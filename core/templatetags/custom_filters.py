from django import template

register = template.Library()

@register.filter
def pluck(queryset_list, key):
    """
    Extracts values from a list of dicts by key.
    Example: [{'status': 'open', 'count': 5}]|pluck:"status" -> ['open']
    """
    return [d.get(key) for d in queryset_list]
  
