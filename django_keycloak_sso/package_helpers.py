from typing import Literal

from django.utils.module_loading import import_string


def get_package_settings(
        key: str,
        arg_type: Literal["list", "solo"] = 'solo',
        convert_str: bool = False,
):
    from . import settings as package_settings
    settings_value = getattr(package_settings, key, None)
    if settings_value is None:
        raise ValueError("Settings key not found")
    if arg_type == 'list' and convert_str:
        return [import_string(p) for p in settings_value]
    if arg_type == 'solo' and convert_str:
        return import_string(settings_value)
    return settings_value
