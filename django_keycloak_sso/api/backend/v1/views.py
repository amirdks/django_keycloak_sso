from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from django_keycloak_sso.api import serializers as module_serializers
from django_keycloak_sso.base_views import BaseKeycloakAdminView
from django_keycloak_sso.documentation import keycloak_login_doc, keycloak_api_doc, keycloak_admin_doc
from django_keycloak_sso.keycloak import KeyCloakConfidentialClient
from django_keycloak_sso.paginations import DefaultPagination
from django_keycloak_sso.sso.authentication import CustomUser
from ...serializers import KeyCloakSetCookieSerializer


class KeyCloakLoginView(APIView):
    http_method_names = ('post',)
    authentication_classes = []

    @keycloak_login_doc(
        operation_summary="Set Token Cookie",
        operation_description="Set received token from keycloak on request cookie",
        request_body=KeyCloakSetCookieSerializer,
        responses={
            200: {
                'description': 'Login successful',
                'content': {
                    'application/json': {
                        'schema': {
                            'type': 'object',
                            'properties': {
                                'message': {'type': 'string'},
                                'token': {'type': 'string'},
                                'user': {'type': 'object'}
                            }
                        }
                    }
                }
            }
        }
    )
    def post(self, request: Request) -> Response:
        keycloak_klass = KeyCloakConfidentialClient()
        serializer = KeyCloakSetCookieSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = serializer.validated_data['token']
        refresh_token = serializer.validated_data['refreshToken']
        client_id = serializer.validated_data['client_id']

        try:
            decoded_token = keycloak_klass.decode_token(token)
        except KeyCloakConfidentialClient.KeyCloakException as e:
            return Response({"error": str(e)}, status=401)

        response = Response({
            "message": "Login successful",
            "token": token,
            "user": decoded_token
        }, status=status.HTTP_200_OK)

        if keycloak_klass.save_token_method == keycloak_klass.KeyCloakSaveTokenMethodChoices.COOKIE:
            response = keycloak_klass.set_httponly_cookie('access_token', token, response)
            response = keycloak_klass.set_httponly_cookie('refresh_token', refresh_token, response)
            response = keycloak_klass.set_httponly_cookie('client_id', client_id, response)

        return response


class KeyCloakRefreshView(APIView):
    authentication_classes = []

    @keycloak_api_doc(
        operation_summary="Refresh Token",
        operation_description="Refresh received token from keycloak",
        responses={
            200: {
                'description': 'Token refreshed successfully',
                'content': {
                    'application/json': {
                        'schema': {
                            'type': 'object',
                            'properties': {
                                'detail': {'type': 'string'},
                                'access_token': {'type': 'string', 'description': 'New access token'},
                                'refresh_token': {'type': 'string', 'description': 'New refresh token (optional)'}
                            }
                        }
                    }
                }
            },
            401: {
                'description': 'No refresh token or client ID / Token refresh failed',
                'content': {
                    'application/json': {
                        'schema': {
                            'type': 'object',
                            'properties': {
                                'detail': {'type': 'string'}
                            }
                        }
                    }
                }
            }
        }
    )
    def post(self, request):
        keycloak_klass = KeyCloakConfidentialClient()
        refresh_token = keycloak_klass.get_token(request, 'refresh_token')
        client_id = keycloak_klass.get_token(request, 'client_id')

        if not refresh_token or not client_id:
            return Response({"detail": "No refresh token Or Client ID"}, status=401)

        try:
            new_tokens = keycloak_klass.send_request(
                keycloak_klass.KeyCloakRequestTypeChoices.REFRESH_ACCESS_TOKEN,
                keycloak_klass.KeyCloakRequestTypeChoices,
                keycloak_klass.KeyCloakRequestMethodChoices.POST,
                keycloak_klass.KeyCloakPanelTypeChoices.USER,
                refresh_token=refresh_token,
                client_id=client_id,
            )
        except Exception as e:
            return Response({"detail": "Token refresh failed"}, status=401)

        response = Response({"detail": "Token refreshed"}, status=200)
        response.set_cookie("access_token", new_tokens["access_token"], httponly=True, secure=True)

        if keycloak_klass.save_token_method == keycloak_klass.KeyCloakSaveTokenMethodChoices.COOKIE:
            response = keycloak_klass.set_httponly_cookie('refresh_token', refresh_token, response)
            if "refresh_token" in new_tokens:
                response.set_cookie("refresh_token", new_tokens["refresh_token"], httponly=True, secure=True)
            return response

        return Response(new_tokens, status=200)


class KeyCloakLogoutView(APIView):
    authentication_classes = []

    @keycloak_api_doc(
        operation_summary="Logout Token",
        operation_description="Logout received token from keycloak",
        responses={
            200: {
                'description': 'Logged out successfully',
                'content': {
                    'application/json': {
                        'schema': {
                            'type': 'object',
                            'properties': {
                                'detail': {'type': 'string', 'example': 'Logged out'}
                            }
                        }
                    }
                }
            },
            401: {
                'description': 'No refresh token or client ID',
                'content': {
                    'application/json': {
                        'schema': {
                            'type': 'object',
                            'properties': {
                                'detail': {'type': 'string'}
                            }
                        }
                    }
                }
            }
        }
    )
    def post(self, request):
        keycloak_klass = KeyCloakConfidentialClient()
        refresh_token = keycloak_klass.get_token(request, 'refresh_token')
        client_id = keycloak_klass.get_token(request, 'client_id')

        if not refresh_token or not client_id:
            return Response({"detail": "No refresh token Or Client ID"}, status=401)

        logout_res = keycloak_klass.send_request(
            keycloak_klass.KeyCloakRequestTypeChoices.LOGOUT,
            keycloak_klass.KeyCloakRequestTypeChoices,
            keycloak_klass.KeyCloakRequestMethodChoices.POST,
            keycloak_klass.KeyCloakPanelTypeChoices.USER,
            refresh_token=refresh_token,
            client_id=client_id,
        )

        if keycloak_klass.save_token_method == keycloak_klass.KeyCloakSaveTokenMethodChoices.COOKIE:
            response = Response({"detail": "Logged out"}, status=200)
            response.delete_cookie("access_token")
            response.delete_cookie("refresh_token")
            response.delete_cookie("client_id")
            return response

        return Response({"detail": "Logged out"}, status=200)


class UserProfileRetrieveView(BaseKeycloakAdminView):

    @keycloak_admin_doc(
        operation_summary="User Profile Retrieve",
        operation_description="User Profile Retrieve from keycloak",
        responses={
            200: module_serializers.UserSerializer(),
            401: {
                'description': 'Invalid or expired token',
                'content': {
                    'application/json': {
                        'schema': {
                            'type': 'object',
                            'properties': {
                                'error': {'type': 'string'}
                            }
                        }
                    }
                }
            }
        }
    )
    def get(self, request: Request):
        keycloak_klass = KeyCloakConfidentialClient()
        access_token = keycloak_klass.get_token(request, 'access_token')

        try:
            decoded_token = keycloak_klass.decode_token(access_token)
        except KeyCloakConfidentialClient.KeyCloakException as e:
            return Response({"error": str(e)}, status=401)

        return Response(module_serializers.UserSerializer(
            CustomUser(payload=decoded_token, is_authenticated=False)
        ).data, status=200)


class GroupListRetrieveView(BaseKeycloakAdminView):
    pagination_class = DefaultPagination

    @keycloak_admin_doc(
        operation_summary="Group List Retrieve",
        operation_description="Group List Retrieve from keycloak",
        responses={
            200: module_serializers.GroupSerializer(many=True),
            404: {
                'description': 'Requested group data was not found',
                'content': {
                    'application/json': {
                        'schema': {
                            'type': 'object',
                            'properties': {
                                'detail': {'type': 'string'}
                            }
                        }
                    }
                }
            }
        },
        # Add query parameters documentation
        parameters=[
            {
                'name': 'own',
                'in': 'query',
                'description': 'Filter to user\'s own groups (set to "1" to enable)',
                'required': False,
                'schema': {'type': 'string', 'enum': ['1']}
            },
            {
                'name': 'type',
                'in': 'query',
                'description': 'Filter groups by type/role',
                'required': False,
                'schema': {'type': 'string'}
            }
        ]
    )
    def get(self, request: Request, pk: str = None):
        keycloak_klass = KeyCloakConfidentialClient()

        try:
            response = keycloak_klass.send_request(
                keycloak_klass.KeyCloakRequestTypeChoices.GROUPS,
                keycloak_klass.KeyCloakRequestTypeChoices,
                keycloak_klass.KeyCloakRequestMethodChoices.GET,
                keycloak_klass.KeyCloakPanelTypeChoices.ADMIN,
                detail_pk=pk,
            )

            if request.query_params.get("own") == "1" and not pk:
                user_group_names = [group for group in request.user.groups_parent]
                response = [group for group in response if group.get("name") in user_group_names]
                group_type = request.query_params.get("type")

                if group_type:
                    group_with_type = [
                        user_group for user_group in request.user.groups_dict_list if
                        user_group.get("role") == group_type
                    ]
                    group_with_type_name_list = [group.get("title") for group in group_with_type]
                    response = [group for group in response if group.get("name") in group_with_type_name_list]

            paginator = self.pagination_class()
            paginated_queryset = paginator.paginate_queryset(response, request)
            serializer = module_serializers.GroupSerializer(paginated_queryset, many=True)
            return paginator.get_paginated_response(serializer.data)

        except keycloak_klass.KeyCloakNotFoundException:
            return Response({"detail": "Requested group data was not found"}, status=404)


class UserListRetrieveView(BaseKeycloakAdminView):

    @keycloak_admin_doc(
        operation_summary="User List Retrieve",
        operation_description="User List Retrieve from keycloak",
        responses={
            200: {
                'description': 'List of users from KeyCloak',
                'content': {
                    'application/json': {
                        'schema': {
                            'type': 'array',
                            'items': {
                                'type': 'object',
                                'description': 'User data from KeyCloak'
                            }
                        }
                    }
                }
            },
            404: {
                'description': 'Requested user data was not found',
                'content': {
                    'application/json': {
                        'schema': {
                            'type': 'object',
                            'properties': {
                                'detail': {'type': 'string'}
                            }
                        }
                    }
                }
            }
        }
    )
    def get(self, request: Request, pk: str = None):
        keycloak_klass = KeyCloakConfidentialClient()

        try:
            response = keycloak_klass.send_request(
                keycloak_klass.KeyCloakRequestTypeChoices.USERS,
                keycloak_klass.KeyCloakRequestTypeChoices,
                keycloak_klass.KeyCloakRequestMethodChoices.GET,
                keycloak_klass.KeyCloakPanelTypeChoices.ADMIN,
                detail_pk=pk,
            )
        except keycloak_klass.KeyCloakNotFoundException as e:
            return Response({"detail": "Requested user data was not found"}, status=404)

        return Response(response, status=200)
