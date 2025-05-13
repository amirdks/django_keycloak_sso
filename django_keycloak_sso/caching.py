import hashlib
from typing import Any

from django.core.cache import cache
from django.db.models import TextChoices


class SSOCacheControlKlass:

    def get_custom_class_cache_key(self, cache_base_key: str):
        cache_base_key = f"{cache_base_key}_{self.id}"
        cache_key = hashlib.sha256(cache_base_key.encode()).hexdigest()
        return cache_key

    def get_custom_class_cached_value(self, cache_base_key: str) -> Any:
        cache_key = self.get_custom_class_cache_key(cache_base_key)
        data = cache.get(cache_key)
        return data if data is not None else None

    def set_custom_class_cache_value(self, cache_base_key: str, value: Any, timeout: int = 3600) -> None:
        cache_key = self.get_custom_class_cache_key(cache_base_key)
        cache.set(cache_key, value, timeout=timeout)

    @staticmethod
    def get_cache_key(field_type: TextChoices, pk: str = None):
        if pk:
            cache_key = f"{field_type}_{pk}"
        else:
            cache_key = f"{field_type.lower()}s"
        return cache_key

    def get_cached_value(self, field_type: TextChoices, pk: str = None) -> Any:
        cache_key = self.get_cache_key(field_type, pk)
        data = cache.get(cache_key)
        return data if data is not None else None

    def set_cache_value(
            self,
            field_type: TextChoices,
            value: Any,
            timeout: int = 3600,
            pk: str = None
    ) -> None:
        cache_key = self.get_cache_key(field_type, pk)
        cache.set(cache_key, value, timeout=timeout)
