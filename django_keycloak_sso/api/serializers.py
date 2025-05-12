from rest_framework import serializers


class KeyCloakSetCookieSerializer(serializers.Serializer):
    token = serializers.CharField(required=True)
    refreshToken = serializers.CharField(required=True)
    client_id = serializers.CharField(required=True)


class GroupSerializer(serializers.Serializer):
    id = serializers.CharField()
    title = serializers.SerializerMethodField()

    def get_title(self, obj):
        if obj and obj.get('name'):
            return obj['name']
        return None


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

    def get_id(self, obj) -> str:
        return obj.id if obj else None

    def get_groups(self, obj) -> str:
        return obj.groups_parent if obj else None

    def get_group_list(self, obj) -> list:
        return obj.groups_dict_list if obj else None
