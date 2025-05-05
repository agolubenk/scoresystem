from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)

@register.filter
def filter_position(position_grades, position_name):
    if not position_grades:
        return None
    return next((pg for pg in position_grades if pg.position.name == position_name), None)

@register.filter
def filter_parameter(descriptions, parameter_id):
    return any(desc.parameter_id == parameter_id for desc in descriptions) 