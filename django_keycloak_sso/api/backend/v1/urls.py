from django.urls import path, include

from . import views

auth_urls = [
    path("login/", views.KeyCloakLoginView.as_view(), name="keycloak_login_view"),
    path("refresh/", views.KeyCloakRefreshView.as_view(), name="keycloak_refresh_view"),
    path("logout/", views.KeyCloakLogoutView.as_view(), name="keycloak_logout_view"),
    # path('test2/', views.Test.as_view(), name='test'),
]
sso_urls = [
    path('profile/', views.UserProfileRetrieveView.as_view(), name='user_profile_retrieve_view'),
    path('groups/', views.GroupListRetrieveView.as_view(), name='group_list_view'),
    path('groups/create/',views.CreateGroupView.as_view(),name='group_create_view'),
    path('groups/<str:pk>/', views.GroupListRetrieveView.as_view(), name='group_retrieve_view'),
    path('groups/<str:pk>/roles-assign/',views.AssignRoleGroupView.as_view(),name='group_assign_roles_view'),
    path("users/", views.UserListRetrieveView.as_view(), name="user_retrieve_view"),
    path("users/<str:pk>/", views.UserListRetrieveView.as_view(), name="user_list_view"),
    path('roles/',views.RoleListRetrieveView.as_view(),name='role_list_view'),
    path('roles/<str:role_id>/',views.RoleListRetrieveView.as_view(),name='role_retrieve_view'),
    # path("roles/", views.KeyCloakRefreshView.as_view(), name="keycloak_refresh_view"),
]

urlpatterns = [
    path('auth/', include(auth_urls)),
    path('sso/', include(sso_urls)),
]
