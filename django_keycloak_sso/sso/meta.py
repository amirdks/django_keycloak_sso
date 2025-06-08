from django.db import models
from rest_framework import serializers

from django_keycloak_sso.sso import fields as sso_fields
from django_keycloak_sso.sso.fields import SSOUserField, SSOGroupField
from .sso import SSOKlass


class SSOModelMeta(models.base.ModelBase):
    def __new__(cls, name, bases, attrs):
        new_class = super().__new__(cls, name, bases, attrs)

        # Dynamically add properties for SSOUserField and SSOGroupField
        for field in new_class._meta.fields:
            if isinstance(field, SSOUserField):
                # Add a property to fetch full user data
                prop_name = f"{field.name}_data"
                setattr(new_class, prop_name, cls._make_sso_property(field.name, "user"))

            elif isinstance(field, SSOGroupField):
                # Add a property to fetch full group data
                prop_name = f"{field.name}_data"
                setattr(new_class, prop_name, cls._make_sso_property(field.name, "group"))

        return new_class

    @staticmethod
    def _make_sso_property(field_name: str, field_type: str):
        """
        Create a dynamic property to fetch SSO data for the given field.

        :param field_name: The name of the field to create the property for.
        :param field_type: The type of SSO data ('user' or 'group').
        :return: A property object for the field.
        """

        def sso_property(instance):
            # Retrieve the field's value from the instance
            value = getattr(instance, field_name)
            if value is None:
                return None  # Return None if no value is set

            # Retrieve the field instance from the model
            field = instance._meta.get_field(field_name)
            if hasattr(value, "id"):
                value = getattr(value, "id")
            # Use the field's `get_full_data` method to fetch detailed data
            return field.get_full_data(value=value)

        # Set property metadata for better introspection
        sso_property.__name__ = f"{field_name}_data"
        sso_property.__doc__ = (
            f"Dynamically fetches full SSO data for the '{field_name}' field of type '{field_type}'."
        )
        return property(sso_property)


# TODO : add functionality for m2m field
class CustomMetaSSOModelSerializer(serializers.ModelSerializer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.Meta.model._meta.get_fields():
            if field.auto_created and not field.concrete:
                continue
            field_name = field.name
            if field_name not in self.fields:
                continue
            if isinstance(field, sso_fields.SSOUserField):
                self._add_dynamic_validation(field_name, SSOKlass.SSODataTypeChoices.USER)
            elif isinstance(field, sso_fields.SSOGroupField):
                self._add_dynamic_validation(field_name, SSOKlass.SSODataTypeChoices.COMPANY_GROUP)

    def _add_dynamic_validation(self, field_name, data_type_choice):
        def validate_field(value):
            if value is None:
                return value
            sso_klass = SSOKlass()
            if not sso_klass.check_object_exists(data_type_choice, value):
                raise serializers.ValidationError(
                    f"{field_name.capitalize()} with ID {value} does not exist in SSO system."
                )
            return value

        self.fields[field_name].validators.append(validate_field)
