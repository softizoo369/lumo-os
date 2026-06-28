from django import template

register = template.Library()

@register.filter(name='add_class')
def add_class(field, css_class):
    """
    Adds a CSS class to a Django form field.
    Usage: {{ field|add_class:"form-control" }}
    """
    if hasattr(field, 'as_widget'):
        return field.as_widget(attrs={"class": css_class})
    return field