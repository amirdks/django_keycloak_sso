from django.conf import settings


def get_settings_value(name: str, default=None):
    return (
        getattr(settings, name, default)
        if hasattr(settings, name)
        else default
    )
