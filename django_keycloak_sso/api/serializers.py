from rest_framework import serializers


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
        if not instance.is_exists:
            return dict()
        return super().to_representation(instance)
