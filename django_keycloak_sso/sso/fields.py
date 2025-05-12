from typing import Any, List

from django.core.cache import cache
from django.db import models
from django.utils.translation import gettext_lazy as _

from django_keycloak_sso.keycloak import KeyCloakBaseManager, KeyCloakConfidentialClient
from django_keycloak_sso.sso.authentication import CustomUser, CustomGroup
from django_keycloak_sso.sso.helpers import CustomGetterObjectKlass
from django_keycloak_sso.sso.sso import SSOKlass


class CustomSSORelatedField(models.CharField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("max_length", 36)
        super().__init__(*args, **kwargs)

    def from_db_value(self, value: Any, expression, connection) -> str | None:
        """
        Converts the database value back into an integer upon retrieval.
        """
        if value is None:
            return None
        return str(value)

    def _get_sso_field_value(self, value: str | int, sso_method: str, cache_key: str = None,
                             getter_klass: Any = None) -> Any:
        class_name = str(self.__class__.__name__).lower()
        cache_key = cache_key if cache_key else f"{class_name}_{value}"
        data = cache.get(cache_key)

        if not data:
            # Fetch user data from SSO if not cached
            sso_client = SSOKlass()
            if not hasattr(sso_client, sso_method):
                raise _("SSO Klass hasn't specified method")
            try:
                data = getattr(sso_client, sso_method)(pk=value)
                cache.set(cache_key, data, timeout=3600)  # Cache for 1 hour
            except (
                    SSOKlass.SSOKlassException,
                    KeyCloakConfidentialClient.KeyCloakException,
                    KeyCloakConfidentialClient.KeyCloakNotFoundException
            ):
                data = None
        getter_klass = getter_klass if getter_klass else CustomGetterObjectKlass
        return getter_klass(payload=data)


class SSOUserM2MField(models.ManyToManyField):
    """
    Custom Many-to-Many Field for SSO users.
    Integrates a through model to store additional user-related fields.
    """

    def __init__(self, to, **kwargs):
        """
        Initializes the custom M2M field. Sets 'to' to the User model.
        """
        if 'through' not in kwargs:
            raise ValueError(_("You must specify a 'through' model for SSOUserM2MField."))
        super().__init__(to, **kwargs)

    def get_full_users(self, group_instance) -> List:
        """
        Fetch full user data from SSO for all users in the group.
        """
        user_ids = (
            self.through.objects.filter(group=group_instance)
            .values_list('user_id', flat=True)
        )
        full_users = []
        for user_id in user_ids:
            cache_key = f"sso_user_{user_id}"
            user_data = cache.get(cache_key)

            if not user_data:
                # Fetch user data from SSO if not in cache
                sso_client = SSOKlass()
                if not hasattr(sso_client, 'get_user_detail_data'):
                    raise ValueError(_("SSO Klass hasn't specified method 'get_user_detail_data'"))
                user_data = sso_client.get_user_detail_data(pk=user_id)
                cache.set(cache_key, user_data, timeout=3600)  # Cache for 1 hour

            full_users.append(CustomUser(**user_data))

        return full_users


class SSOUserField(CustomSSORelatedField):
    """
    Custom field for storing a user ID as an integer.
    Accepts either an integer ID or a CustomUser instance, storing the extracted ID.
    """

    def get_prep_value(self, value: CustomUser | str) -> str | None:
        """
        Prepares the value for saving to the database.
        """
        if isinstance(value, CustomUser):
            # Extract the 'id' attribute from the CustomUser instance
            return value.id
            # return int(value.id)
        elif isinstance(value, str):
            # If an integer ID is provided directly
            return value
        elif value is None:
            return None  # Allows null values if the field allows it
        else:
            raise ValueError(_("CustomUserField only accepts integers or CustomUser instances."))

    def from_db_value(self, value, expression, connection):
        value = super().from_db_value(value, expression, connection)
        if value is None:
            return None
        return value

    def get_full_data(self, value: int):
        return self._get_sso_field_value(
            value=value,
            sso_method='get_user_detail_data',
            cache_key=None,
            getter_klass=CustomUser,
        )


class SSOGroupField(CustomSSORelatedField):
    """
    Custom field for storing a group ID as an integer.
    Accepts:
    - CustomUser instance with a primary group (stores primary group ID),
    - CustomGroup instance (stores group ID),
    - Integer ID directly.
    """

    def get_prep_value(self, value: CustomUser | CustomGroup | str) -> str | None:
        """
        Prepares the value for saving to the database.
        """
        if isinstance(value, CustomUser):
            # Check if user has a primary group
            primary_group = value.primary_group
            if primary_group is None:
                raise ValueError(_("CustomUser instance has no primary group."))
            return str(primary_group.id)

        elif isinstance(value, CustomGroup):
            # Extract the 'id' attribute from CustomGroup instance
            return str(value.id)

        elif isinstance(value, str):
            # If an integer ID is provided directly
            return value

        elif value is None:
            return None  # Allow null values if the field allows it

        else:
            raise ValueError(
                _("CustomGroupField only accepts integers, CustomUser with a primary group, or CustomGroup instances.")
            )

    def from_db_value(self, value, expression, connection):
        value = super().from_db_value(value, expression, connection)
        if value is None:
            return None
        return value

    def get_full_data(self, value: int):
        return self._get_sso_field_value(
            value=value,
            sso_method='get_company_group_detail_data',
            cache_key=None,
            getter_klass=CustomGroup,
        )