import hashlib
from typing import Any

from django.conf import settings
from django.core.cache import cache

from django_keycloak_sso.keycloak import KeyCloakConfidentialClient


class CustomGetterObjectKlass:
    def __init__(self, payload: dict):
        self._payload = payload
        self.keycloak_klass = KeyCloakConfidentialClient()

    # def __getattr__(self, name):
    #     if name in self._payload:
    #         return self._payload[name]
    #     raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")

    def __getattr__(self, name):
        if name in self._payload:
            return self._payload[name]
        return super().__getattribute__(name)

    def __repr__(self):
        return f"<CustomGetterObjectKlass()>"

    def _get_cache_key(self, cache_base_key: str):
        cache_base_key = f"{cache_base_key}_{self.id}"
        cache_key = hashlib.sha256(cache_base_key.encode()).hexdigest()
        return cache_key

    def _get_cached_value(self, cache_base_key: str) -> Any:
        cache_key = self._get_cache_key(cache_base_key)
        data = cache.get(cache_key)
        return data if data is not None else None

    def _set_cache_value(self, cache_base_key: str, value: Any, timeout: int = 3600) -> None:
        cache_key = self._get_cache_key(cache_base_key)
        cache.set(cache_key, value, timeout=timeout)


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
