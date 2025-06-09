from typing import Any

from django.conf import settings

from django_keycloak_sso.caching import SSOCacheControlKlass
from django_keycloak_sso.keycloak import KeyCloakConfidentialClient


class CustomGetterObjectKlass:
    def __init__(self, payload: dict):
        self.is_exists = bool(payload)
        self._payload = payload
        self.keycloak_klass = KeyCloakConfidentialClient()
        self.sso_cache_klass = SSOCacheControlKlass()

    # def __getattr__(self, name):
    #     if name in self._payload:
    #         return self._payload[name]
    #     raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")

    def __getattr__(self, name):
        if not self.is_exists:
            return None
        if name in self._payload:
            return self._payload[name]
        return super().__getattribute__(name)

    def __bool__(self):
        return self.is_exists

    def __repr__(self):
        return f"<CustomGetterObjectKlass()>"

    def _get_cache_key(self, cache_base_key: str):
        return self.sso_cache_klass.get_custom_class_cache_key(cache_base_key, self)

    def _get_cached_value(self, cache_base_key: str) -> Any:
        return self.sso_cache_klass.get_custom_class_cached_value(cache_base_key, self)

    def _set_cache_value(self, cache_base_key: str, value: Any, timeout: int = 3600) -> None:
        return self.sso_cache_klass.set_custom_class_cache_value(cache_base_key, value, self, timeout)


default_sso_service_authorization_method = 'IP'
default_jwt_algorithm = 'HS256'


def get_settings_value(name: str, default=None):
    return (
        getattr(settings, name, default)
        if hasattr(settings, name)
        else default
    )


def get_sso_service_authorization_method():
    return get_settings_value("SSO_SERVICE_AUTHORIZATION_METHOD", default_sso_service_authorization_method)


def get_sso_service_authorization_key():
    return get_settings_value("SSO_SERVICE_AUTHORIZATION_KEY", '')


def get_jwt_algorithm():
    return get_settings_value("JWT_ALGORITHM", default_jwt_algorithm)
