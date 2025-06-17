from typing import Any

from django.apps import apps
from django.core.cache import cache
from django.db import models
from django.utils.translation import gettext_lazy as _

from django_keycloak_sso.keycloak import KeyCloakConfidentialClient
from django_keycloak_sso.sso.authentication import CustomUser, CustomGroup
from django_keycloak_sso.sso.helpers import CustomGetterObjectKlass
from django_keycloak_sso.sso.sso import SSOKlass

sso_klass = SSOKlass()


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


class SSOManyFieldDescriptor:
    def __init__(self, field, manager_klass):
        self.field = field
        self.manager_klass = manager_klass

    def __get__(self, instance, cls=None):
        if instance is None:
            return self
        return self.manager_klass(instance, self.field)


class SSOUserManager:
    def __init__(self, instance, field):
        self.instance = instance
        self.field = field
        self.rel_model = field._relation_model

    def _get_relation_qs(self):
        return self.rel_model.objects.filter(parent=self.instance)

    def get_ids(self):
        return list(self._get_relation_qs().values_list("user_id", flat=True))

    def get_full_data(self):
        users = []
        user_ids = self.get_ids()
        sso_data_list = []

        if len(user_ids) > 0:
            sso_data_list = sso_klass.get_sso_data_list(
                user_ids,
                'user_id',
                sso_klass.SSOFieldTypeChoices.USER
            )

        for uid in user_ids:
            custom_instance = CustomGetterObjectKlass({'user_id': uid})
            try:
                users.append(sso_klass.get_serializer_field_data(
                    field_name='user_id',
                    field_type=sso_klass.SSOFieldTypeChoices.USER,
                    obj_=custom_instance,
                    list_data=sso_data_list,
                    get_from_list=True
                ))
            except Exception as e:
                continue
        return users

    def add(self, user):
        user_id = user.id if isinstance(user, CustomUser) else str(user)
        self.rel_model.objects.get_or_create(parent=self.instance, user_id=user_id)

    def remove(self, user):
        user_id = user.id if isinstance(user, CustomUser) else str(user)
        self._get_relation_qs().filter(user_id=user_id).delete()

    def clear(self):
        self._get_relation_qs().delete()


class SSOGroupManager:
    def __init__(self, instance, field):
        self.instance = instance
        self.field = field
        self.rel_model = field._relation_model

    def _get_relation_qs(self):
        return self.rel_model.objects.filter(parent=self.instance)

    def get_ids(self):
        return list(self._get_relation_qs().values_list("group_id", flat=True))

    def get_full_data(self):
        groups = []
        group_ids = self.get_ids()
        sso_data_list = []

        if len(group_ids) > 0:
            sso_data_list = sso_klass.get_sso_data_list(
                group_ids,
                'group_id',
                sso_klass.SSOFieldTypeChoices.GROUP
            )

        for uid in group_ids:
            custom_instance = CustomGetterObjectKlass({'group_id': uid})
            try:
                groups.append(sso_klass.get_serializer_field_data(
                    field_name='group_id',
                    field_type=sso_klass.SSOFieldTypeChoices.GROUP,
                    obj_=custom_instance,
                    list_data=sso_data_list,
                    get_from_list=True
                ))
            except Exception as e:
                continue
        return groups

    def add(self, group):
        group_id = group.id if isinstance(group, CustomGroup) else str(group)
        self.rel_model.objects.get_or_create(parent=self.instance, group_id=group_id)

    def remove(self, group):
        group_id = group.id if isinstance(group, CustomGroup) else str(group)
        self._get_relation_qs().filter(group_id=group_id).delete()

    def clear(self):
        self._get_relation_qs().delete()


class SSOManyBaseField(models.Field):
    def __init__(self, *args, **kwargs):
        kwargs['editable'] = False
        kwargs['null'] = True
        kwargs['blank'] = True
        self.field_type = None
        self.manager_klass = None
        super().__init__(*args, **kwargs)

    def get_internal_type(self):
        return "TextField"

    # def deconstruct(self):
    #     name, path, args, kwargs = super().deconstruct()
    #     kwargs.pop('editable', None)
    #     return name, path, args, kwargs

    def deconstruct(self):
        # This tells Django: don't include this field in migration files
        return None, None, (), {}

    def contribute_to_class(self, cls, name, **kwargs):
        self.set_attributes_from_name(name)
        self.model_class = cls
        self.name = name
        self.concrete = False
        self._create_relation_model()
        setattr(cls, name, SSOManyFieldDescriptor(self, self.manager_klass))

    def _create_relation_model(self):
        rel_model_name = f"{self.model_class.__name__}_{self.name}_SSORelation"
        app_label = self.model_class._meta.app_label

        full_name = f"{app_label}.{rel_model_name}"

        if apps.all_models[app_label].get(rel_model_name.lower()):
            self._relation_model = apps.get_model(app_label, rel_model_name)
            return

        class Meta:
            app_label = self.model_class._meta.app_label
            unique_together = ('parent', f'{self.field_type}_id')
            verbose_name = f"{self.name} relation"
            verbose_name_plural = f"{self.name} relations"

        field_type = self.field_type
        attrs = {
            '__module__': self.model_class.__module__,
            'parent': models.ForeignKey(self.model_class, on_delete=models.CASCADE),
            f'{self.field_type}_id': models.CharField(max_length=36),
            'Meta': Meta,
            '__str__': lambda self: f"{self.parent} - {getattr(self, f'{field_type}_id', None)}",
        }

        self._relation_model = type(rel_model_name, (models.Model,), attrs)
        models.Model.add_to_class(rel_model_name, self._relation_model)

    def get_attname(self):
        return None  # Prevent Django from mapping this to a real DB field


class SSOManyUserField(SSOManyBaseField):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.field_type = 'user'
        self.manager_klass = SSOUserManager


class SSOManyGroupField(SSOManyBaseField):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.field_type = 'group'
        self.manager_klass = SSOGroupManager

# def clean(self):
#     super().clean()
#     if not self.pk:  # Need to save first
#         return
#     if not self.delivery_user_ids.get_user_ids():
#         raise ValidationError({'delivery_user_ids': _("At least one delivery user is required.")})
