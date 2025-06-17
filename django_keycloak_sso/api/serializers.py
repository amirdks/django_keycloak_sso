from django.db import transaction
from rest_framework import serializers

from django_keycloak_sso.sso.authentication import CustomGroup, CustomUser


class KeyCloakSetCookieSerializer(serializers.Serializer):
    token = serializers.CharField(required=True)
    refreshToken = serializers.CharField(required=True)
    client_id = serializers.CharField(required=True)


class GroupSerializer(serializers.Serializer):
    id = serializers.CharField()
    title = serializers.SerializerMethodField()

    def get_title(self, obj):
        if hasattr(obj, 'name'):
            return getattr(obj, 'name')
        else:
            if obj and obj.get('name'):
                return obj['name']
        return None

    def to_representation(self, instance):
        if not isinstance(instance, CustomGroup):
            instance = CustomGroup(payload=instance)
        if not instance.is_exists:
            return dict()
        return super().to_representation(instance)


class UserSerializer(serializers.Serializer):
    id = serializers.SerializerMethodField()
    username = serializers.CharField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    full_name = serializers.CharField()
    roles = serializers.ListField()
    groups = serializers.SerializerMethodField()
    group_roles = serializers.ListField()
    group_list = serializers.SerializerMethodField()

    def get_id(self, obj):
        if hasattr(obj, 'id'):
            return getattr(obj, 'id')
        else:
            if obj and obj.get('id'):
                return obj['id']
        return None

    def get_groups(self, obj):
        if hasattr(obj, 'groups_parent'):
            return getattr(obj, 'groups_parent')
        else:
            if obj and obj.get('groups_parent'):
                return obj['groups_parent']
        return None

    def get_group_list(self, obj):
        if hasattr(obj, 'groups_dict_list'):
            return getattr(obj, 'groups_dict_list')
        else:
            if obj and obj.get('groups_dict_list'):
                return obj['groups_dict_list']
        return None

    def to_representation(self, instance):
        if not isinstance(instance, CustomUser):
            instance = CustomUser(payload=instance, is_authenticated=False)
        if not instance.is_exists:
            return dict()
        return super().to_representation(instance)


class SSOManyFieldMixin:
    """
    Mixin to handle SSO many-to-many fields in serializers.
    Provides automatic handling of SSO many fields during create/update operations.
    """

    def get_sso_many_fields(self):
        """
        Returns a dictionary of SSO many fields in the model.
        Override this method to customize which fields are handled.
        """
        from django_keycloak_sso.sso.fields import SSOManyBaseField  # Update import path

        many_fields = {}
        model = self.Meta.model

        for field_name in dir(model):
            try:
                field = getattr(model, field_name)
                if hasattr(field, 'field') and isinstance(field.field, SSOManyBaseField):
                    many_fields[field_name] = field
            except:
                continue

        return many_fields

    def handle_sso_many_fields(self, instance, validated_data):
        """
        Handles updating SSO many-to-many fields after instance creation/update.
        """
        sso_many_fields = self.get_sso_many_fields()

        for field_name, field_descriptor in sso_many_fields.items():
            if field_name in validated_data:
                values = validated_data.pop(field_name, [])
                manager = getattr(instance, field_name)

                # Clear existing relations if updating
                if self.instance:  # Update operation
                    manager.clear()

                # Add new relations
                for value in values:
                    manager.add(value)

    def create(self, validated_data):
        # Extract SSO many field data before creating instance
        sso_many_data = {}
        sso_many_fields = self.get_sso_many_fields()

        for field_name in sso_many_fields:
            if field_name in validated_data:
                sso_many_data[field_name] = validated_data.pop(field_name)

        # Create instance
        with transaction.atomic():
            instance = super().create(validated_data)

            # Handle SSO many fields
            for field_name, values in sso_many_data.items():
                manager = getattr(instance, field_name)
                for value in values:
                    manager.add(value)

        return instance

    def update(self, instance, validated_data):
        # Extract SSO many field data before updating instance
        sso_many_data = {}
        sso_many_fields = self.get_sso_many_fields()

        for field_name in sso_many_fields:
            if field_name in validated_data:
                sso_many_data[field_name] = validated_data.pop(field_name)

        # Update instance
        with transaction.atomic():
            instance = super().update(instance, validated_data)

            # Handle SSO many fields
            for field_name, values in sso_many_data.items():
                manager = getattr(instance, field_name)
                manager.clear()  # Clear existing relations
                for value in values:
                    manager.add(value)

        return instance


class SSOManyField(serializers.Field):
    """
    A generic field for handling SSO many-to-many relationships.
    Can be used instead of ListField for more control.
    """

    def __init__(self, **kwargs):
        self.field_type = kwargs.pop('field_type', 'user')  # 'user' or 'group'
        self.is_limited = kwargs.pop('is_limited', True)
        super().__init__(**kwargs)

    def to_representation(self, obj):
        """
        Serialize the SSO many field to full data from Keycloak
        """
        try:
            # obj here is the manager instance
            if self.is_limited:
                return obj.get_ids()
            else:
                return obj.get_full_data()
        except Exception as e:
            return []

    def to_internal_value(self, data):
        """
        Deserialize list of IDs
        """
        if not isinstance(data, list):
            raise serializers.ValidationError("Expected a list of IDs")

        # Validate each ID
        for item in data:
            if not isinstance(item, str) or len(item) != 36:
                raise serializers.ValidationError(f"Invalid ID format: {item}")

        return data
