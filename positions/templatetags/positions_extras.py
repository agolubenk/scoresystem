from django import template

register = template.Library()

@register.filter
def get_item(dictionary, keys):
    """Получить значение из словаря по ключу или кортежу ключей"""
    if isinstance(keys, str) and ',' in keys:
        # Если ключи переданы как строка с разделителем
        keys = tuple(int(k.strip()) for k in keys.split(','))
    return dictionary.get(keys) if isinstance(keys, tuple) else dictionary.get(keys) 